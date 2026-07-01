#!/usr/bin/env bash
# scripts/validate-policies.sh — assert the Cloud Custodian policy packs are safe.
#
# Hard rule (addendum §1): v1 never remediates. This checks every bundled policy is
# report-only (no `actions:`) and carries CostHive metadata, then — if the custodian
# CLI is available — runs `custodian validate` on each pack. No AWS, no writes.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
POLICY_DIR="$ROOT/policies"

echo "=== CostHive policy safety check ==="

# 1) Pure-Python structural + no-write assertion (no custodian needed).
python3 - "$POLICY_DIR" <<'PY'
import glob, os, sys
import yaml

policy_dir = sys.argv[1]
files = sorted(glob.glob(os.path.join(policy_dir, "*.yml")) + glob.glob(os.path.join(policy_dir, "*.yaml")))
if not files:
    sys.exit("no policy packs found in %s" % policy_dir)

fail = False
for pf in files:
    doc = yaml.safe_load(open(pf)) or {}
    for policy in doc.get("policies", []):
        name = policy.get("name", "?")
        if policy.get("actions"):
            print(f"  ✗ {os.path.basename(pf)}:{name} contains remediation actions (must be report-only)")
            fail = True
        meta = policy.get("metadata") or {}
        if "category" not in meta or "monthly_savings_each" not in meta:
            print(f"  ✗ {os.path.basename(pf)}:{name} missing metadata.category/monthly_savings_each")
            fail = True
    print(f"  ✓ {os.path.basename(pf)} ({len(doc.get('policies', []))} policies, report-only)")

sys.exit(1 if fail else 0)
PY

# 2) If custodian is installed, validate each pack for real.
if command -v custodian >/dev/null 2>&1; then
  echo "--- custodian validate ---"
  for pf in "$POLICY_DIR"/*.yml "$POLICY_DIR"/*.yaml; do
    [ -e "$pf" ] || continue
    custodian validate "$pf"
  done
else
  echo "--- custodian not installed; skipping 'custodian validate' (structural check passed) ---"
fi

echo "✓ Policy safety check passed."
