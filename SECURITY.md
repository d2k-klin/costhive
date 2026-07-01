# Security Policy

## Reporting a vulnerability

Please report security issues privately via the repository's security advisory
feature rather than a public issue. We aim to acknowledge within 72 hours.

## Design guarantees

- **Read-only.** The shipped IAM policy grants no write/delete actions.
- **Cloud Custodian runs `--dryrun`.** CostHive never modifies an account in v1.
- **No data exfiltration.** All analysis and report generation runs locally; no
  scan data is sent anywhere. PDF rendering is local (WeasyPrint/Chromium).
- **Credentials** are resolved via standard AWS mechanisms (profile / env / STS
  assume-role) and never logged or written to reports.
