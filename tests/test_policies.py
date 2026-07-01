"""Cloud Custodian policy-pack safety tests.

Hard rule (addendum §1): CostHive never remediates in v1. These tests assert the
bundled policy packs contain **no write/remediation actions** and carry the metadata
the normalizer needs — enforced in pure Python so they run without Custodian
installed. If `custodian` is on PATH, we additionally `custodian validate` each pack.
"""

import pathlib
import shutil
import subprocess

import pytest
import yaml

from costhive.models import Category, Confidence, Risk

POLICY_DIR = pathlib.Path(__file__).parent.parent / "policies"
POLICY_FILES = sorted(POLICY_DIR.glob("*.yml")) + sorted(POLICY_DIR.glob("*.yaml"))


def _all_policies():
    for pf in POLICY_FILES:
        doc = yaml.safe_load(pf.read_text()) or {}
        for policy in doc.get("policies", []):
            yield pf.name, policy


def test_policy_packs_exist():
    assert POLICY_FILES, "no Cloud Custodian policy packs found in policies/"


def test_no_write_or_remediation_actions():
    """The hard rule: default packs must be report-only — no `actions:` at all."""
    offenders = [f"{fname}:{policy.get('name')}" for fname, policy in _all_policies() if policy.get("actions")]
    assert not offenders, f"policies must not contain remediation actions (report-only): {offenders}"


def test_every_policy_has_costhive_metadata():
    for fname, policy in _all_policies():
        meta = policy.get("metadata") or {}
        where = f"{fname}:{policy.get('name')}"
        assert "category" in meta, f"{where} missing metadata.category"
        assert "monthly_savings_each" in meta, f"{where} missing metadata.monthly_savings_each"
        # Values must map cleanly onto the unified schema enums.
        assert isinstance(Category.parse(meta["category"]), Category)
        assert isinstance(Confidence.parse(meta.get("confidence")), Confidence)
        assert isinstance(Risk.parse(meta.get("risk")), Risk)
        assert float(meta["monthly_savings_each"]) >= 0


def test_policies_are_valid_yaml_with_required_keys():
    for pf in POLICY_FILES:
        doc = yaml.safe_load(pf.read_text())
        assert isinstance(doc, dict) and "policies" in doc
        for policy in doc["policies"]:
            assert "name" in policy and "resource" in policy


@pytest.mark.skipif(shutil.which("custodian") is None, reason="custodian not installed")
def test_custodian_validate_passes():
    for pf in POLICY_FILES:
        proc = subprocess.run(["custodian", "validate", str(pf)], capture_output=True, text=True)
        assert proc.returncode == 0, f"custodian validate failed for {pf.name}: {proc.stderr}"
