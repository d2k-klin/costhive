from costhive.models import Category, Confidence, SavingsFinding


def test_confidence_parse_and_order():
    assert Confidence.parse("high") is Confidence.HIGH
    assert Confidence.parse("estimated") is Confidence.LOW
    assert Confidence.parse(None) is Confidence.MEDIUM
    assert Confidence.parse(2) is Confidence.HIGH
    assert Confidence.HIGH > Confidence.LOW


def test_category_parse_direct_and_heuristic():
    assert Category.parse("idle") is Category.IDLE
    assert Category.parse("ebs-unattached") is Category.UNUSED
    assert Category.parse("gp2-to-gp3") is Category.STORAGE_CLASS
    assert Category.parse("ec2-low-utilization") is Category.RIGHTSIZING
    assert Category.parse("savings_plan_coverage") is Category.COMMITMENT
    assert Category.parse("mystery") is Category.OTHER
    assert Category.parse(None) is Category.OTHER


def test_category_label():
    assert Category.UNUSED.label == "Unused / orphaned"
    assert Category.OFF_HOURS.label == "Off-hours scheduling"


def test_finding_normalizes_types_and_fingerprint():
    f = SavingsFinding(
        tool="steampipe",
        category="unused",
        title="Unattached EBS volume",
        description="idle",
        estimated_monthly_savings="8.5",
        confidence="high",
        resource="vol-123",
        service="ebs",
    )
    assert f.category is Category.UNUSED
    assert f.confidence is Confidence.HIGH
    assert f.estimated_monthly_savings == 8.5
    assert f.id  # fingerprint computed
    assert f.annual_savings == 102.0


def test_finding_clamps_negative_and_bad_savings():
    assert SavingsFinding("t", Category.OTHER, "x", "y", estimated_monthly_savings=-5).estimated_monthly_savings == 0.0
    assert (
        SavingsFinding("t", Category.OTHER, "x", "y", estimated_monthly_savings="n/a").estimated_monthly_savings == 0.0
    )


def test_dedup_key_is_resource_plus_category():
    a = SavingsFinding("steampipe", Category.UNUSED, "t", "d", resource="vol-1", service="ebs")
    b = SavingsFinding("custodian", Category.UNUSED, "t", "d", resource="vol-1", service="ebs")
    assert a.dedup_key == b.dedup_key


def test_to_dict_has_labels_and_annual():
    d = SavingsFinding("steampipe", Category.IDLE, "t", "d", estimated_monthly_savings=10, confidence="low").to_dict()
    assert d["category"] == "idle"
    assert d["category_label"] == "Idle resources"
    assert d["confidence"] == "Low"
    assert d["annual_savings"] == 120.0
