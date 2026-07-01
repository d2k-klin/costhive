# 🐝 CostHive Cost-Optimization Report
**Client:** Acme Corp

## Run metadata

| | |
|---|---|
| **Mode** | Live-account scan |
| **Account** | `123456789012` |
| **Identity** | `arn:aws:iam::123456789012:role/CostHiveAudit` |
| **Regions** | us-east-1 |
| **Generated** | 2026-07-01 00:00:00 UTC |
| **CostHive** | v0.0.1 |
| **Tools** | steampipe (Steampipe v2.4.4), custodian (custodian 0.9.51), komiser (komiser 3.1.22), opencost (opencost 1.120.4) |

## Executive summary

> ### 💰 Total estimated monthly savings: **$268.00**
> _($3,216.00/year across 8 opportunities)_
>
> **✅ Safe to reclaim now:** $11.60/mo · **⚖️ Needs a judgment call:** $250.00/mo
>
> _Figures are estimates based on public list prices, provided to rank opportunities — validate against your own usage before acting. Safe items are reversible/no-impact; judgment-call items may affect a workload._

### Savings by category

| Category | Opportunities | Est. monthly savings | Annual |
|----------|---------------|----------------------|--------|
| Rightsizing | 3 | $130.00 | $1,560.00 |
| Idle resources | 1 | $120.00 | $1,440.00 |
| Unused / orphaned | 2 | $11.60 | $139.20 |
| Storage class | 1 | $6.40 | $76.80 |
| Untagged (governance) | 1 | $0.00 | $0.00 |

### Savings by risk (how safe is it to act?)

| Risk | Opportunities | Est. monthly savings |
|------|---------------|----------------------|
| Safe | 3 | $11.60 |
| Moderate | 1 | $6.40 |
| Judgment call | 4 | $250.00 |

### ⚡ Quick wins (high confidence, do these first)

| Est. monthly savings | Resource | Action |
|----------------------|----------|--------|
| **$8.00** | `vol-0aaaaaaaaaaaaaaa1` | Snapshot then delete the volume. |
| **$6.40** | `vol-0ccccccccccccccc3` | Modify volume type gp2 -> gp3 (online). |
| **$3.60** | `eipalloc-0bbbbbbbbbbbbbbb2` | Release the Elastic IP if no longer needed. |

### Top 8 opportunities by dollar impact

| # | Est. monthly savings | Confidence | Risk | Category | Tool | Resource | Opportunity |
|---|----------------------|------------|------|----------|------|----------|-------------|
| 1 | $120.00 | Medium | Judgment call | Idle resources | custodian | `db-legacy-1` | rds-idle-no-connections |
| 2 | $70.00 | Medium | Judgment call | Rightsizing | opencost | `analytics` | Over-provisioned namespace: analytics |
| 3 | $30.00 | Medium | Judgment call | Rightsizing | custodian | `i-0ddddddddddddddd4` | ec2-low-utilization |
| 4 | $30.00 | Medium | Judgment call | Rightsizing | custodian | `i-0eeeeeeeeeeeeeee5` | ec2-low-utilization |
| 5 | $8.00 | High | Safe | Unused / orphaned | steampipe | `vol-0aaaaaaaaaaaaaaa1` | Unattached EBS volume |
| 6 | $6.40 | Medium | Moderate | Storage class | steampipe | `vol-0ccccccccccccccc3` | EBS gp2 volume can migrate to gp3 |
| 7 | $3.60 | High | Safe | Unused / orphaned | steampipe | `eipalloc-0bbbbbbbbbbbbbbb2` | Unassociated Elastic IP |
| 8 | $0.00 | High | Safe | Untagged (governance) | komiser | `prod-orphan-worker` | Untagged resource: prod-orphan-worker |

## Tools

| Tool | Status | Findings | Est. savings | Version | Notes |
|------|--------|----------|--------------|---------|-------|
| steampipe | ok | 3 | $18.00 | Steampipe v2.4.4 | 5/5 queries ran |
| custodian | ok | 3 | $180.00 | custodian 0.9.51 | 2 policy file(s) evaluated (dry-run, no changes made) |
| komiser | ok | 1 | $0.00 | komiser 3.1.22 | 1 untagged cost-allocation gap(s) |
| opencost | ok | 1 | $70.00 | opencost 1.120.4 |  |

## All opportunities

### $120.00/mo — rds-idle-no-connections

- **Category:** Idle resources · **Confidence:** Medium · **Risk:** Judgment call
- **Source tool:** custodian
- **Service:** rds
- **Resource:** `db-legacy-1`
- **Why:** RDS instance with zero connections over 7 days.
- **Recommended action:** Snapshot and stop/delete; confirm truly unused.

### $70.00/mo — Over-provisioned namespace: analytics

- **Category:** Rightsizing · **Confidence:** Medium · **Risk:** Judgment call
- **Source tool:** opencost
- **Service:** eks
- **Resource:** `analytics`
- **Why:** Namespace 'analytics' in prod-eks runs at 30% resource efficiency, wasting ~$70.00/mo of its $100.00/mo spend.
- **Recommended action:** Right-size CPU/memory requests to match actual usage (verify headroom for peak load first).

### $30.00/mo — ec2-low-utilization

- **Category:** Rightsizing · **Confidence:** Medium · **Risk:** Judgment call
- **Source tool:** custodian
- **Service:** ec2
- **Resource:** `i-0ddddddddddddddd4`
- **Why:** Instances under 5% average CPU over 14 days.
- **Recommended action:** Downsize the instance type; verify peak-load headroom first.

### $30.00/mo — ec2-low-utilization

- **Category:** Rightsizing · **Confidence:** Medium · **Risk:** Judgment call
- **Source tool:** custodian
- **Service:** ec2
- **Resource:** `i-0eeeeeeeeeeeeeee5`
- **Why:** Instances under 5% average CPU over 14 days.
- **Recommended action:** Downsize the instance type; verify peak-load headroom first.

### $8.00/mo — Unattached EBS volume

- **Category:** Unused / orphaned · **Confidence:** High · **Risk:** Safe
- **Source tool:** steampipe
- **Service:** ebs · **Region:** us-east-1
- **Resource:** `vol-0aaaaaaaaaaaaaaa1`
- **Why:** Volume is in the 'available' state and still billing.
- **Recommended action:** Snapshot then delete the volume.

### $6.40/mo — EBS gp2 volume can migrate to gp3

- **Category:** Storage class · **Confidence:** Medium · **Risk:** Moderate
- **Source tool:** steampipe
- **Service:** ebs · **Region:** us-east-1
- **Resource:** `vol-0ccccccccccccccc3`
- **Why:** gp3 delivers baseline performance at ~20% lower per-GB cost.
- **Recommended action:** Modify volume type gp2 -> gp3 (online).

### $3.60/mo — Unassociated Elastic IP

- **Category:** Unused / orphaned · **Confidence:** High · **Risk:** Safe
- **Source tool:** steampipe
- **Service:** ec2 · **Region:** us-east-1
- **Resource:** `eipalloc-0bbbbbbbbbbbbbbb2`
- **Why:** Elastic IP is allocated but not associated.
- **Recommended action:** Release the Elastic IP if no longer needed.

### $0.00/mo — Untagged resource: prod-orphan-worker

- **Category:** Untagged (governance) · **Confidence:** High · **Risk:** Safe
- **Source tool:** komiser
- **Service:** ec2 · **Region:** us-east-1
- **Resource:** `prod-orphan-worker`
- **Why:** ec2 'prod-orphan-worker' costs ~$90.00/mo but has no cost-allocation tags, so its spend cannot be attributed to a team or project.
- **Recommended action:** Apply cost-allocation tags (owner, environment, cost-center) for chargeback.


---
_Generated by [CostHive](https://github.com/d2k-klin/costhive) v0.0.1. Savings are estimates — validate against your own usage before acting. No data leaves your machine._