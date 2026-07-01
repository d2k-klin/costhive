"""Komiser tool wrapper — cloud inventory + cost/governance.

Komiser is primarily a long-running dashboard server backed by its own DB, which
doesn't fit CostHive's one-shot report model. For v1 we use it in a lightweight
governance role: if a Komiser resources export is available (via `--komiser-export`
or a running Komiser API), we flag high-cost, untagged resources as cost-allocation
gaps. Without an export, the tool cleanly reports SKIPPED.
"""

from __future__ import annotations

import json
import os

from costhive.auth import AwsContext
from costhive.normalize import parse_komiser
from costhive.tools.base import CostTool, ToolResult, ToolStatus


class KomiserTool(CostTool):
    name = "komiser"
    binary = ""  # consumed via an export file / API, not a bundled CLI invocation
    requires_aws = True

    def __init__(self, export_path: str | None = None, untagged_threshold: float = 0.0):
        self.export_path = export_path or os.environ.get("COSTHIVE_KOMISER_EXPORT")
        self.untagged_threshold = untagged_threshold

    def _run(self, ctx: AwsContext | None, workdir: str) -> ToolResult:
        if not self.export_path:
            return ToolResult(
                self.name,
                ToolStatus.SKIPPED,
                message="no Komiser export provided (set --komiser-export or COSTHIVE_KOMISER_EXPORT).",
            )
        if not os.path.isfile(self.export_path):
            return ToolResult(
                self.name,
                ToolStatus.ERROR,
                message=f"Komiser export not found: {self.export_path}",
            )
        try:
            with open(self.export_path) as fh:
                data = json.load(fh)
        except (OSError, json.JSONDecodeError) as exc:
            return ToolResult(self.name, ToolStatus.ERROR, message=f"could not read Komiser export: {exc}")

        account_id = ctx.identity.account_id if ctx else ""
        findings = parse_komiser(data, account_id=account_id, untagged_threshold=self.untagged_threshold)
        return ToolResult(
            self.name,
            ToolStatus.OK,
            findings=findings,
            message=f"{len(findings)} untagged cost-allocation gap(s)",
            raw=data,
        )
