# Usage

CostHive has two verbs:

- **`scan`** — analyze a live AWS account and rank savings by dollar impact.
- **`estimate`** — price Terraform/CDK/CFN on disk *before* deploy (no AWS account touched).

Plus `costhive tools` (list bundled tools) and `costhive --version`.

> Examples use Docker (`docker compose run --rm costhive …`). From a source install,
> drop that prefix and run `costhive …` directly. Placeholders: `123456789012`
> (account id), `<role-arn>`.

## Task recipes

### Scan a live account with a profile

```bash
docker compose run --rm costhive scan --profile my-profile --yes
```

Output:

```
▶ running steampipe …
  ok (7 findings, $84.20/mo) — 5/5 queries ran
▶ running custodian …
  ok (2 findings, $44.20/mo) — 2 policy files evaluated (dry-run, no changes made)

💰 Total estimated monthly savings: $128.40 ($1,540.80/yr, 9 opportunities)
   ✅ safe to reclaim: $46.00/mo · ⚖️  judgment call: $82.40/mo
```

### Assume a role (with external ID)

The primary path for auditing a client account:

```bash
docker compose run --rm costhive scan \
  --role-arn arn:aws:iam::123456789012:role/CostHiveAudit \
  --external-id shared-secret --yes
```

### Scan multiple accounts

Repeat `--role-arn`. You get a per-account report plus a roll-up across the estate:

```bash
docker compose run --rm costhive scan \
  --role-arn arn:aws:iam::111111111111:role/CostHiveAudit \
  --role-arn arn:aws:iam::222222222222:role/CostHiveAudit \
  --external-id shared-secret --client-name "Acme Corp"
# → ./reports/111111111111/…, ./reports/222222222222/…, ./reports/report.html (roll-up)
```

### Filter by category / region

```bash
docker compose run --rm costhive scan --profile my-profile \
  --categories idle,unused,rightsizing --regions eu-central-1,us-east-1 --yes
```

### Enable the opt-in tools

Each activates when you supply its input:

```bash
# Komiser governance (untagged high-cost resources) from an export
costhive scan --profile p --komiser-export ./komiser-resources.json --yes

# CloudQuery advanced mode (needs an external Postgres)
costhive scan --profile p --cloudquery-db-url postgres://user:pass@host/cq \
  --cloudquery-spec ./cq-spec.yaml --yes

# OpenCost / EKS (from an OpenCost /allocation export)
costhive scan --profile p --opencost-export ./allocation.json --yes
```

### Pre-deploy estimate

```bash
docker compose run --rm -e COSTHIVE_IAC=./terraform costhive estimate --path /iac
```

### Generate a branded client report

```bash
costhive scan --role-arn <role-arn> --external-id shared-secret \
  --client-name "Acme Corp" --logo ./acme-logo.png --pdf --yes
```

### Run in CI as a cost gate

```bash
costhive scan --profile ci --fail-under 500 --yes
# exits 3 if ≥ $500/mo of identified savings is going unactioned
```

See [ci-cd.md](ci-cd.md) for a full workflow.

## Command & flag reference

> This section is generated from the CLI definitions by
> `scripts/gen-cli-reference.py` and checked in CI, so it never drifts. Run
> `python scripts/gen-cli-reference.py` after changing the CLI.

<!-- BEGIN CLI REFERENCE -->

### `costhive estimate`

Pre-deploy cost estimate of IaC on disk (Infracost). No AWS account touched.

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--path` | str | `.` | Path to Terraform/CDK/CFN to price. |
| `--client-name` | str | — | Client/engagement name for the report header. |
| `--logo` | str | — | Path to a logo image embedded in the report header. |
| `--format` | str | `html,md,json` | Formats: html, md, json, pdf. |
| `--pdf` | bool | `False` | Shorthand to add PDF output. |
| `--pdf-engine` | str | `weasyprint` | PDF engine: weasyprint or chromium. |
| `--out` | str | `./reports` | Output directory for reports. |
| `--tool-output` | bool | `False` | Stream raw tool output. |

### `costhive scan`

Analyze one or more live AWS accounts and produce a dollar-ranked savings report.

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--profile` | str | — | AWS profile name. |
| `--role-arn` | list[str] | — | IAM role ARN to assume (STS). Repeat for multi-account analysis. |
| `--external-id` | str | — | External ID for role assumption. |
| `--regions` | str | — | Comma-separated regions (e.g. eu-central-1,us-east-1). |
| `--tools` | str | `steampipe,custodian` | Comma-separated tools. Default: steampipe, custodian. Add komiser/cloudquery/opencost with their respective flags. |
| `--categories` | str | — | Filter findings to these categories (idle, unused, rightsizing, untagged, commitment, storage_class, off_hours, network). |
| `--policy-dir` | str | — | Cloud Custodian policy directory (default: bundled). |
| `--komiser-export` | str | — | Path to a Komiser resources JSON export. |
| `--cloudquery-db-url` | str | — | Postgres URL to enable CloudQuery mode. |
| `--cloudquery-spec` | str | — | CloudQuery sync spec file. |
| `--opencost-export` | str | — | OpenCost /allocation JSON export (EKS). |
| `--client-name` | str | — | Client/engagement name for the report header. |
| `--logo` | str | — | Path to a logo image embedded in the report header. |
| `--format` | str | `html,md,json` | Comma-separated output formats: html, md, json, pdf. |
| `--pdf` | bool | `False` | Shorthand to add PDF output (the client deliverable). |
| `--pdf-engine` | str | `weasyprint` | PDF engine: weasyprint (default) or chromium. |
| `--out` | str | `./reports` | Output directory for reports. |
| `--yes`, `-y` | bool | `False` | Skip the confirmation prompt. |
| `--fail-under` | float | — | Exit non-zero if total estimated monthly savings is at/above this amount (CI cost gate). |
| `--tool-output` | bool | `False` | Stream raw tool stdout/stderr while commands run. Elapsed-time heartbeats are shown by default. |

### `costhive tools`

List available FinOps tools.

_No options._

<!-- END CLI REFERENCE -->
