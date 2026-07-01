# Authentication

CostHive resolves AWS credentials through standard mechanisms and always calls
`sts:GetCallerIdentity` first, printing the account and identity before doing
anything. **Credentials never leave your machine** and are never written to reports.

## The three methods

CostHive tries them in this order (consultant-first — assume-role is the primary
path):

### 1. Assume role (primary for consultants)

```bash
costhive scan \
  --role-arn arn:aws:iam::123456789012:role/CostHiveAudit \
  --external-id shared-secret
```

- `--external-id` guards against the confused-deputy problem and is standard for
  third-party access. Use it.
- Repeat `--role-arn` to analyze several accounts in one run (per-account reports +
  a roll-up).
- Deploy the read-only audit role in the client account with the shipped
  CloudFormation template — see [iam-permissions.md](iam-permissions.md#cross-account-audit-role-consultants).

### 2. AWS profile

```bash
costhive scan --profile client-x
```

Uses a named profile from `~/.aws/config` / `~/.aws/credentials`. In Docker,
`~/.aws` is mounted read-only.

### 3. Static keys (env vars only)

```bash
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
export AWS_SESSION_TOKEN=...        # if using temporary creds
costhive scan
```

Never pass keys as CLI flags — they'd leak into shell history and process lists.
Environment variables only.

## Credential precedence

When a role ARN is given, the profile/env credentials establish a **base session**
that is used to assume the role; the assumed-role's temporary credentials are what
the tools actually run as. Without a role ARN, the profile (or ambient env keys) is
used directly.

## Regions

Pass `--regions eu-central-1,us-east-1` to scope the analysis. If omitted, CostHive
uses the session's region (or `AWS_DEFAULT_REGION`, falling back to `us-east-1`).

## What you'll be asked

Before scanning, CostHive prints a confirmation panel (account, identity, regions,
tools) and notes that the run is read-only and Cloud Custodian is dry-run. Pass
`--yes`/`-y` to skip the prompt (e.g. in CI).

See also: [iam-permissions.md](iam-permissions.md) for the exact policy.
