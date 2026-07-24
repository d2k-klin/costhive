# Security Policy

## Reporting a vulnerability

Please report security issues privately via the repository's security advisory
feature rather than a public issue. We aim to acknowledge within 72 hours.

## Supported versions

CostHive is pre-1.0. Security fixes are applied to the **latest released version**
only. Pin a version and upgrade to receive fixes.

| Version | Supported |
|---------|-----------|
| latest `0.x` | ✅ |
| older `0.x` | ❌ |

## Design guarantees

- **Read-only.** The shipped IAM policy grants no write/delete actions.
- **Cloud Custodian runs `--dryrun`.** CostHive never modifies an account in v1.
- **Reports stay local.** CostHive does not upload generated reports, and PDF
  rendering is local. Connected tools may call AWS, Infracost, Prometheus, or
  other endpoints the user explicitly configures.
- **Credentials** are resolved via standard AWS mechanisms (profile / env / STS
  assume-role) and never logged or written to reports.
