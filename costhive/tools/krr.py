"""Robusta KRR export wrapper — Kubernetes workload rightsizing recommendations."""

from __future__ import annotations

import json
import os

from costhive.auth import AwsContext
from costhive.models import Category, Confidence, Risk, SavingsFinding
from costhive.tools.base import CostTool, ToolResult, ToolStatus


class KrrTool(CostTool):
    name = "krr"
    binary = ""  # KRR runs against Kubernetes/Prometheus; CostHive consumes its JSON export.
    requires_aws = False

    def __init__(self, export_path: str | None = None):
        self.export_path = export_path or os.environ.get("COSTHIVE_KRR_EXPORT")

    def _run(self, ctx: AwsContext | None, workdir: str) -> ToolResult:
        if not self.export_path:
            return ToolResult(
                self.name,
                ToolStatus.SKIPPED,
                message="no KRR export provided (set --krr-export or COSTHIVE_KRR_EXPORT).",
            )
        try:
            with open(self.export_path) as fh:
                data = json.load(fh)
        except (OSError, json.JSONDecodeError) as exc:
            return ToolResult(self.name, ToolStatus.ERROR, message=f"could not read KRR export: {exc}")

        findings = parse_krr(data)
        return ToolResult(
            self.name,
            ToolStatus.OK,
            findings=findings,
            message=f"{len(findings)} workload/container recommendation(s) imported",
            raw=data,
        )


def parse_krr(data: dict | list) -> list[SavingsFinding]:
    """Normalize KRR JSON without inventing dollars that only OpenCost can supply."""
    scans = data.get("scans", []) if isinstance(data, dict) else data
    findings: list[SavingsFinding] = []
    for scan in scans or []:
        if not isinstance(scan, dict):
            continue
        obj = scan.get("object", {})
        recommended = scan.get("recommended", {})
        if not isinstance(obj, dict) or not isinstance(recommended, dict):
            continue

        current = obj.get("allocations", {}).get("requests", {})
        target = recommended.get("requests", {})
        changes = _request_changes(current, target)
        if not changes:
            continue

        namespace = str(obj.get("namespace") or "default")
        kind = str(obj.get("kind") or "Workload")
        name = str(obj.get("name") or "unknown")
        container = str(obj.get("container") or "container")
        cluster = str(obj.get("cluster") or "")
        resource = "/".join(part for part in (cluster, namespace, kind, name, container) if part)
        warnings = obj.get("warnings") or []

        findings.append(
            SavingsFinding(
                tool="krr",
                category=Category.RIGHTSIZING,
                title=f"Right-size {kind} {namespace}/{name} ({container})",
                description=(
                    f"KRR analyzed historical Kubernetes usage and recommends request changes: {'; '.join(changes)}."
                ),
                estimated_monthly_savings=0.0,
                confidence=Confidence.LOW if warnings else Confidence.HIGH,
                risk=Risk.JUDGMENT,
                resource=resource,
                service="kubernetes",
                recommended_action=(
                    "Apply the recommended requests in a staging environment, verify peak-load headroom, "
                    "then combine with OpenCost to quantify the dollar impact."
                ),
            )
        )
    return findings


def _request_changes(current: object, target: object) -> list[str]:
    if not isinstance(current, dict) or not isinstance(target, dict):
        return []
    changes: list[str] = []
    for resource in ("cpu", "memory"):
        before = _number(current.get(resource))
        after = _number(target.get(resource))
        if before is None or after is None or before == after:
            continue
        formatter = _format_cpu if resource == "cpu" else _format_memory
        direction = "reduce" if after < before else "increase"
        changes.append(f"{resource} {direction} {formatter(before)} → {formatter(after)}")
    return changes


def _number(value: object) -> float | None:
    if isinstance(value, dict):
        value = value.get("value")
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str) and value != "?":
        try:
            return float(value)
        except ValueError:
            pass
    return None


def _format_cpu(value: float) -> str:
    return f"{value:g} cores" if value >= 1 else f"{value * 1000:g}m"


def _format_memory(value: float) -> str:
    gib = value / 1024**3
    return f"{gib:g} GiB" if gib >= 1 else f"{value / 1024**2:g} MiB"
