"""Tool registry — maps names to tool factories.

Adding a 7th tool is one entry here plus a wrapper module.
"""

from __future__ import annotations

from collections.abc import Callable

from costhive.tools.base import CostTool, ToolResult, ToolStatus, session_env
from costhive.tools.cloudquery import CloudQueryTool
from costhive.tools.custodian import CustodianTool
from costhive.tools.infracost import InfracostTool
from costhive.tools.komiser import KomiserTool
from costhive.tools.opencost import OpenCostTool
from costhive.tools.steampipe import SteampipeTool

#: Registered tools. Values are factories so per-run options can be injected.
REGISTRY: dict[str, Callable[..., CostTool]] = {
    "steampipe": SteampipeTool,
    "custodian": CustodianTool,
    "komiser": KomiserTool,
    "cloudquery": CloudQueryTool,
    "infracost": InfracostTool,
    "opencost": OpenCostTool,
}

ALL_TOOLS = list(REGISTRY.keys())

#: Live-account tools that run by default (read-only, no external DB needed).
DEFAULT_LIVE_TOOLS = ["steampipe", "custodian"]


def build_tools(
    names: list[str],
    *,
    policy_dir: str | None = None,
    komiser_export: str | None = None,
    cloudquery_db_url: str | None = None,
    cloudquery_spec: str | None = None,
) -> list[CostTool]:
    """Instantiate the requested tools, passing through per-tool options."""
    tools: list[CostTool] = []
    for name in names:
        factory = REGISTRY.get(name)
        if factory is None:
            raise KeyError(f"unknown tool '{name}'. Available: {', '.join(ALL_TOOLS)}")
        if name == "custodian":
            tools.append(factory(policy_dir=policy_dir))
        elif name == "komiser":
            tools.append(factory(export_path=komiser_export))
        elif name == "cloudquery":
            tools.append(factory(db_url=cloudquery_db_url, spec_path=cloudquery_spec))
        else:
            tools.append(factory())
    return tools


__all__ = [
    "REGISTRY",
    "ALL_TOOLS",
    "DEFAULT_LIVE_TOOLS",
    "build_tools",
    "CostTool",
    "ToolResult",
    "ToolStatus",
    "session_env",
]
