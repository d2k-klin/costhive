"""CloudQuery tool wrapper — sync AWS inventory to a DB, then SQL over it.

CloudQuery is an **opt-in advanced mode** (project plan §10): unlike Steampipe (which
embeds Postgres), CloudQuery syncs to an external database, so it needs a `--db-url`.
When enabled, the wrapper runs `cloudquery sync` with the bundled AWS->Postgres spec,
then runs the same FinOps SQL contract over the synced tables. Without a DB URL it
cleanly reports SKIPPED so the default run stays lightweight.
"""

from __future__ import annotations

import json
import os
import shutil

from costhive.auth import AwsContext
from costhive.normalize import parse_cloudquery
from costhive.tools.base import CostTool, ToolResult, ToolStatus, session_env
from costhive.tools.queries import FINOPS_QUERIES


class CloudQueryTool(CostTool):
    name = "cloudquery"
    binary = "cloudquery"
    requires_aws = True
    version_flag = "version"

    def __init__(self, db_url: str | None = None, spec_path: str | None = None):
        self.db_url = db_url or os.environ.get("COSTHIVE_CLOUDQUERY_DB_URL")
        self.spec_path = spec_path or os.environ.get("COSTHIVE_CLOUDQUERY_SPEC")

    def is_available(self) -> bool:
        return shutil.which(self.binary) is not None

    def _run(self, ctx: AwsContext | None, workdir: str) -> ToolResult:
        if not self.db_url:
            return ToolResult(
                self.name,
                ToolStatus.SKIPPED,
                message="opt-in mode — provide --cloudquery-db-url (external Postgres) to enable.",
            )
        if not self.spec_path or not os.path.isfile(self.spec_path):
            return ToolResult(
                self.name,
                ToolStatus.SKIPPED,
                message="no CloudQuery sync spec provided (set --cloudquery-spec).",
            )
        env = session_env(ctx)
        account_id = ctx.identity.account_id if ctx else ""

        sync = self._exec(
            ["cloudquery", "sync", self.spec_path],
            env=env,
            progress=True,
            progress_label=f"{self.name}:sync",
        )
        if sync.returncode != 0:
            return ToolResult(
                self.name,
                ToolStatus.ERROR,
                message=f"cloudquery sync failed (exit {sync.returncode}): {(sync.stderr or '')[-200:]}",
            )

        findings = []
        for _qname, sql in FINOPS_QUERIES.items():
            rows = self._psql(sql, env)
            if rows is None:
                continue
            findings.extend(parse_cloudquery(rows, account_id=account_id))
        return ToolResult(self.name, ToolStatus.OK, findings=findings, message="synced + queried")

    def _psql(self, sql: str, env: dict):
        """Run a query against the synced DB via psql, returning JSON rows.

        Uses `psql`'s ability to emit JSON so we reuse the same column contract as
        Steampipe. Returns None on any failure (missing table, psql absent).
        """
        if not shutil.which("psql") or not self.db_url:
            return None
        wrapped = f"SELECT json_agg(t) FROM ({sql}) t;"
        proc = self._exec(
            ["psql", self.db_url, "-tAc", wrapped],
            env=env,
        )
        out = (proc.stdout or "").strip()
        if proc.returncode != 0 or not out or out == "null":
            return None
        try:
            return json.loads(out)
        except json.JSONDecodeError:
            return None
