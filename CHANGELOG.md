# Changelog

All notable changes to CostHive are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> **Savings-impacting changes** (bundled-tool version bumps, changes to
> savings-estimation logic) are called out explicitly — they change the dollar
> numbers you report to clients.

## [Unreleased]

## [0.0.1] - 2026-07-01

Initial release — the money-first sibling to
[SentryHive](https://github.com/d2k-klin/sentryhive).

### Added
- **Two verbs:** `scan` (live AWS account) and `estimate` (pre-deploy IaC cost via
  Infracost).
- **Six bundled FinOps tools** behind one interface: Steampipe + Cloud Custodian
  (core), Komiser / CloudQuery / OpenCost (opt-in), Infracost (`estimate`).
- **Unified savings schema** — every tool normalizes into one shape ranked by
  `estimated_monthly_savings`, with `category`, `confidence`, and `risk`.
- **Money-first report** (HTML / Markdown / JSON, optional PDF): headline total
  savings, savings-by-category, top opportunities, and quick wins.
- **"Don't overpromise" guardrails** (consultant addendum §5): every finding carries
  a `risk` level (safe / moderate / judgment-call); the report splits **safe savings**
  from **judgment-call savings**, and quick wins exclude risky or low-confidence
  estimates.
- **Cross-account first auth:** profile / static keys / assume-role with
  `--external-id`; multi-account runs produce per-account reports plus a roll-up.
- **Read-only & safe:** least-privilege IAM policy (incl. Cost Explorer / Compute
  Optimizer read), client-onboarding CloudFormation role, and Cloud Custodian running
  in `--dryrun` (report-only).
- **Graceful degradation** when Cost Explorer / Compute Optimizer aren't enabled — a
  preflight probe surfaces exactly what to turn on.
- **CI cost gate** via `--fail-under`.

[Unreleased]: https://github.com/d2k-klin/costhive/compare/v0.0.1...HEAD
[0.0.1]: https://github.com/d2k-klin/costhive/releases/tag/v0.0.1
