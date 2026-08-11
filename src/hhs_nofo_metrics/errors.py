"""Typed package errors used by the API and CLI."""


class NofoMetricsError(Exception):
    """Base error for expected package failures."""

    code = "nofo_metrics_error"

    def to_dict(self) -> dict[str, str]:
        """Return the stable machine-readable error envelope."""

        return {"code": self.code, "message": str(self)}


class DependencyError(NofoMetricsError):
    """A required runtime dependency is unavailable."""

    code = "dependency_error"


class InputError(NofoMetricsError):
    """The source cannot be read or is unsupported."""

    code = "input_error"


class ProfileError(NofoMetricsError):
    """A profile reference or profile document is invalid."""

    code = "profile_error"


class AnalysisError(NofoMetricsError):
    """The source was readable but analysis could not complete."""

    code = "analysis_error"


class AdapterError(NofoMetricsError):
    """An adapter could not be selected or executed."""

    code = "adapter_error"


class AdapterNotFoundError(AdapterError):
    """The requested adapter is not installed."""

    code = "adapter_not_found"


class AdapterContractError(AdapterError):
    """An adapter or its output violates the plugin contract."""

    code = "adapter_contract_error"


class AdapterExecutionError(AdapterError):
    """An adapter failed unexpectedly while inspecting or extracting."""

    code = "adapter_execution_error"
