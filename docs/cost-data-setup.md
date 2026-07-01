# Cost-data setup (Cost Explorer & CUR)

> **This is the #1 cause of "CostHive returned no findings."** Unlike a pure
> inventory scan, full cost value depends on AWS's billing data sources being
> enabled. CostHive works without them, but degrades gracefully and tells you
> exactly what to turn on.

## What CostHive can do without any billing setup

The core waste queries (Steampipe + Cloud Custodian) work from **describe/list +
CloudWatch metrics** alone — no Cost Explorer required. You still get:

- Unattached EBS volumes and Elastic IPs
- Old snapshots
- Idle / low-utilization EC2 and RDS (via CloudWatch metrics)
- gp2→gp3 storage-class opportunities
- Untagged resources

So a brand-new account with nothing enabled still produces a useful report.

## Cost Explorer

- **What it powers:** historical spend, forecasts, and Cost-Explorer-based
  rightsizing / Savings Plans / RI recommendations.
- **Enable it:** Billing console → **Cost Explorer** → *Enable Cost Explorer*.
  Data becomes available **~24 hours** after enabling.
- **Permissions:** `ce:Get*`, `ce:List*`, `ce:Describe*` — included in
  [iam/least-privilege-policy.json](../iam/least-privilege-policy.json).

On start-up CostHive runs a lightweight Cost Explorer probe. If it's disabled or
you lack access, you'll see a yellow note in the console **and** a
**"Cost-data prerequisites"** section in the report — the scan still completes.

## Compute Optimizer

- **What it powers:** EC2 / Auto Scaling / EBS / Lambda rightsizing recommendations.
- **Enable it:** Compute Optimizer console → *Opt in*. Recommendations appear after
  it has observed ~12 hours of CloudWatch metrics (fuller signal after 14 days).
- **Permissions:** `compute-optimizer:Get*`.

## Cost and Usage Reports (CUR) — optional, deepest analysis

For per-resource, tag-level spend attribution, enable a **CUR** delivered to S3
(Billing console → *Cost & Usage Reports* → *Create report*). CostHive does not
require CUR for v1, but future versions will read it when present.

## Cloud Custodian metric filters

Some bundled Custodian policies (idle RDS, low-utilization EC2) query CloudWatch
metrics and need `cloudwatch:GetMetricStatistics` / `GetMetricData` / `ListMetrics`.
These are included in the shipped IAM policy.

## Quick checklist

| Want | Enable |
|------|--------|
| Basic waste findings | Nothing — works out of the box |
| Spend history & forecasts | Cost Explorer (wait ~24h) |
| Rightsizing recommendations | Compute Optimizer (opt-in) |
| Per-resource / tag cost attribution | Cost and Usage Reports (CUR) |

See also: [iam-permissions.md](iam-permissions.md) · [troubleshooting.md](troubleshooting.md).
