# Cost-data prerequisites

Unlike a pure inventory/security scan, cost analysis is most valuable when AWS's
billing data sources are turned on. CostHive works without them, but degrades
gracefully and tells you what to enable.

## Cost Explorer

- **What it powers:** historical spend, forecasts, rightsizing and Savings
  Plans/RI recommendations.
- **Enable it:** Billing console → **Cost Explorer** → *Enable*. Data becomes
  available ~24 hours after enabling.
- **Permissions:** `ce:Get*`, `ce:List*`, `ce:Describe*` (see
  [iam/least-privilege-policy.json](../iam/least-privilege-policy.json)).

On start-up CostHive calls a lightweight Cost Explorer probe. If it's disabled or
you lack access, you'll see a yellow note in the console and a
**"Cost-data prerequisites"** section in the report — the scan still runs.

## Compute Optimizer

- **What it powers:** EC2 / Auto Scaling / EBS / Lambda rightsizing
  recommendations.
- **Enable it:** Compute Optimizer console → *Opt in*. Recommendations appear
  after it has observed ~12 hours of CloudWatch metrics (fuller signal after 14
  days).
- **Permissions:** `compute-optimizer:Get*`.

## Cost and Usage Reports (CUR) — optional

For the deepest analysis (per-resource, tag-level spend), enable a CUR delivered to
S3. CostHive does not require it for v1 but future versions will read it when
present.

## Cloud Custodian metrics filters

Some bundled Custodian policies (idle RDS, low-utilization EC2) query CloudWatch
metrics, which requires `cloudwatch:GetMetricStatistics` / `GetMetricData` /
`ListMetrics`. These are included in the shipped IAM policy.
