"""CostHive command-line interface.

Two verbs, matching the two input modes (project plan §8):

  * ``scan``     — analyze a live AWS account (Steampipe / Custodian / Komiser /
                   CloudQuery / OpenCost) and rank savings by dollar impact.
  * ``estimate`` — price Terraform/CDK/CFN on disk *before* deploy (Infracost).

Tuned for the FinOps-consultant workflow: cross-account assume-role is a first-class
path, several client accounts can be analyzed in one run, and the output is a
money-first, optionally client-branded report (HTML/MD/JSON/PDF).
"""

from __future__ import annotations

import base64
import datetime as dt
import mimetypes
import os
import sys
import tempfile

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from costhive import __version__
from costhive.aggregate import build_report, build_rollup
from costhive.auth import AuthError, build_contexts, discover_eks_clusters, preflight_cost_access
from costhive.report import VALID_FORMATS, write_reports
from costhive.tools import ALL_TOOLS, DEFAULT_LIVE_TOOLS, build_tools
from costhive.tools.base import CostTool, ToolResult
from costhive.tools.infracost import InfracostTool
from costhive.tools.opencost import OpenCostTool

DEFAULT_FORMATS = ["html", "md", "json"]

app = typer.Typer(
    add_completion=False,
    help="Point CostHive at one or more AWS accounts (or IaC on disk) and get a money-first cost report.",
)
console = Console()


def _version_callback(value: bool):
    if value:
        console.print(f"CostHive {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    _version: bool = typer.Option(
        False,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
):
    """CostHive — AWS cost-optimization toolkit."""


@app.command()
def tools():
    """List available FinOps tools."""
    table = Table(title="Available tools")
    table.add_column("Name")
    table.add_column("Role")
    table.add_column("Target")
    table.add_row("steampipe", "core (scan)", "live AWS account — SQL cost/waste queries")
    table.add_row("custodian", "core (scan)", "live AWS account — policy-as-code (dry-run, report-only)")
    table.add_row("komiser", "opt-in (--komiser-export)", "inventory export — untagged cost-allocation gaps")
    table.add_row("cloudquery", "opt-in (--cloudquery-db-url)", "live account → external DB, then SQL")
    table.add_row("opencost", "opt-in (--opencost-export)", "EKS cluster — Kubernetes cost allocation")
    table.add_row("infracost", "estimate verb", "local IaC on disk — pre-deploy cost")
    console.print(table)


@app.command()
def scan(
    profile: str = typer.Option(None, "--profile", help="AWS profile name."),
    role_arn: list[str] = typer.Option(
        None,
        "--role-arn",
        help="IAM role ARN to assume (STS). Repeat for multi-account analysis.",
    ),
    external_id: str = typer.Option(None, "--external-id", help="External ID for role assumption."),
    regions: str = typer.Option(None, "--regions", help="Comma-separated regions (e.g. eu-central-1,us-east-1)."),
    tools_opt: str = typer.Option(
        ",".join(DEFAULT_LIVE_TOOLS),
        "--tools",
        help=f"Comma-separated tools. Default: {', '.join(DEFAULT_LIVE_TOOLS)}. "
        "Add komiser/cloudquery/opencost with their respective flags.",
    ),
    categories: str = typer.Option(
        None,
        "--categories",
        help="Filter findings to these categories (idle, unused, rightsizing, untagged, "
        "commitment, storage_class, off_hours, network).",
    ),
    policy_dir: str = typer.Option(None, "--policy-dir", help="Cloud Custodian policy directory (default: bundled)."),
    komiser_export: str = typer.Option(None, "--komiser-export", help="Path to a Komiser resources JSON export."),
    cloudquery_db_url: str = typer.Option(None, "--cloudquery-db-url", help="Postgres URL to enable CloudQuery mode."),
    cloudquery_spec: str = typer.Option(None, "--cloudquery-spec", help="CloudQuery sync spec file."),
    opencost_export: str = typer.Option(None, "--opencost-export", help="OpenCost /allocation JSON export (EKS)."),
    client_name: str = typer.Option(None, "--client-name", help="Client/engagement name for the report header."),
    logo: str = typer.Option(None, "--logo", help="Path to a logo image embedded in the report header."),
    output_formats: str = typer.Option(
        ",".join(DEFAULT_FORMATS),
        "--format",
        help="Comma-separated output formats: html, md, json, pdf.",
    ),
    pdf: bool = typer.Option(False, "--pdf", help="Shorthand to add PDF output (the client deliverable)."),
    pdf_engine: str = typer.Option("weasyprint", "--pdf-engine", help="PDF engine: weasyprint (default) or chromium."),
    out_dir: str = typer.Option("./reports", "--out", help="Output directory for reports."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip the confirmation prompt."),
    min_savings: float = typer.Option(
        None,
        "--fail-under",
        help="Exit non-zero if total estimated monthly savings is at/above this amount (CI cost gate).",
    ),
    tool_output: bool = typer.Option(
        False,
        "--tool-output",
        help="Stream raw tool stdout/stderr while commands run. Elapsed-time heartbeats are shown by default.",
    ),
):
    """Analyze one or more live AWS accounts and produce a dollar-ranked savings report.

    Cross-account example:

        costhive scan --role-arn arn:aws:iam::1111:role/CostAudit \\
                      --role-arn arn:aws:iam::2222:role/CostAudit \\
                      --external-id shared-secret --client-name "Acme Corp" --pdf
    """
    selected = _resolve_tools(tools_opt, komiser_export, cloudquery_db_url, opencost_export)
    category_filter = _parse_categories(categories)
    formats = _resolve_formats(output_formats, pdf)
    if pdf_engine not in ("weasyprint", "chromium"):
        console.print(f"[red]Unknown --pdf-engine '{pdf_engine}' (use weasyprint or chromium).[/red]")
        raise typer.Exit(code=2)

    region_list = [r.strip() for r in regions.split(",")] if regions else None
    logo_uri = _logo_data_uri(logo) if logo else ""
    generated_at = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    write_kwargs = {"formats": formats, "pdf_engine": pdf_engine, "console": console}

    try:
        contexts = build_contexts(
            profile=profile,
            role_arns=role_arn or None,
            external_id=external_id,
            regions=region_list,
        )
    except AuthError as exc:
        console.print(f"[red]Authentication failed:[/red] {exc}")
        raise typer.Exit(code=1) from None

    _confirm(contexts, selected, client_name, yes)

    reports = []
    for ctx in contexts:
        console.rule(f"[bold]Account {ctx.identity.account_id}[/bold]")
        access = preflight_cost_access(ctx)
        for note in access.notes:
            console.print(f"[yellow]⚠ {note}[/yellow]")
        if opencost_export:
            _note_eks(ctx)

        tool_objs = _build_scan_tools(
            selected, policy_dir, komiser_export, cloudquery_db_url, cloudquery_spec, opencost_export
        )
        with tempfile.TemporaryDirectory(prefix="costhive-") as workdir:
            results = _run(tool_objs, ctx, workdir, tool_output=tool_output)
            report = build_report(
                _filter_results(results, category_filter),
                account_id=ctx.identity.account_id,
                identity_arn=ctx.identity.arn,
                regions=ctx.regions,
                generated_at=generated_at,
                client_name=client_name or "",
                logo_data_uri=logo_uri,
                cost_data_notes=access.notes,
            )
        target = out_dir if len(contexts) == 1 else os.path.join(out_dir, ctx.identity.account_id)
        paths = write_reports(report, target, **write_kwargs)
        _print_summary(report, paths)
        reports.append(report)

    if len(reports) > 1:
        console.rule("[bold]Roll-up across accounts[/bold]")
        rollup = build_rollup(reports, generated_at=generated_at, client_name=client_name or "", logo_data_uri=logo_uri)
        paths = write_reports(rollup, out_dir, **write_kwargs)
        _print_summary(rollup, paths)
        reports.append(rollup)

    _fail_on_tool_errors(reports)
    _maybe_fail_under(reports, min_savings)
    raise typer.Exit(code=0)


@app.command()
def estimate(
    path: str = typer.Option(".", "--path", help="Path to Terraform/CDK/CFN to price."),
    client_name: str = typer.Option(None, "--client-name", help="Client/engagement name for the report header."),
    logo: str = typer.Option(None, "--logo", help="Path to a logo image embedded in the report header."),
    output_formats: str = typer.Option(",".join(DEFAULT_FORMATS), "--format", help="Formats: html, md, json, pdf."),
    pdf: bool = typer.Option(False, "--pdf", help="Shorthand to add PDF output."),
    pdf_engine: str = typer.Option("weasyprint", "--pdf-engine", help="PDF engine: weasyprint or chromium."),
    out_dir: str = typer.Option("./reports", "--out", help="Output directory for reports."),
    tool_output: bool = typer.Option(False, "--tool-output", help="Stream raw tool output."),
):
    """Pre-deploy cost estimate of IaC on disk (Infracost). No AWS account touched."""
    formats = _resolve_formats(output_formats, pdf)
    logo_uri = _logo_data_uri(logo) if logo else ""
    generated_at = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    console.rule("[bold]Pre-deploy estimate (Infracost)[/bold]")
    tool = InfracostTool(path=path)
    with tempfile.TemporaryDirectory(prefix="costhive-estimate-") as workdir:
        results = _run([tool], None, workdir, tool_output=tool_output)
    projected = 0.0
    if results and isinstance(results[0].raw, dict):
        projected = float(results[0].raw.get("_projected_monthly_cost", 0.0) or 0.0)

    report = build_report(
        results,
        account_id="",
        identity_arn="",
        regions=[],
        generated_at=generated_at,
        client_name=client_name or "",
        logo_data_uri=logo_uri,
        mode="estimate",
        projected_monthly_cost=projected,
    )
    paths = write_reports(report, out_dir, formats=formats, pdf_engine=pdf_engine, console=console)
    _print_estimate_summary(report, paths)
    _fail_on_tool_errors([report])
    raise typer.Exit(code=0)


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _resolve_tools(tools_opt: str, komiser_export, cloudquery_db_url, opencost_export) -> list[str]:
    selected = [t.strip() for t in tools_opt.split(",") if t.strip()]
    # Auto-enable opt-in tools when their input is supplied.
    if komiser_export and "komiser" not in selected:
        selected.append("komiser")
    if cloudquery_db_url and "cloudquery" not in selected:
        selected.append("cloudquery")
    if opencost_export and "opencost" not in selected:
        selected.append("opencost")
    unknown = [t for t in selected if t not in ALL_TOOLS or t == "infracost"]
    if unknown:
        console.print(
            f"[red]Unknown or non-scan tool(s): {', '.join(unknown)} (infracost is the 'estimate' verb).[/red]"
        )
        raise typer.Exit(code=2)
    return selected


def _parse_categories(categories: str | None) -> set[str] | None:
    if not categories:
        return None
    from costhive.models import Category

    valid = {c.value for c in Category}
    requested = {c.strip().lower() for c in categories.split(",") if c.strip()}
    unknown = requested - valid
    if unknown:
        console.print(f"[red]Unknown categories: {', '.join(sorted(unknown))}. Valid: {', '.join(sorted(valid))}[/red]")
        raise typer.Exit(code=2)
    return requested


def _filter_results(results: list[ToolResult], category_filter: set[str] | None) -> list[ToolResult]:
    if not category_filter:
        return results
    for r in results:
        r.findings = [f for f in r.findings if f.category.value in category_filter]
    return results


def _build_scan_tools(
    selected, policy_dir, komiser_export, cloudquery_db_url, cloudquery_spec, opencost_export
) -> list[CostTool]:
    tools: list[CostTool] = []
    for name in selected:
        if name == "opencost":
            tools.append(OpenCostTool(allocation_export=opencost_export))
        else:
            tools.extend(
                build_tools(
                    [name],
                    policy_dir=policy_dir,
                    komiser_export=komiser_export,
                    cloudquery_db_url=cloudquery_db_url,
                    cloudquery_spec=cloudquery_spec,
                )
            )
    return tools


def _resolve_formats(output_formats: str, pdf: bool) -> list[str]:
    formats = [f.strip().lower() for f in output_formats.split(",") if f.strip()]
    if pdf and "pdf" not in formats:
        formats.append("pdf")
    invalid = [f for f in formats if f not in VALID_FORMATS]
    if invalid:
        console.print(f"[red]Unknown format(s): {', '.join(invalid)}. Valid: {', '.join(sorted(VALID_FORMATS))}[/red]")
        raise typer.Exit(code=2)
    return formats


def _note_eks(ctx) -> None:
    detected = discover_eks_clusters(ctx)
    if detected:
        console.print(
            f"[dim]EKS clusters detected: {', '.join(detected)} — OpenCost analysis enabled via export.[/dim]"
        )


def _run(tool_objs: list[CostTool], ctx, workdir: str, tool_output: bool = False):
    results = []
    for tool in tool_objs:
        tool.show_tool_output = tool_output
        console.print(f"▶ running [bold]{tool.name}[/bold] …")
        result = tool.run(ctx, workdir)
        style = {"ok": "green", "skipped": "yellow", "error": "red"}[result.status.value]
        savings = sum(f.estimated_monthly_savings for f in result.findings)
        note = f" — {result.message}" if result.message else ""
        console.print(
            f"  [{style}]{result.status.value}[/{style}] ({len(result.findings)} findings, ${savings:,.2f}/mo){note}"
        )
        results.append(result)
    return results


def _confirm(contexts, selected, client_name, yes):
    lines = []
    if client_name:
        lines.append(f"[bold]Client:[/bold] {client_name}")
    for ctx in contexts:
        lines.append(f"[bold]Account:[/bold] {ctx.identity.account_id}  [dim]{ctx.identity.arn}[/dim]")
    lines.append(f"[bold]Regions:[/bold] {', '.join(contexts[0].regions)}")
    lines.append(f"[bold]Tools:[/bold] {', '.join(selected)}")
    lines.append("[dim]Read-only analysis. Cloud Custodian runs in dry-run — nothing is modified.[/dim]")
    console.print(Panel.fit("\n".join(lines), title="About to analyze", border_style="yellow"))
    if not yes and not typer.confirm("Proceed?", default=True):
        console.print("Aborted.")
        raise typer.Exit(code=0)


def _logo_data_uri(path: str) -> str:
    if not os.path.isfile(path):
        console.print(f"[yellow]Logo not found, ignoring: {path}[/yellow]")
        return ""
    mime = mimetypes.guess_type(path)[0] or "image/png"
    with open(path, "rb") as fh:
        encoded = base64.b64encode(fh.read()).decode()
    return f"data:{mime};base64,{encoded}"


def _maybe_fail_under(reports, threshold):
    if threshold is None:
        return
    total = sum(r.total_monthly_savings for r in reports if not r.is_rollup)
    if total >= threshold:
        console.print(
            f"[red]✗ ${total:,.2f}/mo in identified savings is at or above the --fail-under "
            f"threshold of ${threshold:,.2f} — failing as a CI cost gate.[/red]"
        )
        raise typer.Exit(code=3)


def _fail_on_tool_errors(reports):
    errors = [t for report in reports for t in report.tool_errors]
    if not errors:
        return
    console.print(
        "[red]Run incomplete: one or more tools failed. Reports were written, but findings are incomplete.[/red]"
    )
    for error in errors:
        note = f" — {error.message}" if error.message else ""
        console.print(f"  [red]{error.name}[/red]{note}")
    raise typer.Exit(code=1)


def _print_summary(report, paths: dict[str, str]):
    console.print(
        f"\n[bold green]💰 Total estimated monthly savings: "
        f"${report.total_monthly_savings:,.2f}[/bold green] "
        f"[dim](${report.annual_savings:,.2f}/yr, {report.total} opportunities)[/dim]"
    )
    if report.by_category:
        table = Table(title="Savings by category")
        table.add_column("Category")
        table.add_column("Count", justify="right")
        table.add_column("Monthly", justify="right")
        for c in report.by_category:
            table.add_row(c.label, str(c.count), f"${c.savings:,.2f}")
        console.print(table)
    console.print("\n[bold]Reports written:[/bold]")
    for fmt, path in paths.items():
        console.print(f"  • {fmt}: [cyan]{path}[/cyan]")


def _print_estimate_summary(report, paths: dict[str, str]):
    console.print(
        f"\n[bold cyan]Projected monthly cost: ${report.projected_monthly_cost:,.2f}[/bold cyan] "
        f"[dim](${report.projected_monthly_cost * 12:,.2f}/yr, {report.total} resources)[/dim]"
    )
    console.print("\n[bold]Reports written:[/bold]")
    for fmt, path in paths.items():
        console.print(f"  • {fmt}: [cyan]{path}[/cyan]")


if __name__ == "__main__":  # pragma: no cover
    sys.exit(app())
