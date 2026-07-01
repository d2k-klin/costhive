from costhive.aggregate import build_report, build_rollup, category_breakdown, dedup, quick_wins, rank
from costhive.models import Category, Confidence, SavingsFinding
from costhive.tools.base import ToolResult, ToolStatus


def _f(tool, savings, conf=Confidence.MEDIUM, cat=Category.UNUSED, resource="vol-x", service="ebs"):
    return SavingsFinding(
        tool=tool,
        category=cat,
        title=f"{tool} finding",
        description="d",
        estimated_monthly_savings=savings,
        confidence=conf,
        service=service,
        resource=resource,
    )


def test_dedup_keeps_higher_savings_and_marks_confirmation():
    findings = [_f("steampipe", 8.0), _f("custodian", 5.0)]
    out = dedup(findings)
    assert len(out) == 1
    assert out[0].estimated_monthly_savings == 8.0
    assert "confirmed by" in out[0].description


def test_dedup_distinct_resources_not_merged():
    out = dedup([_f("steampipe", 8.0, resource="vol-1"), _f("steampipe", 3.0, resource="vol-2")])
    assert len(out) == 2


def test_rank_orders_by_savings_then_confidence():
    findings = [
        _f("a", 5.0, resource="r1"),
        _f("b", 50.0, resource="r2"),
        _f("c", 5.0, conf=Confidence.HIGH, resource="r3"),
    ]
    out = rank(findings)
    assert out[0].estimated_monthly_savings == 50.0
    # Among the two $5 findings, the higher-confidence one comes first.
    fives = [f for f in out if f.estimated_monthly_savings == 5.0]
    assert fives[0].confidence is Confidence.HIGH


def test_category_breakdown_sums_and_sorts():
    findings = [
        _f("a", 10.0, cat=Category.UNUSED, resource="r1"),
        _f("b", 5.0, cat=Category.UNUSED, resource="r2"),
        _f("c", 30.0, cat=Category.RIGHTSIZING, resource="r3"),
    ]
    cats = category_breakdown(findings)
    assert cats[0].category == "rightsizing"
    assert cats[0].savings == 30.0
    unused = next(c for c in cats if c.category == "unused")
    assert unused.count == 2 and unused.savings == 15.0


def test_quick_wins_only_high_confidence_above_threshold():
    findings = [
        _f("a", 100.0, conf=Confidence.LOW, resource="r1"),
        _f("b", 20.0, conf=Confidence.HIGH, resource="r2"),
        _f("c", 0.5, conf=Confidence.HIGH, resource="r3"),
    ]
    wins = quick_wins(findings)
    assert [w.resource for w in wins] == ["r2"]  # low-conf and sub-$1 excluded


def test_build_report_totals_and_sections():
    results = [
        ToolResult(
            "steampipe",
            ToolStatus.OK,
            findings=[
                _f("steampipe", 40.0, conf=Confidence.HIGH, resource="r1"),
                _f("steampipe", 10.0, resource="r2"),
            ],
        ),
        ToolResult("komiser", ToolStatus.SKIPPED, message="no export"),
    ]
    report = build_report(
        results,
        account_id="123",
        identity_arn="arn:aws:iam::123:user/me",
        regions=["us-east-1"],
        generated_at="now",
    )
    assert report.total == 2
    assert report.total_monthly_savings == 50.0
    assert report.annual_savings == 600.0
    assert report.top_opportunities[0].estimated_monthly_savings == 40.0
    assert len(report.quick_wins) == 1
    names = {t.name: t.status for t in report.tools}
    assert names["komiser"] == "skipped"
    assert report.to_dict()["summary"]["total_monthly_savings"] == 50.0


def test_build_report_marks_tool_errors():
    report = build_report(
        [ToolResult("steampipe", ToolStatus.ERROR, message="timed out")],
        account_id="123",
        identity_arn="arn",
        regions=["us-east-1"],
        generated_at="now",
    )
    assert report.has_tool_errors is True
    assert report.tool_errors[0].name == "steampipe"
    assert report.to_dict()["summary"]["run_complete"] is False


def test_build_rollup_combines_accounts_without_cross_dedup():
    r1 = build_report(
        [ToolResult("steampipe", ToolStatus.OK, findings=[_f("steampipe", 10.0, resource="vol-1")])],
        account_id="111",
        identity_arn="a",
        regions=["us-east-1"],
        generated_at="now",
    )
    r2 = build_report(
        [ToolResult("steampipe", ToolStatus.OK, findings=[_f("steampipe", 20.0, resource="vol-1")])],
        account_id="222",
        identity_arn="b",
        regions=["eu-central-1"],
        generated_at="now",
    )
    rollup = build_rollup([r1, r2], generated_at="now")
    assert rollup.is_rollup
    assert rollup.accounts == ["111", "222"]
    assert rollup.total == 2  # same resource id in two accounts stays distinct
    assert rollup.total_monthly_savings == 30.0
