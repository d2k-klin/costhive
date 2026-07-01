# CostHive — single image bundling the FinOps tools so users install nothing but Docker.
FROM python:3.12-slim

LABEL org.opencontainers.image.title="CostHive" \
      org.opencontainers.image.description="AWS cost-optimization toolkit — one image, one money-first report." \
      org.opencontainers.image.licenses="Apache-2.0" \
      org.opencontainers.image.source="https://github.com/d2k-klin/costhive"

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PATH="/opt/costhive-venv/bin:/opt/tool-venv/bin:/usr/local/steampipe:$PATH"

# System deps:
#  - git: IaC checkout for Infracost
#  - curl/unzip/tar: install AWS CLI, Steampipe, Infracost
#  - libpango/cairo/gdk-pixbuf + fonts: WeasyPrint PDF rendering (kept local, no network)
RUN apt-get update && apt-get install -y --no-install-recommends \
        git curl unzip tar ca-certificates postgresql-client \
        libpango-1.0-0 libpangocairo-1.0-0 libcairo2 libgdk-pixbuf-2.0-0 libffi-dev \
        fonts-dejavu fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# AWS CLI v2 (used by tools that resolve credentials / kubeconfig).
RUN ARCH="$(uname -m)" \
    && curl -sSL "https://awscli.amazonaws.com/awscli-exe-linux-${ARCH}.zip" -o /tmp/awscliv2.zip \
    && unzip -q /tmp/awscliv2.zip -d /tmp \
    && /tmp/aws/install \
    && rm -rf /tmp/aws /tmp/awscliv2.zip

# Pinned tool versions come from the single source of truth (tool-versions.env),
# overridable at build time with --build-arg. Keep the defaults in sync with that file.
ARG STEAMPIPE_VERSION=2.4.4
ARG CUSTODIAN_VERSION=0.9.51
ARG INFRACOST_VERSION=0.10.44

# Steampipe + AWS plugin (live SQL cost queries), pinned.
RUN useradd -m steampipe \
    && curl -sSL https://steampipe.io/install/steampipe.sh | STEAMPIPE_VERSION="v${STEAMPIPE_VERSION}" sh \
    && su steampipe -c "steampipe plugin install aws" || true

# Infracost (pre-deploy IaC cost estimate), pinned.
RUN curl -sSL "https://raw.githubusercontent.com/infracost/infracost/master/scripts/install.sh" \
      | INFRACOST_VERSION="${INFRACOST_VERSION}" sh

# Isolate tool CLIs from CostHive's app dependencies (several pin older boto3/typer).
RUN python -m venv /opt/tool-venv \
    && /opt/tool-venv/bin/pip install --upgrade pip "setuptools<81" \
    && /opt/tool-venv/bin/pip install "c7n==${CUSTODIAN_VERSION}"        # Cloud Custodian

RUN python -m venv /opt/costhive-venv \
    && /opt/costhive-venv/bin/pip install --upgrade pip

WORKDIR /app
COPY pyproject.toml README.md ./
COPY costhive ./costhive
COPY policies ./policies
RUN /opt/costhive-venv/bin/pip install ".[pdf]"

# Make the Custodian CLI reachable from the app venv's PATH lookups.
ENV PATH="/opt/tool-venv/bin:$PATH"

# Reports land here; mount a host volume over it (see docker-compose.yml).
VOLUME ["/app/reports"]

ENTRYPOINT ["costhive"]
CMD ["--help"]
