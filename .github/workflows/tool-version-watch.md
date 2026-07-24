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

CostHive tracks its FinOps and supporting CLI tools in `tool-versions.env`
(the single source of truth — see `docs/tools.md` "Version pinning" and
`CONTRIBUTING.md`). Dependabot (`.github/dependabot.yml`) covers pip/
github-actions/docker-base-image, but not these — they're plain release-tag
pins, not package-manager manifest entries, so nothing else watches them.

Find any tool that has a newer stable upstream release, bump it correctly,
adapt any code the release notes say broke, and validate. If everything is
already current, make no changes — an empty diff means no PR is opened.

## 1. Read current pins

Read `tool-versions.env` for the current versions: `AWS_CLI_VERSION`,
`STEAMPIPE_VERSION`, `STEAMPIPE_AWS_PLUGIN_VERSION`, `CUSTODIAN_VERSION`,
`INFRACOST_VERSION`, `CLOUDQUERY_VERSION`, `KOMISER_VERSION`,
`OPENCOST_VERSION`, `KRR_VERSION`, and `GITLEAKS_VERSION`.

## 2. Get latest upstream versions

Run these exact checks (each has a quirk — use the given approach, don't just
hit `/releases/latest` blindly):

- steampipe: `gh api repos/turbot/steampipe/releases/latest --jq .tag_name`
- steampipe AWS plugin:
  `gh api repos/turbot/steampipe-plugin-aws/releases/latest --jq .tag_name`
- infracost: `gh api repos/infracost/cli/releases/latest --jq .tag_name`
- komiser: `gh api repos/mlabouardy/komiser/releases/latest --jq .tag_name`
- opencost: `gh api repos/opencost/opencost/releases/latest --jq .tag_name`
- krr: `gh api repos/robusta-dev/krr/releases/latest --jq .tag_name`
- AWS CLI v2: this repository uses tags instead of GitHub Releases:
  `gh api "repos/aws/aws-cli/tags?per_page=1" --jq '.[0].name'`
- gitleaks: `gh api repos/gitleaks/gitleaks/releases/latest --jq .tag_name`
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
- `AWS_CLI_VERSION`, `STEAMPIPE_VERSION`, `STEAMPIPE_AWS_PLUGIN_VERSION`,
  `CUSTODIAN_VERSION`, and `INFRACOST_VERSION` are also duplicated as `ARG`
  defaults near the top of the `Dockerfile` — update those defaults too, per
  the comment above them ("Keep these defaults in sync with it").
  `CLOUDQUERY_VERSION`/`KOMISER_VERSION`/`OPENCOST_VERSION`/`KRR_VERSION` are
  documented-only pins (not Dockerfile ARGs, see `docs/tools.md`) — just the
  env file for those.
- `GITLEAKS_VERSION` is consumed directly from `tool-versions.env` by
  `.github/workflows/ci.yml`; it has no duplicate.
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
- Add a `CHANGELOG.md` entry under `## [Unreleased]`. Call FinOps tool/plugin
  bumps **savings-impacting** (`CONTRIBUTING.md` convention: they can change
  findings/dollar amounts); AWS CLI and Gitleaks bumps are regular tooling
  changes.

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
