"""Infracost tool wrapper — pre-deploy cost estimate for Terraform/CDK/CFN.

This is the `estimate` verb's engine: it does NOT touch a live AWS account. It reads
IaC on disk and projects monthly cost before anything ships. `infracost breakdown
--format json` yields projects -> breakdown -> resources with `monthlyCost`, which we
surface as informational findings (the projected spend, not a saving).
"""

from __future__ import annotations

import json
import os

from costhive.auth import AwsContext
from costhive.normalize import infracost_total, parse_infracost
from costhive.tools.base import CostTool, ToolResult, ToolStatus


class InfracostTool(CostTool):
    name = "infracost"
    binary = "infracost"
    requires_aws = False
    version_flag = "--version"

    def __init__(self, path: str | None = None):
        self.path = path or os.environ.get("COSTHIVE_IAC_PATH") or os.getcwd()

    def _run(self, ctx: AwsContext | None, workdir: str) -> ToolResult:
        if not os.path.isdir(self.path):
            return ToolResult(self.name, ToolStatus.ERROR, message=f"IaC path not found: {self.path}")
        out_file = os.path.join(workdir, "infracost.json")
        proc = self._exec(
            ["infracost", "breakdown", "--path", self.path, "--format", "json", "--out-file", out_file],
            progress=True,
            progress_label=self.name,
        )
        data = _load_json(out_file, proc.stdout)
        if data is None:
            return ToolResult(
                self.name,
                ToolStatus.ERROR,
                message=f"infracost produced no JSON (exit {proc.returncode}): {(proc.stderr or '')[-200:]}",
            )
        findings = parse_infracost(data)
        total = infracost_total(data)
        result = ToolResult(
            self.name,
            ToolStatus.OK,
            findings=findings,
            message=f"projected ${total:.2f}/mo across {len(findings)} resource(s)",
            raw=data,
        )
        # Stash the total so the CLI can set the report's projected_monthly_cost.
        result.raw = {"_projected_monthly_cost": total, "infracost": data}
        return result


def _load_json(out_file: str, stdout: str):
    if os.path.isfile(out_file):
        try:
            with open(out_file) as fh:
                return json.load(fh)
        except (OSError, json.JSONDecodeError):
            pass
    stdout = (stdout or "").strip()
    if stdout:
        try:
            return json.loads(stdout)
        except json.JSONDecodeError:
            return None
    return None
