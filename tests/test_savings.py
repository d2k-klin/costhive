"""Savings-estimation & $-ranking tests — CostHive's highest-value guard.

Feeds the committed, sanitized tool-output fixtures through the real parsers and
aggregator and asserts the dollar math and ranking are correct and stable. Wrong
numbers here mean wrong numbers in a client's report, so these assertions are exact.
"""

from costhive.aggregate import build_report
from costhive.normalize import (
    infracost_total,
    parse_custodian,
    parse_infracost,
    parse_komiser,
    parse_steampipe,
)
from costhive.tools.base import ToolResult, ToolStatus
from costhive.tools.opencost import _parse_allocation

from .conftest import load_fixture


def _scan_report():
    """Build the report from all live-account fixtures, as a real scan would."""
    steampipe = parse_steampipe(load_fixture("steampipe_sample.json"), account_id="123456789012")
    custodian = parse_custodian(load_fixture("custodian_sample.json"), account_id="123456789012")
    komiser = parse_komiser(load_fixture("komiser_sample.json"), account_id="123456789012")
    opencost = _parse_allocation(load_fixture("opencost_sample.json"), cluster="prod-eks")
    results = [
        ToolResult("steampipe", ToolStatus.OK, findings=steampipe),
        ToolResult("custodian", ToolStatus.OK, findings=custodian),
        ToolResult("komiser", ToolStatus.OK, findings=komiser),
        ToolResult("opencost", ToolStatus.OK, findings=opencost),
    ]
    return build_report(
        results,
        account_id="123456789012",
        identity_arn="arn:aws:iam::123456789012:role/CostHiveAudit",
        regions=["us-east-1"],
        generated_at="2026-07-01 00:00:00 UTC",
    )


def test_total_savings_is_exact():
    # steampipe 18.00 + custodian 180.00 + komiser 0 + opencost 70.00
    report = _scan_report()
    assert report.total_monthly_savings == 268.0
    assert report.annual_savings == 3216.0
    assert report.total == 8


def test_safe_vs_judgment_split_is_exact():
    report = _scan_report()
    assert report.safe_savings == 11.6  # unattached EBS 8 + EIP 3.6 (untagged is $0)
    assert report.judgment_savings == 250.0  # 2×EC2 (60) + RDS (120) + OpenCost (70)


def test_ranking_is_by_dollar_impact():
    report = _scan_report()
    top = report.top_opportunities
    assert [round(f.estimated_monthly_savings, 2) for f in top[:4]] == [120.0, 70.0, 30.0, 30.0]
    # Highest-value finding is the idle RDS instance.
    assert top[0].resource == "db-legacy-1"


def test_category_breakdown_totals():
    report = _scan_report()
    cats = {c.category: c for c in report.by_category}
    assert cats["rightsizing"].savings == 130.0 and cats["rightsizing"].count == 3  # 2 EC2 + OpenCost ns
    assert cats["idle"].savings == 120.0
    assert cats["unused"].savings == 11.6 and cats["unused"].count == 2
    assert cats["storage_class"].savings == 6.4
    assert cats["untagged"].savings == 0.0
    # Ordered by savings, money-first.
    assert [c.category for c in report.by_category][:2] == ["rightsizing", "idle"]


def test_risk_breakdown_totals():
    report = _scan_report()
    risks = {r.risk: r for r in report.by_risk}
    assert risks["safe"].savings == 11.6 and risks["safe"].count == 3
    assert risks["moderate"].savings == 6.4
    assert risks["judgment"].savings == 250.0 and risks["judgment"].count == 4


def test_quick_wins_are_low_risk_high_value():
    report = _scan_report()
    # Safe/moderate, >= medium confidence, >= $1 — the judgment-call items are excluded.
    assert [f.resource for f in report.quick_wins] == [
        "vol-0aaaaaaaaaaaaaaa1",  # $8.00 safe
        "vol-0ccccccccccccccc3",  # $6.40 moderate
        "eipalloc-0bbbbbbbbbbbbbbb2",  # $3.60 safe
    ]


def test_infracost_estimate_is_projected_not_savings():
    data = load_fixture("infracost_sample.json")
    findings = parse_infracost(data)
    assert infracost_total(data) == 512.5
    # Projected spend never inflates savings totals.
    assert all(f.estimated_monthly_savings == 0.0 for f in findings)
    assert len(findings) == 2  # the $0 resource is skipped
