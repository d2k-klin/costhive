# ⬡ CostHive

> Point it at an AWS account and get a money-first cost-optimization report from best-in-class open-source FinOps tools — no manual tool wrangling.

[![CI](https://github.com/d2k-klin/costhive/actions/workflows/ci.yml/badge.svg)](https://github.com/d2k-klin/costhive/actions/workflows/ci.yml)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](pyproject.toml)
[![Read-only](https://img.shields.io/badge/AWS-read--only-green.svg)](iam/least-privilege-policy.json)

CostHive orchestrates several open-source AWS FinOps tools behind **one command** and merges their output into **one consolidated, dollar-ranked report** — a single list of *"$X/mo saved by doing Y"* instead of six dashboards. It's the cost sibling to [SentryHive](https://github.com/d2k-klin/sentryhive): same orchestration pattern and report engine, but findings are ranked by **savings** rather than severity.

```bash
docker compose run --rm costhive scan \
  --role-arn arn:aws:iam::CLIENT:role/CostHiveAudit \
  --external-id shared-secret --client-name "Acme Corp"
# → ./reports/report.html (branded), report.md, findings.json
```

See a rendered example: [examples/sample-report.md](examples/sample-report.md) · [examples/sample-report.html](examples/sample-report.html).

> ⚠️ **Before you run:** basic waste findings work out of the box, but historical
> spend, forecasts and rightsizing need **Cost Explorer enabled** in the account
> (~24h to populate). If you get few/no findings, this is almost always why — see
> [docs/cost-data-setup.md](docs/cost-data-setup.md). Only analyze accounts you're
> authorized to.

---

## Why

1. **Zero-setup** — one Docker image bundles every FinOps tool. You install nothing but Docker.
2. **Money-first report** — the headline is one number: total estimated monthly savings. Broken down by category, with the top opportunities and "quick wins" called out.
3. **Pre-deploy + live + Kubernetes** — cost before deploy (Infracost), in the running account (Steampipe/Custodian/Komiser/CloudQuery), and in EKS (OpenCost).
4. **Trust-first & read-only** — ships a least-privilege IAM policy; Cloud Custodian runs in **dry-run** (report-only). No data leaves your machine.
5. **Cross-account first** — assume-role with `--external-id`; analyze **many client accounts in one run** with a per-account report plus a roll-up.

## Bundled tools

| Tool | What it does | Role |
|------|--------------|------|
| [Steampipe](https://github.com/turbot/steampipe) | SQL over live AWS APIs — waste/savings queries | **core** (`scan`) |
| [Cloud Custodian](https://github.com/cloud-custodian/cloud-custodian) | Policy-as-code — idle/unused/untagged (dry-run) | **core** (`scan`) |
| [Komiser](https://github.com/mlabouardy/komiser) | Inventory + cost/governance — untagged gaps | opt-in (`--komiser-export`) |
| [CloudQuery](https://github.com/cloudquery/cloudquery) | Sync AWS inventory to a DB, then SQL | opt-in (`--cloudquery-db-url`) |
| [OpenCost](https://github.com/opencost/opencost) | Kubernetes/EKS cost allocation | opt-in (`--opencost-export`) |
| [Infracost](https://github.com/infracost/infracost) | Pre-deploy cost of Terraform/CDK/CFN | `estimate` verb |

The default `scan` runs **Steampipe + Custodian**. The opt-in tools activate when you supply their input. Infracost powers the separate `estimate` verb (local IaC, no AWS account touched).

## Quick start (Docker — recommended)

```bash
git clone https://github.com/d2k-klin/costhive
cd costhive
docker compose build

# Live-account scan with a profile
docker compose run --rm costhive scan --profile my-aws-profile

# Cross-account via a read-only audit role
docker compose run --rm costhive scan \
  --role-arn arn:aws:iam::123456789012:role/CostHiveAudit \
  --external-id shared-secret --client-name "Acme Corp" --pdf

# Focus on specific categories and regions
docker compose run --rm costhive scan --profile my-aws-profile \
  --categories idle,unused,rightsizing --regions eu-central-1,us-east-1

# Pre-deploy IaC cost estimate (no AWS account touched)
COSTHIVE_IAC=./terraform docker compose run --rm costhive estimate --path /iac
```

## Local install (without Docker)

```bash
pip install -e .
# Install whichever tools you want on PATH: steampipe (+aws plugin), custodian, infracost.
costhive scan --profile my-aws-profile
```

Any tool not found on `PATH` is cleanly reported as **skipped** — CostHive still produces a report from whatever ran.

## The unified savings schema

Every tool's output normalizes into one shape (see [costhive/models.py](costhive/models.py)):

| Field | Meaning |
|-------|---------|
| `estimated_monthly_savings` | The sort key — dollars per month. |
| `category` | idle · rightsizing · unused · untagged · commitment · storage_class · off_hours · network |
| `confidence` | high / medium / low — CostHive never overpromises a shaky estimate. |
| `resource`, `service`, `region`, `account_id` | What & where. |
| `recommended_action` | The "do Y" half of "$X/mo by doing Y". |

## Authentication

Three methods (details in [docs/iam-permissions.md](docs/iam-permissions.md)):

1. **AWS profile** — `--profile myprofile`
2. **Static keys** — env `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` / `AWS_SESSION_TOKEN` (env only, never flags)
3. **Assume role** — `--role-arn ...` with `--external-id`, cross-account

CostHive always runs `sts:GetCallerIdentity` first and prints the account being analyzed.

## Cost-data prerequisites

Unlike a pure inventory scan, full cost value depends on **Cost Explorer** and **Compute Optimizer** being enabled. CostHive probes for these up front and tells you what to turn on rather than failing opaquely. See [docs/cost-data-setup.md](docs/cost-data-setup.md).

## Documentation

| | |
|---|---|
| [Getting started](docs/getting-started.md) | 5-minute first report |
| [Installation](docs/installation.md) · [Usage](docs/usage.md) | Install methods · every command & flag |
| [Authentication](docs/authentication.md) · [IAM permissions](docs/iam-permissions.md) | Auth modes · least-privilege policy + client onboarding |
| [Cost-data setup](docs/cost-data-setup.md) | Enabling Cost Explorer / CUR |
| [Reports](docs/reports.md) · [Categories](docs/categories.md) | Interpreting savings, confidence & risk |
| [Tools](docs/tools.md) · [Configuration](docs/configuration.md) · [CI/CD](docs/ci-cd.md) | Bundled tools · config reference · pipelines |
| [Architecture](docs/architecture.md) · [Troubleshooting](docs/troubleshooting.md) · [FAQ](docs/faq.md) | How it works · fixes · questions |

Full index: [docs/index.md](docs/index.md).

## CI cost gate

```bash
costhive scan --profile ci --fail-under 500 --yes
# exits non-zero if ≥ $500/mo of identified savings is going unactioned
```

## Safety

- **Read-only by design.** The shipped IAM policy grants no write/delete actions.
- **Cloud Custodian runs `--dryrun`** — it only *reports*, never modifies. Remediation is a deferred v2 feature behind an explicit flag.
- **Estimates, not invoices.** Savings figures use public list prices to *rank* opportunities; validate against your own usage before acting.

## License

Apache-2.0 — see [LICENSE](LICENSE).
