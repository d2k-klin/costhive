# CostHive documentation

CostHive points at an AWS account (or IaC on disk) and produces one consolidated,
dollar-ranked cost-optimization report from best-in-class open-source FinOps tools.

Docs follow the [Diátaxis](https://diataxis.fr/) structure — pick the mode that
matches what you're doing.

## Tutorials — learning by doing
- [Getting started](getting-started.md) — your first savings report in 5 minutes.

## How-to guides — task recipes
- [Installation](installation.md) — Docker, from source, PyPI.
- [Usage](usage.md) — scan, estimate, filtering, branded reports, multi-account.
- [Authentication](authentication.md) — profile, static keys, assume-role.
- [Cost-data setup](cost-data-setup.md) — enabling Cost Explorer & CUR.
- [CI/CD](ci-cd.md) — run CostHive in a pipeline.

## Reference — lookup
- [IAM permissions](iam-permissions.md) — least-privilege policy + client onboarding role.
- [Tools](tools.md) — the six bundled FinOps tools and their pinned versions.
- [Categories](categories.md) — every savings category + how estimates are derived.
- [Reports](reports.md) — output formats, branding, interpreting savings.
- [Configuration](configuration.md) — every flag and environment variable.

## Explanation — understanding
- [Architecture](architecture.md) — orchestration → normalization → ranking → report.
- [FAQ](faq.md) — common questions.
- [Troubleshooting](troubleshooting.md) — symptom → cause → fix.

## Trust & safety

CostHive is **read-only**: the shipped IAM policy grants no write/delete actions, and
Cloud Custodian runs in `--dryrun`. All analysis and report generation runs locally —
no scan data leaves your machine. See [../SECURITY.md](../SECURITY.md).
