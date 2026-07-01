# FAQ

**Does CostHive change anything in my account?**
No. It's read-only; the shipped IAM policy grants no write/delete actions, and Cloud
Custodian runs in `--dryrun`. Remediation is a deferred v2 feature behind an explicit
flag.

**Does my data leave my machine?**
No. All analysis and report generation (including PDF) runs locally. Credentials are
never logged or written to reports.

**Do I have to enable Cost Explorer?**
Not for basic waste findings — but yes for spend history, forecasts, and rightsizing.
See [cost-data-setup.md](cost-data-setup.md).

**Are the savings numbers exact?**
No — they're estimates from public list prices, used to *rank* opportunities. Each
carries a **confidence** and a **risk** level, and the report separates safe savings
from judgment-call savings. Validate against your own usage before acting. See
[categories.md](categories.md).

**Can I scan several client accounts at once?**
Yes — repeat `--role-arn`. You get a per-account report plus a roll-up. See
[usage.md](usage.md#scan-multiple-accounts).

**How is this different from just running the tools myself?**
Zero setup (one Docker image), and one money-first, `$`-ranked report instead of six
dashboards to reconcile.

**How does it relate to SentryHive?**
CostHive is the cost sibling to [SentryHive](https://github.com/d2k-klin/sentryhive):
same orchestration and report engine, but findings rank by **savings** instead of
severity. A consultant can offer security + cost audits from one family of tools.

**Which tools run by default?**
Steampipe + Cloud Custodian. Komiser, CloudQuery, and OpenCost are opt-in; Infracost
powers the separate `estimate` verb. See [tools.md](tools.md).

**Can I add my own cost checks?**
Yes — add a Cloud Custodian policy pack (`policies/*.yml`) or a new `CostTool`. See
[../CONTRIBUTING.md](../CONTRIBUTING.md).

**Is there a hosted/SaaS version?**
No — CostHive is a local CLI by design. Everything stays on your machine.
