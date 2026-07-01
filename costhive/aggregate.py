"""Aggregate normalized savings findings across tools: dedup, rank, summarize.

For the FinOps/consultant audience the report *is* the product, so this layer also
computes the money-first extras the report surfaces: total estimated monthly
savings (the headline number), savings broken down by category and by risk (safe vs
judgment-call), the top opportunities by dollar impact, and the "quick wins" (high
savings + low risk + defensible confidence) called out separately.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from costhive import __version__
from costhive.models import Category, Confidence, Risk, SavingsFinding
from costhive.tools.base import ToolResult


@dataclass
class ToolSummary:
    name: str
    status: str
    findings: int
    savings: float = 0.0
    message: str = ""
    version: str = ""


@dataclass
class CategoryBreakdown:
    category: str
    label: str
    count: int
    savings: float

    @property
    def annual(self) -> float:
        return round(self.savings * 12, 2)


@dataclass
class RiskBreakdown:
    """Savings split by how safe it is to act — the "don't overpromise" view."""

    risk: str
    label: str
    count: int
    savings: float

    @property
    def annual(self) -> float:
        return round(self.savings * 12, 2)


@dataclass
class Report:
    """Everything the report layer needs, already aggregated and sorted."""

    account_id: str
    identity_arn: str
    regions: list[str]
    generated_at: str
    findings: list[SavingsFinding]
    total_monthly_savings: float
    by_category: list[CategoryBreakdown]
    tools: list[ToolSummary]
    by_risk: list[RiskBreakdown] = field(default_factory=list)
    top_opportunities: list[SavingsFinding] = field(default_factory=list)
    quick_wins: list[SavingsFinding] = field(default_factory=list)
    currency: str = "USD"
    # Consultant / evidence metadata.
    client_name: str = ""
    logo_data_uri: str = ""
    tool_version: str = __version__
    accounts: list[str] = field(default_factory=list)  # populated for roll-up reports
    is_rollup: bool = False
    # Estimate (Infracost pre-deploy) mode: projected spend, not savings.
    mode: str = "scan"  # "scan" (live account) | "estimate" (pre-deploy IaC)
    projected_monthly_cost: float = 0.0
    cost_data_notes: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.findings)

    @property
    def annual_savings(self) -> float:
        return round(self.total_monthly_savings * 12, 2)

    @property
    def safe_savings(self) -> float:
        """Monthly savings from reversible, no-impact actions — the number a client
        can bank with the least risk."""
        return round(sum(f.estimated_monthly_savings for f in self.findings if f.risk is Risk.SAFE), 2)

    @property
    def judgment_savings(self) -> float:
        """Monthly savings that require a human judgment call (rightsizing, deleting
        backups) — real, but don't promise them as banked."""
        return round(sum(f.estimated_monthly_savings for f in self.findings if f.risk is Risk.JUDGMENT), 2)

    @property
    def tool_errors(self) -> list[ToolSummary]:
        return [t for t in self.tools if t.status == "error"]

    @property
    def has_tool_errors(self) -> bool:
        return bool(self.tool_errors)

    def to_dict(self) -> dict:
        return {
            "client_name": self.client_name,
            "mode": self.mode,
            "account_id": self.account_id,
            "accounts": self.accounts,
            "identity_arn": self.identity_arn,
            "regions": self.regions,
            "generated_at": self.generated_at,
            "costhive_version": self.tool_version,
            "currency": self.currency,
            "summary": {
                "total_findings": self.total,
                "total_monthly_savings": self.total_monthly_savings,
                "annual_savings": self.annual_savings,
                "projected_monthly_cost": self.projected_monthly_cost,
                "run_complete": not self.has_tool_errors,
                "safe_savings": self.safe_savings,
                "judgment_savings": self.judgment_savings,
                "by_category": [vars(c) | {"annual": c.annual} for c in self.by_category],
                "by_risk": [vars(r) | {"annual": r.annual} for r in self.by_risk],
                "cost_data_notes": self.cost_data_notes,
            },
            "tools": [vars(t) for t in self.tools],
            "findings": [f.to_dict() for f in self.findings],
        }


def dedup(findings: list[SavingsFinding]) -> list[SavingsFinding]:
    """Collapse the same resource+category reported by multiple tools.

    When two tools flag the same opportunity (e.g. an unattached EBS volume surfaced
    by both Steampipe and Custodian), keep the one with the higher savings estimate
    and record the contributing tools on the survivor. This avoids double-counting
    dollars in the headline total.
    """
    best: dict[str, SavingsFinding] = {}
    for f in findings:
        key = f.dedup_key
        existing = best.get(key)
        if existing is None:
            best[key] = f
            continue
        winner, loser = (
            (f, existing)
            if (f.estimated_monthly_savings, int(f.confidence))
            > (existing.estimated_monthly_savings, int(existing.confidence))
            else (existing, f)
        )
        tools = sorted({existing.tool, f.tool})
        if len(tools) > 1:
            winner.title = winner.title or loser.title
            marker = "confirmed by " + " + ".join(tools)
            if marker not in winner.description:
                winner.description = (winner.description + f" ({marker})").strip()
        best[key] = winner
    return list(best.values())


def rank(findings: list[SavingsFinding]) -> list[SavingsFinding]:
    """Sort by dollar impact — highest estimated monthly savings first, then
    confidence, then tool/category for stable output."""
    return sorted(
        findings,
        key=lambda f: (-f.estimated_monthly_savings, -int(f.confidence), f.tool, f.category.value),
    )


def category_breakdown(findings: list[SavingsFinding]) -> list[CategoryBreakdown]:
    """Per-category count + savings, ordered by savings desc (money-first)."""
    tally: dict[Category, CategoryBreakdown] = {}
    for f in findings:
        cb = tally.get(f.category)
        if cb is None:
            cb = CategoryBreakdown(category=f.category.value, label=f.category.label, count=0, savings=0.0)
            tally[f.category] = cb
        cb.count += 1
        cb.savings = round(cb.savings + f.estimated_monthly_savings, 2)
    return sorted(tally.values(), key=lambda c: (-c.savings, -c.count, c.label))


def risk_breakdown(findings: list[SavingsFinding]) -> list[RiskBreakdown]:
    """Per-risk-level count + savings, ordered safest-first (SAFE, MODERATE, JUDGMENT)."""
    tally: dict[Risk, RiskBreakdown] = {}
    for f in findings:
        rb = tally.get(f.risk)
        if rb is None:
            rb = RiskBreakdown(risk=f.risk.name.lower(), label=f.risk.label, count=0, savings=0.0)
            tally[f.risk] = rb
        rb.count += 1
        rb.savings = round(rb.savings + f.estimated_monthly_savings, 2)
    return [tally[r] for r in Risk if r in tally]


def quick_wins(findings: list[SavingsFinding], limit: int = 5, min_savings: float = 1.0) -> list[SavingsFinding]:
    """Low-risk, non-trivial, defensible savings — the "do these first" list.

    Per the consultant addendum (§4), quick wins are "high savings + low effort/risk".
    We deliberately exclude JUDGMENT-call actions (rightsizing prod, deleting backups)
    and LOW-confidence estimates, so the consultant never fronts a shaky or risky
    number as an easy win.
    """
    wins = [
        f
        for f in findings
        if f.risk <= Risk.MODERATE and f.confidence >= Confidence.MEDIUM and f.estimated_monthly_savings >= min_savings
    ]
    return rank(wins)[:limit]


def _summaries(results: list[ToolResult]) -> tuple[list[SavingsFinding], list[ToolSummary]]:
    all_findings: list[SavingsFinding] = []
    summaries: list[ToolSummary] = []
    for r in results:
        savings = round(sum(f.estimated_monthly_savings for f in r.findings), 2)
        summaries.append(
            ToolSummary(
                name=r.tool,
                status=r.status.value,
                findings=len(r.findings),
                savings=savings,
                message=r.message,
                version=r.version,
            )
        )
        all_findings.extend(r.findings)
    return all_findings, summaries


def build_report(
    results: list[ToolResult],
    *,
    account_id: str,
    identity_arn: str,
    regions: list[str],
    generated_at: str,
    client_name: str = "",
    logo_data_uri: str = "",
    mode: str = "scan",
    projected_monthly_cost: float = 0.0,
    cost_data_notes: list[str] | None = None,
    top_n: int = 10,
) -> Report:
    all_findings, summaries = _summaries(results)
    deduped = rank(dedup(all_findings))
    total_savings = round(sum(f.estimated_monthly_savings for f in deduped), 2)
    currency = deduped[0].currency if deduped else "USD"

    return Report(
        account_id=account_id,
        identity_arn=identity_arn,
        regions=regions,
        generated_at=generated_at,
        findings=deduped,
        total_monthly_savings=total_savings,
        by_category=category_breakdown(deduped),
        by_risk=risk_breakdown(deduped),
        tools=summaries,
        top_opportunities=deduped[:top_n],
        quick_wins=quick_wins(deduped),
        currency=currency,
        client_name=client_name,
        logo_data_uri=logo_data_uri,
        mode=mode,
        projected_monthly_cost=projected_monthly_cost,
        cost_data_notes=cost_data_notes or [],
    )


def build_rollup(
    reports: list[Report], *, generated_at: str, client_name: str = "", logo_data_uri: str = "", top_n: int = 10
) -> Report:
    """Combine per-account reports into one roll-up across all analyzed accounts.

    Findings keep their account_id so the consultant can trace each back; the roll-up
    is the leadership-level "total savings across the estate" view. No cross-account
    dedup: the same resource id in two accounts is genuinely distinct.
    """
    combined: list[SavingsFinding] = []
    tool_status: dict[str, ToolSummary] = {}
    accounts: list[str] = []
    regions: set[str] = set()
    notes: list[str] = []
    for rep in reports:
        accounts.append(rep.account_id)
        regions.update(rep.regions)
        combined.extend(rep.findings)
        notes.extend(rep.cost_data_notes)
        for t in rep.tools:
            agg = tool_status.get(t.name)
            if agg is None:
                tool_status[t.name] = ToolSummary(t.name, t.status, t.findings, t.savings, t.message, t.version)
            else:
                agg.findings += t.findings
                agg.savings = round(agg.savings + t.savings, 2)

    ranked = rank(combined)
    total_savings = round(sum(f.estimated_monthly_savings for f in ranked), 2)

    return Report(
        account_id="multiple",
        identity_arn="",
        regions=sorted(regions),
        generated_at=generated_at,
        findings=ranked,
        total_monthly_savings=total_savings,
        by_category=category_breakdown(ranked),
        by_risk=risk_breakdown(ranked),
        tools=list(tool_status.values()),
        top_opportunities=ranked[:top_n],
        quick_wins=quick_wins(ranked),
        currency=ranked[0].currency if ranked else "USD",
        client_name=client_name,
        logo_data_uri=logo_data_uri,
        accounts=accounts,
        is_rollup=True,
        cost_data_notes=sorted(set(notes)),
    )
