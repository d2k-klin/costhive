"""AWS credential resolution and identity verification.

Supports, in priority order (see project plan §5):
  1. AWS profile      -> --profile
  2. Static keys      -> env AWS_ACCESS_KEY_ID / SECRET / SESSION_TOKEN
  3. Assume role      -> --role-arn (+ optional --external-id), cross-account

Always calls sts:GetCallerIdentity first so the user sees exactly which account is
about to be analyzed.

Cost note: unlike a pure security scan, cost analysis benefits from Cost Explorer
(`ce:*` read) and Compute Optimizer data. `preflight_cost_access` probes whether
those are enabled so the tools can degrade gracefully and tell the user what to turn
on (see docs/prerequisites.md).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

import boto3
from botocore.exceptions import BotoCoreError, ClientError


class AuthError(Exception):
    """Raised when credentials cannot be resolved or verified."""


@dataclass
class Identity:
    account_id: str
    arn: str
    user_id: str


@dataclass
class CostDataAccess:
    """What billing/cost data sources are actually reachable for this identity."""

    cost_explorer: bool = False
    compute_optimizer: bool = False
    notes: list[str] = field(default_factory=list)


@dataclass
class AwsContext:
    """A resolved, verified AWS session plus the identity behind it."""

    session: boto3.Session
    identity: Identity
    regions: list[str]

    def client(self, service: str, region: str | None = None):
        return self.session.client(service, region_name=region)


def resolve_session(
    profile: str | None = None,
    role_arn: str | None = None,
    external_id: str | None = None,
    region: str | None = None,
    role_session_name: str = "costhive",
) -> boto3.Session:
    """Build a boto3 Session from the chosen auth strategy.

    A profile (or ambient env keys) establishes the base session. If a role ARN is
    given, that base session is used to assume the role and a new session is built
    from the temporary credentials.
    """
    base = boto3.Session(profile_name=profile, region_name=region)

    if not role_arn:
        return base

    try:
        sts = base.client("sts")
        params: dict = {"RoleArn": role_arn, "RoleSessionName": role_session_name}
        if external_id:
            params["ExternalId"] = external_id
        resp = sts.assume_role(**params)
    except (ClientError, BotoCoreError) as exc:
        raise AuthError(f"Failed to assume role {role_arn}: {exc}") from exc

    creds = resp["Credentials"]
    return boto3.Session(
        aws_access_key_id=creds["AccessKeyId"],
        aws_secret_access_key=creds["SecretAccessKey"],
        aws_session_token=creds["SessionToken"],
        region_name=region,
    )


def verify_identity(session: boto3.Session) -> Identity:
    """Call sts:GetCallerIdentity; raise AuthError with a clear message on failure."""
    try:
        resp = session.client("sts").get_caller_identity()
    except (ClientError, BotoCoreError) as exc:
        raise AuthError(
            "Could not verify AWS credentials via sts:GetCallerIdentity. "
            f"Check your profile/keys/role. Underlying error: {exc}"
        ) from exc
    return Identity(
        account_id=resp["Account"],
        arn=resp["Arn"],
        user_id=resp["UserId"],
    )


def default_regions(session: boto3.Session) -> list[str]:
    """Region the session resolved to, falling back to us-east-1."""
    region = session.region_name or os.environ.get("AWS_DEFAULT_REGION") or "us-east-1"
    return [region]


def build_context(
    profile: str | None = None,
    role_arn: str | None = None,
    external_id: str | None = None,
    regions: list[str] | None = None,
) -> AwsContext:
    """One-stop: resolve credentials, verify identity, settle on regions."""
    primary = regions[0] if regions else None
    session = resolve_session(
        profile=profile,
        role_arn=role_arn,
        external_id=external_id,
        region=primary,
    )
    identity = verify_identity(session)
    resolved_regions = regions or default_regions(session)
    return AwsContext(session=session, identity=identity, regions=resolved_regions)


def build_contexts(
    profile: str | None = None,
    role_arns: list[str] | None = None,
    external_id: str | None = None,
    regions: list[str] | None = None,
) -> list[AwsContext]:
    """Resolve one AwsContext per target account.

    Consultants analyze several client accounts in one run by passing multiple role
    ARNs. With no role ARN, this yields a single context from the profile/env keys.
    """
    if not role_arns:
        return [build_context(profile=profile, external_id=external_id, regions=regions)]
    return [build_context(profile=profile, role_arn=arn, external_id=external_id, regions=regions) for arn in role_arns]


def preflight_cost_access(ctx: AwsContext) -> CostDataAccess:
    """Best-effort probe of Cost Explorer / Compute Optimizer availability.

    Cost Explorer must be explicitly enabled on an account before the CE API returns
    data, and Compute Optimizer must be opted-in. Rather than let a tool fail
    opaquely, we check up front and surface a clear "enable this" note. All failures
    degrade to False rather than raising — a cost scan is still useful without them.
    """
    access = CostDataAccess()
    # Cost Explorer is a global endpoint served from us-east-1.
    try:
        ce = ctx.client("ce", region="us-east-1")
        ce.get_cost_categories(
            SearchString="",
            TimePeriod={"Start": "2020-01-01", "End": "2020-01-02"},
            MaxResults=1,
        )
        access.cost_explorer = True
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        if code in ("AccessDeniedException", "UnauthorizedException", "AccessDenied"):
            access.notes.append("Cost Explorer: access denied — grant ce:Get*/ce:Describe* to this identity.")
        elif code == "DataUnavailableException":
            access.notes.append("Cost Explorer: not enabled — enable it in Billing console (data takes ~24h).")
            access.cost_explorer = True  # enabled path exists; data just not ready
        else:
            # Some CE errors (e.g. validation on the probe range) still mean access works.
            access.cost_explorer = True
    except BotoCoreError:
        access.notes.append("Cost Explorer: could not be reached.")

    try:
        co = ctx.client("compute-optimizer", region=ctx.regions[0] if ctx.regions else "us-east-1")
        status = co.get_enrollment_status()
        if status.get("status") == "Active":
            access.compute_optimizer = True
        else:
            access.notes.append("Compute Optimizer: not opted-in — enable it for rightsizing recommendations.")
    except (ClientError, BotoCoreError):
        access.notes.append("Compute Optimizer: access denied or unavailable.")

    return access


def discover_eks_clusters(ctx: AwsContext) -> list[str]:
    """List EKS cluster names across the context's regions (best-effort).

    Used to auto-detect whether OpenCost (Kubernetes cost allocation) is applicable.
    Failures (no EKS perms, no clusters) return an empty list rather than raising.
    """
    clusters: list[str] = []
    for region in ctx.regions:
        try:
            paginator = ctx.client("eks", region=region).get_paginator("list_clusters")
            for page in paginator.paginate():
                clusters.extend(page.get("clusters", []))
        except (ClientError, BotoCoreError):
            continue
    return sorted(set(clusters))
