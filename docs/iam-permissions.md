# IAM permissions & authentication

CostHive is **read-only**. The shipped policy grants no write or delete actions, and
Cloud Custodian always runs in `--dryrun` (report-only).

## Authentication methods

In priority order:

1. **AWS profile** — `--profile myprofile`
2. **Static keys** — environment variables only:
   `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`.
   Never pass keys as CLI flags.
3. **Assume role** — `--role-arn arn:aws:iam::ACCOUNT:role/CostHiveAudit`
   with `--external-id shared-secret`. Repeat `--role-arn` to analyze several
   accounts in one run.

CostHive always calls `sts:GetCallerIdentity` first and prints the account and
identity before doing anything.

## Least-privilege policy

Attach [iam/least-privilege-policy.json](../iam/least-privilege-policy.json)
alongside the AWS-managed **ViewOnlyAccess** policy. It adds the cost-specific
extras the FinOps tools need:

- **Cost Explorer** reads (`ce:Get*` / `ce:List*` / `ce:Describe*`)
- **Compute Optimizer** reads (`compute-optimizer:Get*`)
- **CloudWatch metrics** reads (for Custodian's idle/low-utilization filters)
- A few EC2/RDS/ELB/EKS describe/list calls

## Cross-account audit role (consultants)

Deploy [iam/audit-role.cfn.yaml](../iam/audit-role.cfn.yaml) in each client
account. It creates a `CostHiveAudit` role that trusts your principal and requires
an `ExternalId` (confused-deputy protection):

```bash
aws cloudformation deploy \
  --template-file iam/audit-role.cfn.yaml \
  --stack-name costhive-audit \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides \
      TrustedPrincipalArn=arn:aws:iam::YOURACCT:user/you \
      ExternalId=shared-secret
```

Then:

```bash
costhive scan --role-arn arn:aws:iam::CLIENT:role/CostHiveAudit --external-id shared-secret
```
