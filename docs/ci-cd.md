# CI/CD integration

Two ways to use CostHive in a pipeline:

1. **Report generator** — produce a savings report on a schedule / on demand and
   publish it as an artifact. The common case.
2. **Cost gate** — fail a build if too much recoverable spend is going unactioned,
   via `--fail-under`.

> Give CI **read-only** credentials (assume-role preferred). CostHive never modifies
> resources, but least privilege is still the rule.

## GitHub Actions — scheduled report

```yaml
name: Cost report
on:
  schedule:
    - cron: "0 6 * * 1"      # Mondays 06:00 UTC
  workflow_dispatch:

permissions:
  id-token: write            # for OIDC assume-role
  contents: read

jobs:
  costhive:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789012:role/CostHiveAudit
          aws-region: us-east-1

      - name: Run CostHive
        run: |
          pipx run --spec . costhive scan --yes --out ./reports
        # or: docker run --rm -v "$PWD/reports:/app/reports" costhive scan --yes

      - uses: actions/upload-artifact@v4
        with:
          name: cost-report
          path: reports/
```

## Cost gate

```bash
costhive scan --profile ci --fail-under 500 --yes
```

Exit codes:

| Code | Meaning |
|------|---------|
| `0` | Completed. |
| `1` | Authentication failed, or a tool errored (report still written). |
| `2` | Bad arguments. |
| `3` | `--fail-under` threshold met — recoverable savings at/above the limit. |

## Notes

- Use `--yes` to skip the confirmation prompt in non-interactive runs.
- Add `--format json` and parse `findings.json` if you want to post the headline
  number to Slack/PRs.
- The bundled tool CLIs must be available — use the Docker image, or install
  Steampipe/Custodian in the runner. Missing tools are skipped, not fatal.
