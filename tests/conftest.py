"""Shared pytest configuration for CostHive tests."""

import json
import pathlib

import pytest

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


def pytest_addoption(parser):
    parser.addoption(
        "--update-golden",
        action="store_true",
        default=False,
        help="Update golden files instead of comparing.",
    )


def load_fixture(name: str):
    """Load a sanitized sample tool-output fixture (see tests/fixtures/)."""
    with open(FIXTURES / name) as fh:
        return json.load(fh)


@pytest.fixture
def fixtures():
    """Dict of all bundled sample tool outputs, keyed by tool name."""
    return {
        "steampipe": load_fixture("steampipe_sample.json"),
        "custodian": load_fixture("custodian_sample.json"),
        "komiser": load_fixture("komiser_sample.json"),
        "infracost": load_fixture("infracost_sample.json"),
        "opencost": load_fixture("opencost_sample.json"),
    }
