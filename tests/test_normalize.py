from costhive.models import Category, Confidence, Risk
from costhive.normalize import (
    infracost_total,
    parse_cloudquery,
    parse_custodian,
    parse_infracost,
    parse_komiser,
    parse_steampipe,
)


def test_parse_steampipe_maps_column_contract():
    rows = [
        {
            "title": "Unattached EBS volume",
            "description": "available",
            "category": "unused",
            "service": "ebs",
            "region": "us-east-1",
            "resource": "vol-123",
            "estimated_monthly_savings": "8.00",
            "confidence": "high",
            "recommended_action": "Delete it",
            "account_id": "123456789012",
        }
    ]
    f = parse_steampipe(rows)[0]
    assert f.tool == "steampipe"
    assert f.category is Category.UNUSED
    assert f.estimated_monthly_savings == 8.0
    assert f.confidence is Confidence.HIGH
    assert f.resource == "vol-123"
    assert f.account_id == "123456789012"


def test_parse_steampipe_accepts_rows_wrapper_and_defaults_account():
    data = {"rows": [{"title": "x", "category": "idle", "estimated_monthly_savings": 3}]}
    f = parse_steampipe(data, account_id="999")[0]
    assert f.category is Category.IDLE
    assert f.account_id == "999"


def test_parse_steampipe_explicit_risk_wins_else_category_default():
    # Explicit risk column overrides the per-category default.
    f = parse_steampipe([{"title": "x", "category": "idle", "risk": "safe"}])[0]
    assert f.risk is Risk.SAFE
    # No risk column: 'unused' defaults to SAFE, 'rightsizing' to JUDGMENT.
    assert parse_steampipe([{"title": "x", "category": "unused"}])[0].risk is Risk.SAFE
    assert parse_steampipe([{"title": "x", "category": "rightsizing"}])[0].risk is Risk.JUDGMENT


def test_parse_cloudquery_relabels_tool():
    rows = [{"title": "x", "category": "unused", "estimated_monthly_savings": 1}]
    f = parse_cloudquery(rows)[0]
    assert f.tool == "cloudquery"


def test_parse_custodian_fans_out_per_resource():
    runs = [
        {
            "policy": "ebs-unattached",
            "category": "unused",
            "monthly_savings_each": 8.0,
            "confidence": "high",
            "recommended_action": "Delete",
            "service": "ebs",
            "resources": [{"VolumeId": "vol-1"}, {"VolumeId": "vol-2"}],
        }
    ]
    runs[0]["risk"] = "safe"
    findings = parse_custodian(runs, account_id="123")
    assert len(findings) == 2
    assert all(f.tool == "custodian" and f.category is Category.UNUSED for f in findings)
    assert {f.resource for f in findings} == {"vol-1", "vol-2"}
    assert all(f.estimated_monthly_savings == 8.0 for f in findings)
    assert all(f.risk is Risk.SAFE for f in findings)


def test_parse_komiser_flags_only_untagged():
    data = {
        "resources": [
            {"name": "tagged-box", "service": "ec2", "cost": 100, "tags": [{"key": "owner"}]},
            {"name": "orphan-box", "service": "ec2", "cost": 50, "tags": [], "region": "eu-central-1"},
        ]
    }
    findings = parse_komiser(data, account_id="123")
    assert len(findings) == 1
    f = findings[0]
    assert f.category is Category.UNTAGGED
    assert f.resource == "orphan-box"
    assert f.estimated_monthly_savings == 0.0  # governance, not deletable
    assert f.risk is Risk.SAFE  # applying tags never affects a workload


def test_parse_infracost_surfaces_projected_cost():
    data = {
        "totalMonthlyCost": "742.50",
        "projects": [
            {
                "name": "prod",
                "breakdown": {
                    "resources": [
                        {"name": "aws_instance.web", "resourceType": "aws_instance", "monthlyCost": "500.00"},
                        {"name": "aws_db_instance.db", "resourceType": "aws_db_instance", "monthlyCost": "242.50"},
                        {"name": "aws_iam_role.free", "monthlyCost": "0"},
                    ]
                },
            }
        ],
    }
    findings = parse_infracost(data)
    assert len(findings) == 2  # zero-cost resource skipped
    assert all(f.tool == "infracost" and f.estimated_monthly_savings == 0.0 for f in findings)
    assert "500.00" in findings[0].description
    assert infracost_total(data) == 742.50


def test_infracost_total_falls_back_to_project_sum():
    data = {
        "projects": [
            {"breakdown": {"totalMonthlyCost": "10"}},
            {"breakdown": {"totalMonthlyCost": "5.5"}},
        ]
    }
    assert infracost_total(data) == 15.5


def test_parsers_tolerate_garbage():
    assert parse_steampipe([{"unexpected": "shape"}])  # does not raise
    assert parse_steampipe(["not a dict", 5, None]) == []
    assert parse_custodian([{"resources": "not-a-list"}]) == []
    assert parse_infracost({"projects": ["bad", None]}) == []
    assert parse_komiser({"resources": [None, 5]}) == []
