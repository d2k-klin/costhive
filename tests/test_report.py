import json

from costhive.aggregate import build_report
from costhive.models import Category, Confidence, Risk, SavingsFinding
from costhive.report.generator import render_html, render_md, write_reports
from costhive.tools.base import ToolResult, ToolStatus


def _report(mode="scan", projected=0.0):
    findings = [
        SavingsFinding(
            "steampipe",
            Category.UNUSED,
            "Unattached EBS volume",
            "available",
            estimated_monthly_savings=40.0,
            confidence=Confidence.HIGH,
            risk=Risk.SAFE,
            resource="vol-1",
            service="ebs",
        ),
        SavingsFinding(
            "custodian",
            Category.RIGHTSIZING,
            "Oversized instance",
            "low CPU",
            estimated_monthly_savings=12.5,
            confidence=Confidence.MEDIUM,
            risk=Risk.JUDGMENT,
            resource="i-2",
            service="ec2",
        ),
    ]
    return build_report(
        [ToolResult("steampipe", ToolStatus.OK, findings=findings)],
        account_id="123456789012",
        identity_arn="arn:aws:iam::123456789012:role/CostAudit",
        regions=["us-east-1"],
        generated_at="2026-07-01 00:00:00 UTC",
        client_name="Acme Corp",
        mode=mode,
        projected_monthly_cost=projected,
    )


def test_render_html_contains_headline_and_money():
    html = render_html(_report())
    assert "CostHive Cost-Optimization Report" in html
    assert "Total estimated monthly savings" in html
    assert "$52.50" in html  # 40 + 12.5
    assert "Acme Corp" in html
    assert "Quick wins" in html  # the high-confidence EBS finding
    # Safe-vs-judgment split (addendum §5): $40 safe, $12.50 judgment.
    assert "Safe to reclaim now" in html
    assert "$40.00" in html
    assert "Needs a judgment call" in html


def test_render_md_contains_category_table():
    md = render_md(_report())
    assert "Total estimated monthly savings" in md
    assert "$52.50" in md
    assert "Savings by category" in md
    assert "Unused / orphaned" in md


def test_estimate_mode_shows_projected_cost():
    html = render_html(_report(mode="estimate", projected=742.5))
    assert "Projected monthly cost" in html
    assert "$742.50" in html


def test_write_reports_emits_all_formats(tmp_path):
    paths = write_reports(_report(), str(tmp_path), formats=["html", "md", "json"])
    assert set(paths) == {"html", "md", "json"}
    for p in paths.values():
        assert (tmp_path / p.split("/")[-1]).exists()
    data = json.loads((tmp_path / "findings.json").read_text())
    assert data["summary"]["total_monthly_savings"] == 52.5
    assert data["mode"] == "scan"
    assert data["findings"][0]["estimated_monthly_savings"] == 40.0


def test_pdf_missing_engine_does_not_abort_other_formats(tmp_path):
    # weasyprint likely absent in CI; PDF is skipped but html/md still written.
    paths = write_reports(_report(), str(tmp_path), formats=["html", "pdf"])
    assert "html" in paths
