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

The golden rule: **attach `estimated_monthly_savings` and an honest `confidence`.**
The dollar figure is the sort key for the whole report; don't overpromise.

## Ground rules

- Read-only by default. Any action that mutates an account is a deferred v2 feature
  behind an explicit, confirmed flag.
- Keep parsers defensive: tool output drifts between versions; degrade rather than
  raise.
