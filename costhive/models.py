"""Unified savings schema — the common shape every tool normalizes into.

This is the heart of CostHive: no matter which FinOps tool produced an opportunity,
it is represented here identically so the aggregator and report layer never need to
know which tool it came from. Findings are ranked by **estimated monthly savings** —
"$X/mo saved by doing Y" is the entire value proposition.
"""

from __future__ import annotations

import dataclasses
import enum
import hashlib
from dataclasses import dataclass


class Confidence(enum.IntEnum):
    """How sure we are about a savings estimate. Higher == more trustworthy.

    Ordered so findings can break ties by confidence and so we can avoid
    overpromising: a HIGH-confidence $50/mo win beats a LOW-confidence $500 guess
    when identifying quick wins.
    """

    LOW = 0
    MEDIUM = 1
    HIGH = 2

    @property
    def label(self) -> str:
        return self.name.capitalize()

    @classmethod
    def parse(cls, value: str | int | None) -> Confidence:
        if value is None:
            return cls.MEDIUM
        if isinstance(value, int) and not isinstance(value, bool):
            return cls(max(0, min(2, value)))
        key = str(value).strip().lower()
        mapping = {
            "high": cls.HIGH,
            "certain": cls.HIGH,
            "confirmed": cls.HIGH,
            "medium": cls.MEDIUM,
            "med": cls.MEDIUM,
            "moderate": cls.MEDIUM,
            "low": cls.LOW,
            "estimate": cls.LOW,
            "estimated": cls.LOW,
            "guess": cls.LOW,
        }
        return mapping.get(key, cls.MEDIUM)


class Category(str, enum.Enum):
    """Savings categories — the axis the exec summary breaks spend down by.

    Every finding lands in exactly one bucket so the report can answer "how much is
    idle compute vs. unused storage vs. rightsizing?" at a glance.
    """

    IDLE = "idle"  # running but doing nothing (stopped-worthy instances, idle RDS)
    RIGHTSIZING = "rightsizing"  # oversized for its actual utilization
    UNUSED = "unused"  # unattached/orphaned (EBS volumes, EIPs, old snapshots, idle NAT)
    UNTAGGED = "untagged"  # governance: no cost allocation tags (savings often $0)
    COMMITMENT = "commitment"  # Savings Plans / Reserved Instance coverage gaps
    STORAGE_CLASS = "storage_class"  # S3/EBS on a pricier tier than needed
    OFF_HOURS = "off_hours"  # non-prod that could be stopped nights/weekends
    NETWORK = "network"  # data-transfer / NAT / cross-AZ waste
    OTHER = "other"

    @property
    def label(self) -> str:
        return {
            "idle": "Idle resources",
            "rightsizing": "Rightsizing",
            "unused": "Unused / orphaned",
            "untagged": "Untagged (governance)",
            "commitment": "Commitment coverage",
            "storage_class": "Storage class",
            "off_hours": "Off-hours scheduling",
            "network": "Network / transfer",
            "other": "Other",
        }[self.value]

    @classmethod
    def parse(cls, value: str | None) -> Category:
        """Best-effort mapping from the many vocabularies tools emit."""
        if not value:
            return cls.OTHER
        key = str(value).strip().lower().replace("-", "_").replace(" ", "_")
        direct = {c.value: c for c in cls}
        if key in direct:
            return direct[key]
        # Keyword heuristics over tool-specific policy/check names.
        table: list[tuple[tuple[str, ...], Category]] = [
            (
                ("rightsiz", "right_siz", "oversized", "over_provision", "downsize", "low_util", "underutil"),
                cls.RIGHTSIZING,
            ),
            (("idle", "stopped", "unused_capacity"), cls.IDLE),
            (("unused", "unattached", "orphan", "available", "unassociated", "detached"), cls.UNUSED),
            (("untagged", "missing_tag", "no_tag", "tagging"), cls.UNTAGGED),
            (("commitment", "savings_plan", "savingsplan", "reserved", "ri_", "reservation"), cls.COMMITMENT),
            (("storage_class", "storage-class", "gp2", "infrequent", "glacier", "tier"), cls.STORAGE_CLASS),
            (("off_hours", "off-hours", "schedule", "nights", "weekend"), cls.OFF_HOURS),
            (("nat", "transfer", "egress", "cross_az", "cross-az", "network"), cls.NETWORK),
        ]
        for needles, cat in table:
            if any(n in key for n in needles):
                return cat
        return cls.OTHER


@dataclass
class SavingsFinding:
    """A single normalized cost-savings opportunity.

    Mirrors the schema in the project plan (id, tool, category, resource,
    estimated_monthly_savings, confidence, description, recommended_action) plus a
    few fields needed for a useful report (service, region, account_id, currency).
    """

    tool: str
    category: Category
    title: str
    description: str
    estimated_monthly_savings: float = 0.0
    confidence: Confidence = Confidence.MEDIUM
    resource: str = ""
    service: str = ""
    region: str = ""
    currency: str = "USD"
    recommended_action: str = ""
    account_id: str = ""
    id: str = ""  # stable fingerprint, computed in __post_init__ if empty

    def __post_init__(self) -> None:
        if not isinstance(self.category, Category):
            self.category = Category.parse(self.category)
        if isinstance(self.confidence, (str, int)) and not isinstance(self.confidence, Confidence):
            self.confidence = Confidence.parse(self.confidence)
        try:
            self.estimated_monthly_savings = round(max(0.0, float(self.estimated_monthly_savings)), 2)
        except (TypeError, ValueError):
            self.estimated_monthly_savings = 0.0
        if not self.id:
            self.id = self.fingerprint()

    def fingerprint(self) -> str:
        """Stable id: tool + category + resource."""
        raw = f"{self.tool}|{self.category.value}|{self.resource}".lower()
        return hashlib.sha1(raw.encode()).hexdigest()[:12]

    @property
    def dedup_key(self) -> str:
        """Cross-tool dedup key: same resource + category from different tools collapse."""
        return f"{self.service}|{self.resource}|{self.category.value}".lower()

    @property
    def annual_savings(self) -> float:
        return round(self.estimated_monthly_savings * 12, 2)

    def to_dict(self) -> dict:
        d = dataclasses.asdict(self)
        d["category"] = self.category.value
        d["category_label"] = self.category.label
        d["confidence"] = self.confidence.label
        d["annual_savings"] = self.annual_savings
        return d
