# Contributing to CostHive

Thanks for helping make cloud cost optimization one-command-simple.

## Dev setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
ruff check . && ruff format --check .
```

Tests use mocks and fixtures only — **no AWS credentials or network access** are
required or permitted in the suite.

## Adding a tool

Every tool is a `CostTool` subclass (see `costhive/tools/base.py`) plus a parser in
`costhive/normalize.py` that maps the tool's native output into the unified
`SavingsFinding` schema. Register it in `costhive/tools/__init__.py`. The
orchestrator, aggregator and report layer never change.

The golden rule: **attach `estimated_monthly_savings`, an honest `confidence`, and a
`risk` level.** The dollar figure is the sort key for the whole report; don't
overpromise, and mark judgment-call actions as such.

## Adding a Cloud Custodian policy pack

Drop a `.yml` file in `policies/`. Each policy needs a `metadata` block CostHive
reads to attach dollars, a category, confidence, and risk to every matched resource:

```yaml
policies:
  - name: my-idle-thing
    resource: ec2
    comment: "Short description shown in the report."
    metadata:
      category: idle          # see docs/categories.md
      monthly_savings_each: 30.0
      confidence: medium       # high | medium | low
      risk: judgment           # safe | moderate | judgment
      recommended_action: "What to do, with the trade-off noted."
    filters: [...]             # NO `actions:` — v1 is report-only (dry-run)
```

## Docs & changelog

- Docs live in the repo and change **in the same PR** as the code.
- After changing the CLI, run `python scripts/gen-cli-reference.py` so
  `docs/usage.md` stays in sync (CI checks this).
- Add a `CHANGELOG.md` entry under `[Unreleased]`. Call out **savings-impacting**
  changes (estimation logic, bundled-tool version bumps) explicitly.
- Never put real credentials, account IDs, or ARNs in docs — use `123456789012`.

## CI

CI validates the **project**, never a cloud account — no AWS credentials, no billing
data, no writes. Required checks on `main`: `lint`, `test`, `policy-check`,
`tool-integrity`, `build`. Run them locally before pushing:

```bash
ruff check . && ruff format --check . && mypy costhive
pytest --cov=costhive
./scripts/validate-policies.sh      # no remediation actions in policy packs
python scripts/check-doc-links.py
```

Bundled-tool versions live in `tool-versions.env` (the single source of truth). Bump
them there; note the change in the changelog.

## Ground rules

- Read-only by default. Any action that mutates an account is a deferred v2 feature
  behind an explicit, confirmed flag.
- Keep parsers defensive: tool output drifts between versions; degrade rather than
  raise.
- **CI never touches AWS.** Tests use fixtures and mocked STS only. Custodian runs
  dry-run against fixtures — never a live account, never write actions.
