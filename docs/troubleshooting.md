# Troubleshooting

Symptom → cause → fix.

## "No findings" / much lower savings than expected

**Cause:** Cost Explorer / Compute Optimizer not enabled, or the identity lacks
`ce:*` / `compute-optimizer:*` reads. Spend-history and rightsizing findings need
them.

**Fix:** Enable Cost Explorer (wait ~24h) and opt into Compute Optimizer — see
[cost-data-setup.md](cost-data-setup.md). CostHive prints a yellow note and a
"Cost-data prerequisites" section when these are missing. Basic waste findings
(unattached EBS/EIP, gp2→gp3) work without them.

## A tool shows `skipped`

**Cause:** its binary isn't on `PATH`, or an opt-in tool wasn't given its input.

**Fix:** Use the Docker image (bundles the CLIs), or install the tool locally. For
opt-in tools, provide `--komiser-export` / `--cloudquery-db-url` / `--opencost-export`.
A skipped tool is expected, not an error — the report still generates.

## `Authentication failed` / `Could not verify AWS credentials`

**Cause:** bad/expired credentials, wrong profile, or an assume-role failure
(missing/incorrect `--external-id`, trust policy mismatch).

**Fix:** Confirm `aws sts get-caller-identity` works with the same profile/role.
For a role, verify the trust policy allows your principal and that the external ID
matches. See [authentication.md](authentication.md).

## `Failed to assume role ... AccessDenied`

**Cause:** the audit role's trust policy doesn't trust your principal, or the
external ID is wrong.

**Fix:** Redeploy the role from [iam/audit-role.cfn.yaml](../iam/audit-role.cfn.yaml)
with the correct `TrustedPrincipalArn` and `ExternalId`.

## Region errors / empty results in some regions

**Cause:** the service isn't used in that region, or the region isn't opted-in.

**Fix:** Scope with `--regions`. Steampipe queries tolerate per-service/per-region
gaps and skip them rather than failing the whole run.

## `permission denied` on specific describe/list calls

**Cause:** the policy is missing an action a tool needs.

**Fix:** Attach [iam/least-privilege-policy.json](../iam/least-privilege-policy.json)
alongside AWS-managed `ViewOnlyAccess`. See [iam-permissions.md](iam-permissions.md).

## CloudQuery does nothing

**Cause:** it's opt-in and needs an external Postgres.

**Fix:** Provide `--cloudquery-db-url` and `--cloudquery-spec`, and ensure `psql`
is available. See [tools.md](tools.md#cloudquery-opt-in--advanced).

## PDF wasn't produced

**Cause:** WeasyPrint (or its system libs) isn't installed.

**Fix:** Use the Docker image, or `pip install "costhive[pdf]"` plus pango/cairo. A
PDF failure never blocks the HTML/MD/JSON outputs. Try `--pdf-engine chromium` if
you have Chrome/Chromium. See [reports.md](reports.md#pdf-rendering).

## Still stuck?

Open a [bug report](https://github.com/d2k-klin/costhive/issues/new/choose) — and
**sanitize** credentials, account IDs, and ARNs first.
