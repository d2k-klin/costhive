# Changelog

All notable changes to CostHive are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> **Savings-impacting changes** (bundled-tool version bumps, changes to
> savings-estimation logic) are called out explicitly — they change the dollar
> numbers you report to clients.

## [Unreleased]

## [0.0.3] - 2026-07-01

### Fixed
- **Steampipe root user error:** container now runs as non-root `steampipe` user,
  resolving "Steampipe cannot be run as the root user" failures.
- **Custodian policy discovery:** set `COSTHIVE_POLICY_DIR=/app/policies` in the
  Docker image so bundled policies are found correctly when installed as a package.
- **AWS credentials mount:** updated `docker-compose.yml` to mount `~/.aws` into
  the non-root user's home (`/home/steampipe/.aws`).

## [0.0.2] - 2026-07-01

### Fixed
- **Infracost install:** replaced unreliable `curl | sh` install script with direct
  GitHub Releases download in both `Dockerfile` and CI `tool-integrity` job (fixes
  `gzip: stdin: not in gzip format` build failures).

### Added
- **Python 3.14 in CI test matrix:** validates compatibility before merging
  Dependabot's base-image bump PR.

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
- Project CI: SHA-pinned `ci.yml` (lint + mypy, test matrix, policy-check,
  tool-integrity, build, docs, secret-scan, pip-audit), `release.yml`
  (GHCR + Release from CHANGELOG), `codeql.yml`, and Dependabot.
- Sanitized tool-output fixtures + golden-file report test + `test_savings.py`
  (exact savings-math guard), `test_policies.py` (no-remediation assertion), and
  `test_cli.py`.
- `tool-versions.env` as the single source of truth for bundled-tool versions.
- `mypy` type-checking (the `costhive` package is type-clean).

### Changed
- Pinned all dependencies to current latest: typer 0.26.8, rich 15.0.0,
  boto3 1.43.38, jinja2 3.1.6, pyyaml 6.0.3, weasyprint 69.0; dev: pytest 9.1.1,
  pytest-cov 7.1.0, ruff 0.15.20, pip-audit 2.10.1, mypy 2.1.0.
- Pinned bundled tools: Steampipe 2.4.4, Cloud Custodian 0.9.51, Infracost 0.10.44
  (documented pins for CloudQuery 6.38.0, Komiser 3.1.22, OpenCost 1.120.4).

[Unreleased]: https://github.com/d2k-klin/costhive/compare/v0.0.3...HEAD
[0.0.3]: https://github.com/d2k-klin/costhive/compare/v0.0.2...v0.0.3
[0.0.2]: https://github.com/d2k-klin/costhive/compare/v0.0.1...v0.0.2
[0.0.1]: https://github.com/d2k-klin/costhive/releases/tag/v0.0.1
