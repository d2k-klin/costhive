from costhive.models import Category
from costhive.tools import ALL_TOOLS, DEFAULT_LIVE_TOOLS, build_tools
from costhive.tools.base import CostTool, ToolStatus
from costhive.tools.komiser import KomiserTool
from costhive.tools.opencost import OpenCostTool, _parse_allocation


def test_registry_has_all_six_tools():
    assert set(ALL_TOOLS) == {"steampipe", "custodian", "komiser", "cloudquery", "infracost", "opencost"}
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
