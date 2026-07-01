#!/usr/bin/env bash
# scripts/extract-changelog.sh <version> — print the CHANGELOG.md section for a
# version (without the leading "## [x.y.z]" header line), for use as release notes.
# Falls back to the whole file if the section isn't found.
set -euo pipefail

VERSION="${1:?usage: extract-changelog.sh <version>}"
VERSION="${VERSION#v}"   # tolerate a leading v (tags are vX.Y.Z)
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CHANGELOG="$ROOT/CHANGELOG.md"

awk -v ver="$VERSION" '
  $0 ~ "^## \\[" ver "\\]" { grab=1; next }
  grab && /^## \[/ { exit }
  grab { print }
' "$CHANGELOG" | sed '/./,$!d'
