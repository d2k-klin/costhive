"""Cloud Custodian tool wrapper — policy-as-code for idle/unused/untagged resources.

v1 is strictly **report-only**: policies run in dry-run mode (no `actions:` are
executed), so nothing in the account is modified. Actual remediation (stopping
instances, deleting volumes) is a deferred v2 feature behind an explicit flag.

Custodian writes one output directory per policy containing `resources.json` (the
matched AWS resources) and `metadata.json` (the policy definition). Our policy packs
annotate each policy with `metadata: {category, monthly_savings_each, ...}`, which
we read back to attach dollars and a category to every matched resource.
"""

from __future__ import annotations

import glob
import json
import os

import yaml

from costhive.auth import AwsContext
from costhive.normalize import parse_custodian
from costhive.tools.base import CostTool, ToolResult, ToolStatus, session_env

#: Default policy pack shipped with CostHive (see policies/).
DEFAULT_POLICY_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "policies")


class CustodianTool(CostTool):
    name = "custodian"
    binary = "custodian"
    requires_aws = True
    version_flag = "version"

    def __init__(self, policy_dir: str | None = None):
        self.policy_dir = policy_dir or os.environ.get("COSTHIVE_POLICY_DIR") or DEFAULT_POLICY_DIR

    def _run(self, ctx: AwsContext | None, workdir: str) -> ToolResult:
        policy_files = sorted(
            glob.glob(os.path.join(self.policy_dir, "*.yml")) + glob.glob(os.path.join(self.policy_dir, "*.yaml"))
        )
        if not policy_files:
            return ToolResult(
                self.name,
                ToolStatus.SKIPPED,
                message=f"no Custodian policy files found in {self.policy_dir}",
            )
        env = session_env(ctx)
        if ctx and ctx.regions:
            env["AWS_DEFAULT_REGION"] = ctx.regions[0]
        out_dir = os.path.join(workdir, "custodian")
        os.makedirs(out_dir, exist_ok=True)
        account_id = ctx.identity.account_id if ctx else ""

        ran = 0
        for pf in policy_files:
            # --dryrun guarantees report-only: policy actions are never executed.
            self._exec(
                ["custodian", "run", "--dryrun", "--output-dir", out_dir, pf],
                env=env,
                progress=True,
                progress_label=f"{self.name}:{os.path.basename(pf)}",
            )
            ran += 1

        policy_runs = _collect_policy_runs(policy_files, out_dir)
        findings = parse_custodian(policy_runs, account_id=account_id)
        return ToolResult(
            self.name,
            ToolStatus.OK,
            findings=findings,
            message=f"{ran} policy file(s) evaluated (dry-run, no changes made)",
        )


def _collect_policy_runs(policy_files: list[str], out_dir: str) -> list[dict]:
    """Join each policy's declared metadata with the resources Custodian matched."""
    runs: list[dict] = []
    for pf in policy_files:
        try:
            with open(pf) as fh:
                doc = yaml.safe_load(fh) or {}
        except (OSError, yaml.YAMLError):
            continue
        for policy in doc.get("policies", []) or []:
            if not isinstance(policy, dict):
                continue
            name = policy.get("name", "")
            meta = policy.get("metadata", {}) or {}
            resources = _load_resources(os.path.join(out_dir, name, "resources.json"))
            runs.append(
                {
                    "policy": name,
                    "category": meta.get("category", "other"),
                    "monthly_savings_each": meta.get("monthly_savings_each", 0.0),
                    "confidence": meta.get("confidence", "medium"),
                    "risk": meta.get("risk"),
                    "recommended_action": meta.get("recommended_action", ""),
                    "description": policy.get("comment", meta.get("description", "")),
                    "service": policy.get("resource", ""),
                    "resources": resources,
                }
            )
    return runs


def _load_resources(path: str):
    try:
        with open(path) as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return []
    return data if isinstance(data, list) else []
