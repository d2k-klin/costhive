"""CostHive — AWS cost-optimization toolkit.

Orchestrates best-in-class open-source FinOps tools and produces one consolidated,
dollar-ranked report of savings opportunities.
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("costhive")
except PackageNotFoundError:
    __version__ = "0+unknown"
