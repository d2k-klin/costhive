# Savings categories, confidence & risk

Every CostHive finding carries three classifiers. This page explains what each means
and **how the dollar estimates are derived** — read it before defending a number to
a client.

## Categories

The category is the axis the exec summary breaks spend down by. Each finding lands
in exactly one.

| Category | What it means | Typical sources |
|----------|---------------|-----------------|
| **Idle** | Running (or stopped-but-still-billing) with no useful work. | Idle RDS (0 connections), stopped instances still paying for EBS. |
| **Rightsizing** | Provisioned larger than actual utilization. | EC2 under low CPU, over-provisioned EKS namespaces (OpenCost). |
| **Unused / orphaned** | Not attached to anything. | Unattached EBS volumes, unassociated Elastic IPs, old snapshots. |
| **Storage class** | On a pricier tier than needed. | gp2 volumes that could be gp3. |
| **Commitment** | Savings Plans / Reserved Instance coverage gaps. | (Roadmap — high value, deferred.) |
| **Off-hours** | Non-prod that could be stopped nights/weekends. | (Roadmap.) |
| **Network** | Data-transfer / NAT / cross-AZ waste. | (Roadmap.) |
| **Untagged** | No cost-allocation tags — a governance gap, not a deletable resource. | Komiser, Custodian tag policies. Savings shown as `$0`. |

## Confidence — how sure we are of the *estimate*

Tools disagree on dollar figures. Confidence keeps us honest.

| Confidence | Meaning |
|------------|---------|
| **High** | Directly observable and priced (e.g. an unattached EBS volume × its GB price). |
| **Medium** | Reasonable estimate with assumptions (e.g. rightsizing a low-CPU instance one size down). |
| **Low** | Rough / heuristic (e.g. an old snapshot that *may* be outside retention). |

## Risk — how safe it is to *act* (the "don't overpromise" axis)

Separate from confidence. A high-confidence estimate can still be a risky action.

| Risk | Meaning | Examples |
|------|---------|----------|
| **Safe** | Reversible, no workload impact. | Delete an unattached EBS volume, release an EIP, apply tags. |
| **Moderate** | Low-impact change. | gp2 → gp3 (online, no downtime). |
| **Judgment call** | Needs human judgment; could affect a workload. | Rightsize a prod instance, delete a snapshot, stop an RDS instance. |

The report splits **safe savings** from **judgment-call savings** so you never front
a risky number as banked. **Quick wins** are deliberately limited to safe/moderate,
defensible (≥ medium confidence) opportunities.

## How estimates are computed

CostHive uses **public on-demand list prices** baked in as constants purely to
*rank* opportunities — not to reproduce a client's negotiated/EDP pricing. That's why
price-derived findings are rarely "high" confidence. Examples:

- **Unattached EBS:** `size_GB × gp3 $/GB-month`.
- **Unassociated EIP:** flat ~$3.60/mo (idle-EIP hourly rate).
- **gp2 → gp3:** `size_GB × (gp2 − gp3) $/GB-month`.
- **OpenCost rightsizing:** `namespace_monthly_cost × (1 − efficiency)`.

Custodian policy findings take their per-resource estimate from the policy's
`metadata.monthly_savings_each` (see [tools.md](tools.md) and the packs in
`policies/`).

> **Always validate against the client's actual usage and pricing before acting.**
> The report says this in its footer for the same reason.

See also: [reports.md](reports.md) for how these appear in the report.
