# Architecture

CostHive is a thin orchestrator around best-in-class OSS FinOps tools. The pipeline
is: **auth → run tools → normalize → aggregate/rank → report.**

```
  AWS creds (profile / keys / assume-role)
        │
        ▼
  ┌───────────────┐   sts:GetCallerIdentity, per account
  │ auth.py       │   + preflight_cost_access (Cost Explorer / Compute Optimizer)
  └──────┬────────┘
         ▼   one AwsContext per account
  ┌───────────────────────────────────────────────┐
  │ tools/  (CostTool subclasses)                  │
  │  steampipe · custodian · komiser · cloudquery  │
  │  · opencost · infracost                        │
  └──────┬─────────────────────────────────────────┘
         ▼  native JSON/rows
  ┌───────────────┐   parse_* → SavingsFinding
  │ normalize.py  │   (category, $ savings, confidence, risk)
  └──────┬────────┘
         ▼
  ┌───────────────┐   dedup · rank by $ · by-category · by-risk · quick wins
  │ aggregate.py  │   → Report
  └──────┬────────┘
         ▼
  ┌───────────────┐   HTML · Markdown · JSON · PDF
  │ report/       │
  └───────────────┘
```

## Key components

| Module | Responsibility |
|--------|----------------|
| `costhive/auth.py` | Resolve credentials, verify identity, probe cost-data access, one `AwsContext` per account. |
| `costhive/tools/base.py` | The `CostTool` contract (`run(ctx, workdir) → ToolResult`) + subprocess/progress helpers. |
| `costhive/tools/*.py` | One wrapper per tool; each returns normalized `SavingsFinding`s. |
| `costhive/models.py` | The unified schema: `SavingsFinding`, `Category`, `Confidence`, `Risk`. |
| `costhive/normalize.py` | Per-tool parsers: native output → `SavingsFinding`. |
| `costhive/aggregate.py` | Dedup, `$`-ranking, category/risk breakdowns, quick wins → `Report`. |
| `costhive/report/` | Jinja2 templates → HTML/MD/JSON/PDF. |
| `costhive/cli.py` | Typer CLI: `scan`, `estimate`, `tools`. |

## Design principles

- **One schema.** Every tool normalizes into `SavingsFinding`, so the aggregator and
  report layer never know which tool produced a finding. Adding a 7th tool is a new
  wrapper + parser + registry entry — nothing downstream changes.
- **The dollar is the sort key.** `estimated_monthly_savings` drives ranking
  everywhere; `confidence` and `risk` keep it honest.
- **Isolation & resilience.** Each tool runs in a child process with the verified
  (possibly assumed-role) credentials. One tool failing is recorded and never aborts
  the run; missing tools are skipped.
- **Read-only & local.** No writes to AWS (Custodian is dry-run); no data leaves the
  machine.

See the sibling [SentryHive](https://github.com/d2k-klin/sentryhive) for the same
pattern applied to security (ranked by severity instead of savings).
