# Getting started

Get your first dollar-ranked savings report in about 5 minutes. This is the happy
path — one profile, one account, Docker.

## Prerequisites

- **Docker** installed.
- An **AWS account (or role) you are authorized to analyze.** Only ever point
  CostHive at accounts you have permission to audit.
- **Read-only credentials** configured as a local AWS profile (see
  [authentication.md](authentication.md)).
- Ideally, **Cost Explorer enabled** in that account for the fullest results — but
  basic waste findings work without it (see [cost-data-setup.md](cost-data-setup.md)).

## Step 1 — Get CostHive

```bash
git clone https://github.com/d2k-klin/costhive
cd costhive
docker compose build
```

## Step 2 — Provide credentials

The simplest path is an existing AWS profile. `docker-compose.yml` mounts
`~/.aws` read-only, so your profiles are available inside the container:

```bash
export AWS_PROFILE=my-sandbox
```

## Step 3 — Run your first scan

```bash
docker compose run --rm costhive scan --profile my-sandbox --yes
```

You'll see each tool run, then a summary:

```
💰 Total estimated monthly savings: $128.40 ($1,540.80/yr, 9 opportunities)
   ✅ safe to reclaim: $46.00/mo · ⚖️  judgment call: $82.40/mo
```

## Step 4 — Open your report

Reports land in `./reports/` on your host:

```bash
open reports/report.html      # macOS  (xdg-open on Linux)
```

The headline savings number is at the top, followed by savings-by-category,
quick wins, and every opportunity with its resource, estimated `$`/mo, confidence,
and risk.

## Next steps

- Analyze a client account with a **read-only role**: [authentication.md](authentication.md).
- Scan **several accounts at once** and get a roll-up: [usage.md](usage.md#scan-multiple-accounts).
- Price Terraform **before deploy**: [usage.md](usage.md#pre-deploy-estimate).
- Wire it into **CI**: [ci-cd.md](ci-cd.md).
- Understand and defend the numbers: [categories.md](categories.md) · [reports.md](reports.md).
