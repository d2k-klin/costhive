# Changelog

All notable changes to CostHive are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> **Savings-impacting changes** (bundled-tool version bumps, changes to
> savings-estimation logic) are called out explicitly — they change the dollar
> numbers you report to clients.

## [Unreleased]

## [0.0.7] - 2026-08-14

### Changed
- **Savings-impacting tool updates:** Steampipe 2.4.4 → 2.4.5, Steampipe
  AWS plugin 1.31.0 → 1.32.0, Infracost 2.12.2 → 2.16.1, CloudQuery CLI
  6.41.0 → 6.41.1, and OpenCost 1.121.0 → 1.121.1. The upstream notes do
  not change CostHive's wrapper flags or parsed output contracts.
- **Current Python toolchain:** raised Hatchling to 1.32.0, Typer to 0.27.1,
  boto3 to 1.43.71, and Ruff to 0.16.3.
- **Current workflow tooling:** upgraded AWS CLI to 2.36.23, CodeQL to
  4.37.7, Docker login to 4.6.0, and regenerated agentic workflows with
  gh-aw 0.86.2.

## [0.0.6] - 2026-07-24

### Changed
- **Savings-impacting tool updates:** Infracost 0.10.44 → 2.12.2,
  CloudQuery CLI 6.38.0 → 6.41.0, OpenCost 1.120.4 → 1.121.0, and the newly
  pinned Steampipe AWS plugin at 1.31.0. No affected wrapper flags or parsed
  output schemas changed outside the Infracost v2 migration described below.
- **Current Python toolchain:** raised compatible dependency floors (Typer,
  boto3, Ruff, mypy, types-PyYAML, Hatchling), added `build` to the tracked dev
  toolset, and moved the Docker/CI default runtime to Python 3.14.
- **Current CI actions:** refreshed all authored workflow actions to their
  latest immutable SHAs and regenerated gh-aw workflows with gh-aw 0.83.1.
- **Pinned supporting CLIs:** AWS CLI 2.36.7 and Gitleaks 8.30.1 now share
  `tool-versions.env` with the FinOps tools.

### Added
- **Kubernetes workload rightsizing:** ingest Robusta KRR 1.29.0 JSON exports
  through `--krr-export`, preserving exact CPU/memory request changes alongside
  OpenCost's dollar estimates in the single consolidated report.
- **Prerequisite visibility:** `costhive prerequisites` documents the AWS role,
  billing-service, Kubernetes, Prometheus, database, export, and API-key inputs;
  scans now auto-detect EKS and report when Kubernetes inputs are missing.
- **Weekly tool-version watch:** `.github/workflows/tool-version-watch.md` (a
  [gh-aw](https://github.github.com/gh-aw/) agentic workflow, Copilot engine)
  checks all pinned tools' upstream releases on a schedule, bumps
  `tool-versions.env`/`Dockerfile` pins, patches wrapper code for breaking
  changes, validates, and opens a PR — covers what Dependabot can't see
  (release-tag pins, not manifest deps).
- **Full supported-Python CI:** tests now run on every supported minor,
  Python 3.10 through 3.14.

### Fixed
- **Report ownership and privacy wording:** every output is branded
  “CostHive by Mr.D,” and the report accurately distinguishes locally generated
  artifacts from external services called by configured tools.
- **Infracost v2 migration:** follow the active `infracost/cli` release line
  instead of the retired v0 repository, switch `estimate` to `scan --json`,
  and parse the v2 resource/cost-component schema while retaining support for
  v0.10 JSON exports.
- **Reliable Steampipe image:** pin the AWS plugin and fail the Docker build if
  its installation fails instead of silently shipping an incomplete image.
- **Tool dependency isolation:** CI now mirrors Docker's separate Custodian
  virtual environment, so Custodian's strict boto3 pin cannot constrain
  CostHive's current boto3 release.
- **Single package version source:** the CLI and reports now read the installed
  package metadata instead of retaining a stale duplicated version constant.
- **Honest AWS prerequisites:** removed unused Cost Explorer/Compute Optimizer
  probes and permissions; v0.0.6 no longer implies those unimplemented imports
  can affect findings, and empty reports state their limited coverage.

## [0.0.5] - 2026-07-02

### Fixed
- **CI Steampipe install:** run the Steampipe install script with `sudo` so it can
  write to `/usr/local/bin` on the GitHub Actions runner.
- **Golden report test:** updated fixture to match current package version.

## [0.0.4] - 2026-07-02

### Fixed
- **boto3 dependency conflict:** lowered `boto3>=1.43.38` to `boto3>=1.43.3` so pip
  can resolve against Cloud Custodian 0.9.51's pinned `boto3==1.43.3`.

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

[Unreleased]: https://github.com/d2k-klin/costhive/compare/v0.0.7...HEAD
[0.0.7]: https://github.com/d2k-klin/costhive/compare/v0.0.6...v0.0.7
[0.0.6]: https://github.com/d2k-klin/costhive/compare/v0.0.5...v0.0.6
[0.0.5]: https://github.com/d2k-klin/costhive/compare/v0.0.4...v0.0.5
[0.0.4]: https://github.com/d2k-klin/costhive/compare/v0.0.3...v0.0.4
[0.0.3]: https://github.com/d2k-klin/costhive/compare/v0.0.2...v0.0.3
[0.0.2]: https://github.com/d2k-klin/costhive/compare/v0.0.1...v0.0.2
[0.0.1]: https://github.com/d2k-klin/costhive/releases/tag/v0.0.1
