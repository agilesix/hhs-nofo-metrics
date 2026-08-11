"""Public API for HHS NOFO Metrics."""

from .api import (
    PdfSource,
    analyze,
    inspect_adapter_support,
    list_adapters,
    list_profiles,
    load_profile,
)
from .errors import (
    AdapterContractError,
    AdapterError,
    AdapterExecutionError,
    AdapterNotFoundError,
    AnalysisError,
    DependencyError,
    InputError,
    NofoMetricsError,
    ProfileError,
)
from .sources import HtmlSource, SourceArtifact, SourceBundle
from .version import PACKAGE_VERSION

__all__ = [
    "AnalysisError",
    "AdapterContractError",
    "AdapterError",
    "AdapterExecutionError",
    "AdapterNotFoundError",
    "DependencyError",
    "InputError",
    "HtmlSource",
    "NofoMetricsError",
    "PdfSource",
    "ProfileError",
    "SourceArtifact",
    "SourceBundle",
    "analyze",
    "inspect_adapter_support",
    "list_adapters",
    "list_profiles",
    "load_profile",
]
__version__ = PACKAGE_VERSION
