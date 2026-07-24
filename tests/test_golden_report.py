"""Golden-file report test.

Renders a Markdown report from the fixed fixture set and compares it against a
committed 'expected' file. This catches accidental report **and savings-number**
regressions in one shot.

Update the golden after an intentional change:
    pytest tests/test_golden_report.py --update-golden
"""

import pathlib

from costhive.aggregate import build_report
from costhive.normalize import parse_custodian, parse_komiser, parse_steampipe
from costhive.report.generator import render_md
from costhive.tools.base import ToolResult, ToolStatus
from costhive.tools.krr import parse_krr
from costhive.tools.opencost import _parse_allocation

from .conftest import load_fixture

GOLDEN = pathlib.Path(__file__).parent / "fixtures" / "golden" / "report.expected.md"


def _fixed_report():
    """Deterministic report from the committed fixtures (pinned versions + timestamp)."""
    results = [
        ToolResult(
            "steampipe",
            ToolStatus.OK,
            version="Steampipe v2.4.4",
            message=(
                "5/5 checks ran; coverage: ebs unattached, eip unassociated, "
                "ebs gp2 to gp3, stopped instances with ebs, old snapshots"
            ),
            findings=parse_steampipe(load_fixture("steampipe_sample.json"), account_id="123456789012"),
        ),
        ToolResult(
            "custodian",
            ToolStatus.OK,
            version="custodian 0.9.51",
            message=(
                "6 policies across 2 file(s) evaluated (dry-run, no changes made); coverage: "
                "ebs unattached, eip unassociated, rds idle no connections, ec2 low utilization, "
                "ec2 untagged, gp2 volumes"
            ),
            findings=parse_custodian(load_fixture("custodian_sample.json"), account_id="123456789012"),
        ),
        ToolResult(
            "komiser",
            ToolStatus.OK,
            version="komiser 3.1.22",
            message="1 untagged cost-allocation gap(s)",
            findings=parse_komiser(load_fixture("komiser_sample.json"), account_id="123456789012"),
        ),
        ToolResult(
            "opencost",
            ToolStatus.OK,
            version="opencost 1.121.0",
            findings=_parse_allocation(load_fixture("opencost_sample.json"), cluster="prod-eks"),
        ),
        ToolResult(
            "krr",
            ToolStatus.OK,
            version="1.29.0",
            message="1 workload/container recommendation(s) imported",
            findings=parse_krr(load_fixture("krr_sample.json")),
        ),
    ]
    return build_report(
        results,
        account_id="123456789012",
        identity_arn="arn:aws:iam::123456789012:role/CostHiveAudit",
        regions=["us-east-1"],
        generated_at="2026-07-01 00:00:00 UTC",
        client_name="Acme Corp",
    )


def test_golden_markdown_report(request):
    rendered = render_md(_fixed_report())
    if request.config.getoption("--update-golden"):
        GOLDEN.parent.mkdir(parents=True, exist_ok=True)
        GOLDEN.write_text(rendered)
        return
    assert GOLDEN.exists(), "golden file missing — run: pytest --update-golden"
    assert rendered == GOLDEN.read_text()
