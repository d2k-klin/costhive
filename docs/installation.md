# Installation

CostHive runs on Linux, macOS, and Windows (WSL2). Python 3.10+ for the from-source
path.

## Docker (recommended)

The Docker image bundles the FinOps tool CLIs (Steampipe, Cloud Custodian,
Infracost), so you install nothing else.

```bash
git clone https://github.com/d2k-klin/costhive
cd costhive
docker compose build
docker compose run --rm costhive --version
```

Or run the CLI directly:

```bash
docker build -t costhive .
docker run --rm -v "$HOME/.aws:/root/.aws:ro" -v "$PWD/reports:/app/reports" \
  costhive scan --profile my-profile --yes
```

## From source (contributors / the code-cautious)

```bash
git clone https://github.com/d2k-klin/costhive
cd costhive
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
costhive --version
```

You then install whichever tool CLIs you want on `PATH` — any tool that isn't
found is cleanly reported as **skipped**:

- [Steampipe](https://steampipe.io/downloads) + the `aws` plugin (`steampipe plugin install aws`)
- [Cloud Custodian](https://cloudcustodian.io/docs/quickstart/index.html) (`pip install c7n`)
- [Infracost](https://www.infracost.io/docs/#quick-start) (for `estimate`)

## PyPI

```bash
pip install costhive        # when published
```

The PyPI package is the orchestrator only; install tool CLIs separately or use Docker.

## PDF output

PDF is optional and needs system libraries (pango/cairo), which the Docker image
already includes. For a source install:

```bash
pip install "costhive[pdf]"     # plus system libs; see reports.md
```

## Verify

```bash
costhive --version
costhive tools        # lists the bundled tools and their roles
```
