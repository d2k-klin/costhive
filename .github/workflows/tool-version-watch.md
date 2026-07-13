---
on:
  schedule: weekly on monday
  workflow_dispatch:

permissions:
  contents: read
  issues: read
  pull-requests: read

engine: copilot

tools:
  edit:
  web-fetch:
  bash:
    - "git:*"
    - "gh:*"
    - "pip:*"
    - "ruff:*"
    - "mypy:*"
    - "pytest:*"
    - "python:*"
    - "curl:*"
    - "jq:*"
    - "./scripts/*"

network: defaults

safe-outputs:
  create-pull-request:
    title-prefix: "deps: "
    labels: [dependencies]
    draft: false
---

# tool-version-watch

CostHive bundles 6 FinOps CLI tools at pinned versions in `tool-versions.env`
(the single source of truth — see `docs/tools.md` "Version pinning" and
`CONTRIBUTING.md`). Dependabot (`.github/dependabot.yml`) covers pip/
github-actions/docker-base-image, but not these — they're plain release-tag
pins, not package-manager manifest entries, so nothing else watches them.

Find any tool that has a newer stable upstream release, bump it correctly,
adapt any code the release notes say broke, and validate. If everything is
already current, make no changes — an empty diff means no PR is opened.

## 1. Read current pins

Read `tool-versions.env` for the 6 current versions: `STEAMPIPE_VERSION`,
`CUSTODIAN_VERSION`, `INFRACOST_VERSION`, `CLOUDQUERY_VERSION`,
`KOMISER_VERSION`, `OPENCOST_VERSION`.

## 2. Get latest upstream versions

Run these exact checks (each has a quirk — use the given approach, don't just
hit `/releases/latest` blindly):

- steampipe: `gh api repos/turbot/steampipe/releases/latest --jq .tag_name`
- infracost: `gh api repos/infracost/infracost/releases/latest --jq .tag_name`
- komiser: `gh api repos/mlabouardy/komiser/releases/latest --jq .tag_name`
- opencost: `gh api repos/opencost/opencost/releases/latest --jq .tag_name`
- cloudquery: this is a monorepo — `/releases/latest` returns whatever plugin
  shipped most recently, NOT the CLI. Instead run:
  `gh api "repos/cloudquery/cloudquery/releases?per_page=30" --jq '[.[] | select(.tag_name | startswith("cli-v"))][0].tag_name'`
  and strip the `cli-` prefix.
- custodian (c7n): it's a PyPI package, not a GitHub release —
  `curl -s https://pypi.org/pypi/c7n/json | jq -r .info.version`

Strip the leading `v` to compare against the plain-number pins in
`tool-versions.env`.

## 3. For each tool that's behind

- Update its version in `tool-versions.env`.
- `STEAMPIPE_VERSION`, `CUSTODIAN_VERSION`, `INFRACOST_VERSION` are also
  duplicated as `ARG ... =` defaults near the top of the `Dockerfile` (search
  for `ARG STEAMPIPE_VERSION=` etc.) — update those defaults too, per the
  comment above them ("Keep the defaults in sync with that file").
  `CLOUDQUERY_VERSION`/`KOMISER_VERSION`/`OPENCOST_VERSION` are
  documented-only pins (not Dockerfile ARGs, see `docs/tools.md`) — just the
  env file for those.
- Fetch that release's notes (`gh api repos/<owner>/<repo>/releases/tags/<tag>
  --jq .body`, or the PyPI changelog for c7n) and read them for breaking
  changes to CLI flags or output format. CostHive shells out to steampipe,
  custodian, and infracost directly (`costhive/tools/*.py`) and parses their
  output in `costhive/normalize.py` — "Keep parsers defensive: tool output
  drifts between versions; degrade rather than raise" (`CONTRIBUTING.md`). If
  a release note calls out a flag rename, output schema change, or removed
  feature that affects code in `costhive/tools/` or `costhive/normalize.py`,
  patch it. If nothing in the notes affects the wrapper code, don't touch it —
  a version bump alone is not a reason to refactor.
- Add a `CHANGELOG.md` entry under `## [Unreleased]` calling out the bump as
  **savings-impacting** (`CONTRIBUTING.md` convention: tool version bumps can
  change findings/dollar amounts).

## 4. Validate

Run, and fix anything that fails as a direct result of your change (don't
chase unrelated pre-existing failures):

```bash
pip install -e ".[dev]"
ruff check .
ruff format --check .
mypy costhive
pytest --cov=costhive --cov-fail-under=65
./scripts/validate-policies.sh
python scripts/check-doc-links.py
```

This job does **not** install the real steampipe/custodian/infracost CLIs —
that's `ci.yml`'s `tool-integrity` and `build` jobs, which run automatically
once your PR exists. Don't try to reproduce them here.

## 5. Wrap up

If you changed any files, leave them modified in the working tree — the PR is
created automatically from your diff. Do not run `git commit` or open the PR
yourself. Summarize, in your final message, a table of tool → old version →
new version, any wrapper-code changes and why, and a link to each bumped
tool's release notes — that becomes the PR description.

If every tool is already at the latest version, make no file changes and say
so; no PR will be created.
