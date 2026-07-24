#!/usr/bin/env bash
# scripts/verify-tools.sh — assert bundled tools are installed at their pinned
# versions (tool-versions.env is the single source of truth). Used by the CI
# tool-integrity job. No AWS, no scanning — just `--version` checks.
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck disable=SC1091
. "$ROOT/tool-versions.env"

FAIL=0

# Tools CostHive shells out to directly — must be present and match the pin.
check_cli() {
  local name="$1" cmd="$2" want="$3"; shift 3
  local flags=("$@")
  printf "%-14s" "$name"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "MISSING — '$cmd' not on PATH"; FAIL=1; return
  fi
  local out; out="$("$cmd" "${flags[@]}" 2>&1 | head -1 || true)"
  if echo "$out" | grep -qF "$want"; then
    echo "OK — $out"
  else
    echo "VERSION MISMATCH — want $want, got: $out"; FAIL=1
  fi
}

echo "=== CostHive tool integrity (pinned versions) ==="
check_cli "steampipe" steampipe "$STEAMPIPE_VERSION" --version
check_cli "custodian" custodian "$CUSTODIAN_VERSION" version
check_cli "infracost" infracost "$INFRACOST_VERSION" --version

echo ""
echo "Docker ARG pins:"
for name in AWS_CLI_VERSION STEAMPIPE_VERSION STEAMPIPE_AWS_PLUGIN_VERSION CUSTODIAN_VERSION INFRACOST_VERSION; do
  want="${!name}"
  printf "%-28s" "$name"
  if grep -qF "ARG ${name}=${want}" "$ROOT/Dockerfile"; then
    echo "OK — $want"
  else
    echo "MISMATCH — tool-versions.env has $want"; FAIL=1
  fi
done

# Export/DB-based tools are consumed via files/APIs, not bundled as CLIs we invoke.
# Their pins are documented here so bumps are reviewed (the version watcher opens PRs).
echo ""
echo "Documented pins (consumed via export/DB, not invoked as a CLI):"
echo "  cloudquery  $CLOUDQUERY_VERSION"
echo "  komiser     $KOMISER_VERSION"
echo "  opencost    $OPENCOST_VERSION"
echo "  krr         $KRR_VERSION"

# CostHive itself must import and report a version.
echo ""
printf "%-14s" "costhive"
if python3 -c "from costhive import __version__; print(f'OK — v{__version__}')" 2>/dev/null; then :; else
  echo "FAILED — cannot import costhive"; FAIL=1
fi

echo ""
if [ "$FAIL" -ne 0 ]; then echo "✗ Tool integrity check failed."; exit 1; fi
echo "✓ Tool integrity check passed."
