"""Per-tool output parsers -> unified `SavingsFinding` list.

Each function takes a tool's native output (already loaded into Python objects) and
returns normalized findings. Parsers are intentionally defensive: tool output
schemas drift between versions, so we read fields by best-effort and never assume a
key is present. Anything we cannot map degrades to a sensible default rather than
raising.

The dollar figure is the sort key everywhere downstream, so every parser makes a
best effort to attach `estimated_monthly_savings` and a `confidence`.
"""

from __future__ import annotations

import re
from typing import Any

from costhive.models import Category, Confidence, SavingsFinding


def _get(d: dict, *keys: str, default: Any = "") -> Any:
    """Return the first present value among keys (case-insensitive)."""
    if not isinstance(d, dict):
        return default
    lowered = {k.lower(): v for k, v in d.items()}
    for k in keys:
        if k in d:
            return d[k]
        if k.lower() in lowered:
            return lowered[k.lower()]
    return default


_NUM_RE = re.compile(r"-?\d+(?:[.,]\d+)?")


def _num(value: Any, default: float = 0.0) -> float:
    """Coerce currency-ish values ("$8.00", "8,50", 8) to float. Never raises."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    if value is None:
        return default
    m = _NUM_RE.search(str(value).replace(",", "."))
    if not m:
        return default
    try:
        return float(m.group())
    except ValueError:
        return default


# --------------------------------------------------------------------------- #
# Steampipe — we run SQL over live AWS APIs. Our FinOps queries (queries/*.sql)
# are authored to emit a stable column contract, so the parser is a direct map.
# `steampipe query --output json` yields a list of row objects (or {"rows":[...]}).
# --------------------------------------------------------------------------- #
def parse_steampipe(data: list[dict] | dict, account_id: str = "") -> list[SavingsFinding]:
    rows = data.get("rows", []) if isinstance(data, dict) else data
    findings: list[SavingsFinding] = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        findings.append(
            SavingsFinding(
                tool="steampipe",
                category=Category.parse(str(_get(row, "category", default="other"))),
                title=str(_get(row, "title", "check", default="")),
                description=str(_get(row, "description", "reason", default="")),
                estimated_monthly_savings=_num(_get(row, "estimated_monthly_savings", "monthly_savings", "savings")),
                confidence=Confidence.parse(_get(row, "confidence", default="medium")),
                resource=str(_get(row, "resource", "arn", "resource_id", "id", default="")),
                service=str(_get(row, "service", default="")),
                region=str(_get(row, "region", default="")),
                recommended_action=str(_get(row, "recommended_action", "action", "remediation", default="")),
                account_id=str(_get(row, "account_id", default=account_id)),
            )
        )
    return findings


# --------------------------------------------------------------------------- #
# CloudQuery — same idea as Steampipe but SQL over a synced inventory DB. The
# wrapper runs the same FinOps query contract, so rows share the column schema.
# --------------------------------------------------------------------------- #
def parse_cloudquery(data: list[dict] | dict, account_id: str = "") -> list[SavingsFinding]:
    findings = parse_steampipe(data, account_id=account_id)
    for f in findings:
        f.tool = "cloudquery"
    return findings


# --------------------------------------------------------------------------- #
# Cloud Custodian — policy-as-code. Each policy matches AWS resources; it does not
# itself compute dollars, so our policy packs annotate each policy with a category
# and a per-resource monthly-savings estimate (policy `metadata`). The wrapper
# assembles one "policy run" dict per policy; here we fan it out to one finding per
# matched resource.
# --------------------------------------------------------------------------- #
def parse_custodian(policy_runs: list[dict], account_id: str = "") -> list[SavingsFinding]:
    findings: list[SavingsFinding] = []
    for run in policy_runs or []:
        if not isinstance(run, dict):
            continue
        category = Category.parse(str(_get(run, "category", default="other")))
        per_resource = _num(_get(run, "monthly_savings_each", "monthly_savings", default=0.0))
        confidence = Confidence.parse(_get(run, "confidence", default="medium"))
        action = str(_get(run, "recommended_action", "action", default=""))
        description = str(_get(run, "description", default=""))
        region = str(_get(run, "region", default=""))
        service = str(_get(run, "service", "resource_type", default=""))
        policy = str(_get(run, "policy", "name", default=""))
        resources = _get(run, "resources", default=[])
        if not isinstance(resources, list):
            continue
        for res in resources:
            rid = _custodian_resource_id(res)
            findings.append(
                SavingsFinding(
                    tool="custodian",
                    category=category,
                    title=policy or f"{category.label} opportunity",
                    description=description or f"Matched by Cloud Custodian policy '{policy}'.",
                    estimated_monthly_savings=per_resource,
                    confidence=confidence,
                    resource=rid,
                    service=service,
                    region=str(_get(res, "Region", "region", default=region)) if isinstance(res, dict) else region,
                    recommended_action=action,
                    account_id=account_id,
                )
            )
    return findings


def _custodian_resource_id(res: Any) -> str:
    if not isinstance(res, dict):
        return str(res)
    for key in (
        "VolumeId",
        "InstanceId",
        "AllocationId",
        "SnapshotId",
        "DBInstanceIdentifier",
        "LoadBalancerName",
        "BucketName",
        "Name",
        "Arn",
        "id",
    ):
        val = _get(res, key)
        if val:
            return str(val)
    return ""


# --------------------------------------------------------------------------- #
# Komiser — visual inventory + cost/governance. Its resources carry `cost` (monthly)
# and `tags`. Komiser's cost-optimization angle for v1 is governance: high-cost
# resources with no cost-allocation tags. Savings is $0 (it's a tagging gap, not a
# deletable resource), but surfacing it is the point.
# --------------------------------------------------------------------------- #
def parse_komiser(
    data: list[dict] | dict, account_id: str = "", untagged_threshold: float = 0.0
) -> list[SavingsFinding]:
    rows = data.get("resources", data.get("rows", [])) if isinstance(data, dict) else data
    findings: list[SavingsFinding] = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        tags = _get(row, "tags", default=[])
        has_tags = bool(tags) if isinstance(tags, (list, dict)) else bool(tags)
        cost = _num(_get(row, "cost", "monthly_cost", default=0.0))
        if has_tags or cost < untagged_threshold:
            continue
        name = str(_get(row, "name", "resourceId", "id", default=""))
        service = str(_get(row, "service", default=""))
        findings.append(
            SavingsFinding(
                tool="komiser",
                category=Category.UNTAGGED,
                title=f"Untagged resource: {name or service}",
                description=(
                    f"{service or 'Resource'} '{name}' costs ~${cost:.2f}/mo but has no cost-allocation tags, "
                    "so its spend cannot be attributed to a team or project."
                ),
                estimated_monthly_savings=0.0,  # governance finding, not directly deletable
                confidence=Confidence.HIGH,
                resource=name,
                service=service,
                region=str(_get(row, "region", default="")),
                recommended_action="Apply cost-allocation tags (owner, environment, cost-center) for chargeback.",
                account_id=str(_get(row, "account", "account_id", default=account_id)),
            )
        )
    return findings


# --------------------------------------------------------------------------- #
# Infracost — pre-deploy IaC cost estimate. This is projected *spend*, not savings:
# `infracost breakdown --format json` yields projects -> breakdown -> resources with
# `monthlyCost`. We surface the most expensive resources so the user sees cost before
# it ships. Savings stays $0; the projected cost rides in the description.
# --------------------------------------------------------------------------- #
def parse_infracost(data: dict) -> list[SavingsFinding]:
    findings: list[SavingsFinding] = []
    if not isinstance(data, dict):
        return findings
    for project in data.get("projects", []) or []:
        if not isinstance(project, dict):
            continue
        project_name = str(project.get("name", ""))
        breakdown = project.get("breakdown", {}) or {}
        for res in breakdown.get("resources", []) or []:
            if not isinstance(res, dict):
                continue
            monthly = _num(res.get("monthlyCost"))
            if monthly <= 0:
                continue
            name = str(res.get("name", ""))
            findings.append(
                SavingsFinding(
                    tool="infracost",
                    category=Category.OTHER,
                    title=f"Projected cost: {name}",
                    description=(
                        f"Terraform resource '{name}'"
                        + (f" in {project_name}" if project_name else "")
                        + f" is projected to cost ${monthly:.2f}/mo once deployed."
                    ),
                    estimated_monthly_savings=0.0,  # projected spend, not a saving
                    confidence=Confidence.HIGH,
                    resource=name,
                    service=str(res.get("resourceType", "")),
                    recommended_action="Review before deploy — rightsize or drop if not required.",
                )
            )
    return findings


def infracost_total(data: dict) -> float:
    """Total projected monthly cost across all Infracost projects."""
    if not isinstance(data, dict):
        return 0.0
    total = _num(data.get("totalMonthlyCost"))
    if total:
        return round(total, 2)
    running = 0.0
    for project in data.get("projects", []) or []:
        breakdown = project.get("breakdown", {}) if isinstance(project, dict) else {}
        running += _num(breakdown.get("totalMonthlyCost"))
    return round(running, 2)
