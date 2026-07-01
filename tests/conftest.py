"""Shared pytest configuration for CostHive tests."""


def pytest_addoption(parser):
    parser.addoption(
        "--update-golden",
        action="store_true",
        default=False,
        help="Update golden files instead of comparing.",
    )
