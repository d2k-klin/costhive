"""OpenCost tool wrapper — Kubernetes/EKS cost allocation.

OpenCost runs *inside* an EKS cluster and exposes an allocation API. Like SentryHive's
hardeneks, it is a deliberately opt-in phase (`--eks`): it needs in-cluster access,
not just IAM, so it is never bundled silently into the default account scan. When
enabled, the wrapper queries the OpenCost allocation endpoint and turns idle/oversized
namespaces into rightsizing findings.
"""

from __future__ import annotations

import json

from costhive.auth import AwsContext
from costhive.models import Category, Confidence, SavingsFinding
from costhive.tools.base import CostTool, ToolResult, ToolStatus


class OpenCostTool(CostTool):
    name = "opencost"
    binary = "kubectl"
    requires_aws = True

    def __init__(self, cluster: str | None = None, allocation_export: str | None = None, kubeconfig: str | None = None):
        self.cluster = cluster
        self.allocation_export = allocation_export
        self.kubeconfig = kubeconfig

    def _run(self, ctx: AwsContext | None, workdir: str) -> ToolResult:
        data = None
        if self.allocation_export:
            try:
                with open(self.allocation_export) as fh:
                    data = json.load(fh)
            except (OSError, json.JSONDecodeError) as exc:
                return ToolResult(self.name, ToolStatus.ERROR, message=f"could not read allocation export: {exc}")
        else:
            return ToolResult(
                self.name,
                ToolStatus.SKIPPED,
                message="opt-in — provide --opencost-export (OpenCost /allocation JSON) to enable EKS cost analysis.",
            )

        findings = _parse_allocation(data, cluster=self.cluster or "")
        return ToolResult(
            self.name,
            ToolStatus.OK,
            findings=findings,
            message=f"{len(findings)} namespace efficiency finding(s)",
            raw=data,
        )


def _parse_allocation(data: dict | list, cluster: str = "") -> list[SavingsFinding]:
    """Turn OpenCost /allocation output into rightsizing findings.

    OpenCost returns `{"data": [ {namespace: {totalCost, cpuEfficiency, ...}} ]}`.
    A namespace with low efficiency is over-provisioned; the wasted spend is roughly
    totalCost * (1 - efficiency).
    """
    findings: list[SavingsFinding] = []
    windows = data.get("data", data) if isinstance(data, dict) else data
    if isinstance(windows, dict):
        windows = [windows]
    for window in windows or []:
        if not isinstance(window, dict):
            continue
        for ns, alloc in window.items():
            if not isinstance(alloc, dict) or ns in ("__idle__", "__unmounted__"):
                continue
            total = float(alloc.get("totalCost", 0) or 0)
            efficiency = alloc.get("totalEfficiency", alloc.get("cpuEfficiency"))
            if total <= 0 or efficiency is None:
                continue
            try:
                eff = float(efficiency)
            except (TypeError, ValueError):
                continue
            waste = round(total * max(0.0, 1.0 - eff), 2)
            if waste <= 0:
                continue
            findings.append(
                SavingsFinding(
                    tool="opencost",
                    category=Category.RIGHTSIZING,
                    title=f"Over-provisioned namespace: {ns}",
                    description=(
                        f"Namespace '{ns}'{f' in {cluster}' if cluster else ''} runs at "
                        f"{eff * 100:.0f}% resource efficiency, wasting ~${waste:.2f}/mo of its ${total:.2f}/mo spend."
                    ),
                    estimated_monthly_savings=waste,
                    confidence=Confidence.MEDIUM,
                    resource=ns,
                    service="eks",
                    recommended_action="Right-size CPU/memory requests to match actual usage.",
                )
            )
    return findings
