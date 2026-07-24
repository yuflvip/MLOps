class DomainError(RuntimeError):
    """Base exception for domain and application level errors."""


class TemplateNotFoundError(DomainError):
    """Raised when a named template cannot be found."""


class TemplateValidationError(DomainError):
    """Raised when a template payload is invalid."""


class ClearMLAdapterError(DomainError):
    """Raised when ClearML adapter operations cannot be completed."""


class DatasetNotFoundError(DomainError):
    """Raised when a dataset record cannot be found."""


class DatasetConflictError(DomainError):
    """Raised when a dataset name or path conflicts with an existing record."""


class DatasetValidationError(DomainError):
    """Raised when a dataset payload is invalid."""


class QuantizationDatasetNotFoundError(DomainError):
    """Raised when a quantization dataset record cannot be found."""


class QuantizationDatasetConflictError(DomainError):
    """Raised when a quantization dataset conflicts with an existing record."""


class QuantizationDatasetValidationError(DomainError):
    """Raised when quantization dataset input is invalid."""


class ProjectNotFoundError(DomainError):
    """Raised when a project record cannot be found."""


class ProjectConflictError(DomainError):
    """Raised when a project key conflicts with an existing record."""


class ProjectValidationError(DomainError):
    """Raised when a project payload is invalid."""


class ExpNotFoundError(DomainError):
    """Raised when an experiment record cannot be found."""


class ExpConflictError(DomainError):
    """Raised when an experiment path or version already exists."""


class ExpValidationError(DomainError):
    """Raised when an experiment operation is invalid."""


class RuntimeEnvironmentNotFoundError(DomainError):
    """Raised when a runtime environment record cannot be found."""


class RuntimeEnvironmentConflictError(DomainError):
    """Raised when a runtime environment key conflicts with an existing record."""


class RuntimeEnvironmentValidationError(DomainError):
    """Raised when a runtime environment payload is invalid."""
