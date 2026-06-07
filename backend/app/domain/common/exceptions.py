class DomainError(RuntimeError):
    """Base exception for domain and application level errors."""


class TemplateNotFoundError(DomainError):
    """Raised when a named template cannot be found."""


class TemplateValidationError(DomainError):
    """Raised when a template payload is invalid."""


class ClearMLAdapterError(DomainError):
    """Raised when ClearML adapter operations cannot be completed."""
