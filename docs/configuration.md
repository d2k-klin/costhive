# Configuration

CostHive is configured entirely through CLI flags and a few environment variables —
there is no config file in v1. For the complete flag list, see the generated
reference in [usage.md](usage.md#command--flag-reference).

## Environment variables

### AWS (standard)

| Variable | Purpose |
|----------|---------|
| `AWS_PROFILE` | Default profile (equivalent to `--profile`). |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` / `AWS_SESSION_TOKEN` | Static credentials (env only — never flags). |
| `AWS_DEFAULT_REGION` | Fallback region when `--regions` is omitted. |

### CostHive tool inputs

| Variable | Equivalent flag | Purpose |
|----------|-----------------|---------|
| `COSTHIVE_POLICY_DIR` | `--policy-dir` | Cloud Custodian policy directory. |
| `COSTHIVE_KOMISER_EXPORT` | `--komiser-export` | Komiser resources JSON export. |
| `COSTHIVE_CLOUDQUERY_DB_URL` | `--cloudquery-db-url` | Postgres URL enabling CloudQuery mode. |
| `COSTHIVE_CLOUDQUERY_SPEC` | `--cloudquery-spec` | CloudQuery sync spec file. |
| `COSTHIVE_IAC_PATH` | `estimate --path` | IaC directory for the `estimate` verb. |
| `INFRACOST_API_KEY` | — | Optional Infracost cloud-pricing key. |

A flag always overrides the matching environment variable.

## docker-compose

`docker-compose.yml` wires the common setup: mounts `~/.aws` read-only, mounts
`./reports` for output, mounts `$COSTHIVE_IAC` at `/iac` for `estimate`, and passes
the AWS env vars through. Copy [../examples/configs/costhive.env.example](../examples/configs/costhive.env.example)
to `.env` and adjust.

## Defaults worth knowing

| Setting | Default |
|---------|---------|
| Tools (`scan`) | `steampipe,custodian` |
| Formats | `html,md,json` |
| Output directory | `./reports` |
| PDF engine | `weasyprint` |
| Region | session region → `AWS_DEFAULT_REGION` → `us-east-1` |
