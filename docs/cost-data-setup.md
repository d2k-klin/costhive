# AWS data-source coverage

CostHive v0.0.6 does not require AWS billing services. The core live-account scan
uses inventory APIs plus CloudWatch metrics, and currently checks:

- unattached EBS volumes and unassociated Elastic IPs;
- gp2 volumes that can move to gp3;
- stopped EC2 instances with attached EBS;
- owned EBS snapshots older than one year;
- RDS instances with no connections over seven days;
- running EC2 instances with average CPU below 5% over 14 days;
- missing owner/cost-center tags.

A zero result means none of these completed checks matched in the selected regions.
It is not a complete optimization certification.

## Not imported yet

The current release does **not** import recommendations or costs from:

- AWS Cost Explorer;
- AWS Compute Optimizer;
- Cost and Usage Reports (CUR).

Enabling those services alone therefore does not change a v0.0.6 report, and the
shipped least-privilege role does not request their permissions. Native imports can
be added later as explicit tools, with their findings normalized into the same
consolidated report.

## CloudWatch metrics

The bundled idle-RDS and low-utilization-EC2 policies query CloudWatch and need
`cloudwatch:GetMetricStatistics`, `cloudwatch:GetMetricData`, and
`cloudwatch:ListMetrics`. These reads are included in the shipped IAM policy.

## Kubernetes and IaC inputs

EKS discovery uses read-only AWS APIs. Kubernetes cost allocation and workload
rightsizing require OpenCost and/or KRR JSON exports; CostHive does not need
cluster-admin access to ingest them. Pre-deploy IaC estimation uses Infracost and
requires `INFRACOST_API_KEY`.

See also: [iam-permissions.md](iam-permissions.md) ·
[troubleshooting.md](troubleshooting.md) · [tools.md](tools.md).
