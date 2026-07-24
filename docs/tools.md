# Integrated tools

CostHive orchestrates seven open-source FinOps tools behind one `CostTool` interface.
Each is wrapped in `costhive/tools/` and normalizes into the unified savings schema.
Any tool not found on `PATH` (or without its required input) is cleanly reported as
**skipped** — the run still produces a report from whatever ran.

| Tool | Role | Target | Enable with |
|------|------|--------|-------------|
| [Steampipe](https://github.com/turbot/steampipe) | core | live account — SQL cost/waste queries | default |
| [Cloud Custodian](https://github.com/cloud-custodian/cloud-custodian) | core | live account — policy-as-code (dry-run) | default |
| [Komiser](https://github.com/mlabouardy/komiser) | opt-in | inventory export — untagged gaps | `--komiser-export` |
| [CloudQuery](https://github.com/cloudquery/cloudquery) | opt-in | live account → external DB, then SQL | `--cloudquery-db-url` |
| [OpenCost](https://github.com/opencost/opencost) | opt-in | EKS — Kubernetes cost allocation | `--opencost-export` |
| [Robusta KRR](https://github.com/robusta-dev/krr) | opt-in | Kubernetes workload rightsizing | `--krr-export` |
| [Infracost](https://github.com/infracost/cli) | `estimate` | local IaC — pre-deploy cost | `costhive estimate` |

## Steampipe (core)

Runs CostHive's bundled FinOps SQL (`costhive/tools/queries.py`) via
`steampipe query --output json`, each query authored to emit the normalizer's column
contract. Needs the Steampipe **AWS plugin** (`steampipe plugin install aws`) and
read-only IAM. Covers unattached EBS/EIP, old snapshots, stopped instances, gp2→gp3.

## Cloud Custodian (core)

Runs the bundled policy packs (`policies/*.yml`) with `custodian run --dryrun` —
**report-only, nothing is modified**. Each policy's `metadata` block supplies the
savings category, per-resource estimate, confidence, and risk. Add your own packs
with `--policy-dir`.

## Komiser (opt-in)

Consumes a Komiser resources JSON export and flags high-cost **untagged** resources
as cost-allocation gaps (governance; `$0` direct savings). Provide `--komiser-export`
or set `COSTHIVE_KOMISER_EXPORT`.

## CloudQuery (opt-in / advanced)

Syncs AWS inventory to an **external Postgres**, then runs the same FinOps SQL over
it. Off by default because it needs a database. Enable with `--cloudquery-db-url`
(and `--cloudquery-spec`).

## OpenCost (opt-in / EKS)

Turns an OpenCost `/allocation` JSON export into namespace rightsizing findings
(`cost × (1 − efficiency)`). Provide `--opencost-export`. EKS clusters are
auto-detected and noted.

## Robusta KRR (opt-in / Kubernetes)

Consumes KRR's JSON formatter output and adds exact CPU/memory request changes to
the consolidated CostHive report:

```bash
krr simple -f json --fileoutput krr-report.json
costhive scan --profile p --opencost-export allocation.json \
  --krr-export krr-report.json --yes
```

Generating the export requires Kubernetes read access plus Prometheus,
kube-state-metrics, and cAdvisor. CostHive only reads the JSON and therefore does
not need kubeconfig or Prometheus credentials. KRR findings intentionally carry
`$0` unless OpenCost independently supplies the cost estimate; that prevents
invented or double-counted savings.

## Infracost (`estimate` verb)

Pre-deploy cost of Terraform/CDK/CFN on disk — does **not** touch a live account.
Run `costhive estimate --path ./terraform`. Infracost v2 requires an API key from
`infracost auth login`, supplied as `INFRACOST_API_KEY`.

## Version pinning

The Docker image pins each bundled CLI plus AWS CLI and the Steampipe AWS plugin;
`tool-versions.env` also tracks export-schema integrations such as KRR. CI pins
Gitleaks. FinOps tool/plugin bumps are called out in the
[CHANGELOG](../CHANGELOG.md) because they can change findings. `costhive tools`
and the report's "Tools" table show the running FinOps versions for
reproducibility.

A weekly [gh-aw](https://github.github.com/gh-aw/) agentic workflow
(`.github/workflows/tool-version-watch.md`, compiled to `tool-version-watch.lock.yml`)
runs on the Copilot coding-agent engine to check each pinned tool's upstream release, bump
`tool-versions.env`/`Dockerfile` when one is behind, patch any wrapper code the
release notes flag as breaking, and open a PR — Dependabot can't do this on its own
since these are release-tag pins, not package-manager manifest entries.
