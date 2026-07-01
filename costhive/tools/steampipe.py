"""Steampipe tool wrapper — SQL over live AWS APIs for cost/waste queries.

Runs CostHive's bundled FinOps queries (queries.py) one at a time via
`steampipe query --output json`, each authored to emit the normalizer's column
contract. Requires the Steampipe AWS plugin and read-only IAM.
"""

from __future__ import annotations

import json

from costhive.auth import AwsContext
from costhive.normalize import parse_steampipe
from costhive.tools.base import CostTool, ToolResult, ToolStatus, session_env
from costhive.tools.queries import FINOPS_QUERIES


class SteampipeTool(CostTool):
    name = "steampipe"
    binary = "steampipe"
    requires_aws = True
    version_flag = "--version"

    def _run(self, ctx: AwsContext | None, workdir: str) -> ToolResult:
        env = session_env(ctx)
        account_id = ctx.identity.account_id if ctx else ""
        findings = []
        errors: list[str] = []
        ran = 0

        for qname, sql in FINOPS_QUERIES.items():
            proc = self._exec(
                ["steampipe", "query", sql, "--output", "json"],
                env=env,
                progress=True,
                progress_label=f"{self.name}:{qname}",
            )
            rows = _load_json(proc.stdout)
            if rows is None:
                # A single failing query (e.g. missing table for a disabled service)
                # must not sink the whole run — record and move on.
                snippet = (proc.stderr or "").strip()[-200:]
                errors.append(f"{qname}: {snippet or 'no JSON output'}")
                continue
            ran += 1
            findings.extend(parse_steampipe(rows, account_id=account_id))

        if ran == 0:
            return ToolResult(
                self.name,
                ToolStatus.ERROR,
                message="no Steampipe query returned data — is the AWS plugin installed? "
                + ("; ".join(errors[:3]) if errors else ""),
            )
        message = f"{ran}/{len(FINOPS_QUERIES)} queries ran" + (f"; {len(errors)} skipped" if errors else "")
        return ToolResult(self.name, ToolStatus.OK, findings=findings, message=message)


def _load_json(text: str):
    text = (text or "").strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None
