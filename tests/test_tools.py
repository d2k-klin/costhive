from costhive.models import Category
from costhive.tools import ALL_TOOLS, DEFAULT_LIVE_TOOLS, build_tools
from costhive.tools.base import CostTool, ToolStatus
from costhive.tools.komiser import KomiserTool
from costhive.tools.krr import KrrTool, parse_krr
from costhive.tools.opencost import OpenCostTool, _parse_allocation


def test_registry_has_all_seven_tools():
    assert set(ALL_TOOLS) == {"steampipe", "custodian", "komiser", "cloudquery", "infracost", "opencost", "krr"}
    assert DEFAULT_LIVE_TOOLS == ["steampipe", "custodian"]


def test_build_tools_instantiates():
    tools = build_tools(["steampipe", "custodian"])
    assert [t.name for t in tools] == ["steampipe", "custodian"]


def test_unavailable_binary_reports_skipped(tmp_path):
    class Missing(CostTool):
        name = "ghost"
        binary = "definitely-not-a-real-binary-xyz"

    result = Missing().run(None, str(tmp_path))
    assert result.status is ToolStatus.SKIPPED
    assert "not found on PATH" in result.message


def test_komiser_without_export_is_skipped(tmp_path):
    result = KomiserTool(export_path=None).run(None, str(tmp_path))
    assert result.status is ToolStatus.SKIPPED


def test_opencost_without_export_is_skipped(tmp_path):
    result = OpenCostTool().run(None, str(tmp_path))
    assert result.status is ToolStatus.SKIPPED


def test_krr_without_export_is_skipped(tmp_path):
    result = KrrTool().run(None, str(tmp_path))
    assert result.status is ToolStatus.SKIPPED


def test_krr_parse_preserves_actions_without_inventing_savings():
    data = {
        "scans": [
            {
                "object": {
                    "cluster": "prod",
                    "namespace": "payments",
                    "kind": "Deployment",
                    "name": "api",
                    "container": "web",
                    "warnings": [],
                    "allocations": {"requests": {"cpu": 2, "memory": 4 * 1024**3}},
                },
                "recommended": {
                    "requests": {
                        "cpu": {"value": 0.5, "severity": "CRITICAL"},
                        "memory": {"value": 1.5 * 1024**3, "severity": "CRITICAL"},
                    }
                },
                "severity": "CRITICAL",
            }
        ]
    }
    findings = parse_krr(data)
    assert len(findings) == 1
    assert findings[0].resource == "prod/payments/Deployment/api/web"
    assert findings[0].estimated_monthly_savings == 0.0
    assert "cpu reduce 2 cores → 500m" in findings[0].description
    assert "memory reduce 4 GiB → 1.5 GiB" in findings[0].description


def test_opencost_allocation_parse_computes_waste():
    data = {
        "data": [
            {
                "team-a": {"totalCost": 100.0, "totalEfficiency": 0.25},
                "__idle__": {"totalCost": 5.0, "totalEfficiency": 0.0},
                "team-b": {"totalCost": 40.0, "totalEfficiency": 1.0},
            }
        ]
    }
    findings = _parse_allocation(data, cluster="prod")
    # team-a wastes 75%; team-b is fully efficient (skipped); __idle__ skipped.
    assert len(findings) == 1
    f = findings[0]
    assert f.category is Category.RIGHTSIZING
    assert f.resource == "team-a"
    assert f.estimated_monthly_savings == 75.0
