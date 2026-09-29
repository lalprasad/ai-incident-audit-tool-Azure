class AuditError(Exception):
    """Base error for expected audit failures."""


class InvalidDocumentError(AuditError):
    """The upload is not a readable PDF or contains no text."""


class NotFoundError(AuditError):
    """The job, audit, or ticket does not exist."""


class ConflictError(AuditError):
    """The job cannot be processed in its current state."""


class ScoringError(AuditError):
    """A score is outside the configured range or the totals cannot be computed."""


class InvalidModelOutput(AuditError):
    """The model JSON failed schema validation. Do not retry forever."""


class TransientError(AuditError):
    """A remote call failed in a way that may succeed if retried."""


class ConfigurationError(AuditError):
    """Live Azure mode is missing required settings."""
