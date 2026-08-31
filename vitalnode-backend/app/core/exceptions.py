"""
Domain exceptions and structured error responses.
All HTTP error details flow through these classes.
"""
from typing import Any, Optional


class VitalNodeError(Exception):
    """Base application error."""
    def __init__(self, message: str, code: str = "INTERNAL_ERROR", details: Optional[dict] = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(message)


class AuthenticationError(VitalNodeError):
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, code="AUTHENTICATION_FAILED")


class AuthorizationError(VitalNodeError):
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(message, code="FORBIDDEN")


class NotFoundError(VitalNodeError):
    def __init__(self, resource: str, resource_id: Any = None):
        msg = f"{resource} not found"
        if resource_id:
            msg = f"{resource} '{resource_id}' not found"
        super().__init__(msg, code="NOT_FOUND", details={"resource": resource})


class ValidationError(VitalNodeError):
    def __init__(self, message: str, field: Optional[str] = None):
        details = {"field": field} if field else {}
        super().__init__(message, code="VALIDATION_ERROR", details=details)


class InvalidVitalError(VitalNodeError):
    def __init__(self, field: str, value: Any, reason: str):
        super().__init__(
            f"Invalid vital value for {field}: {reason}",
            code="INVALID_VITAL",
            details={"field": field, "value": str(value), "reason": reason},
        )


class ConflictError(VitalNodeError):
    def __init__(self, message: str):
        super().__init__(message, code="CONFLICT")


class MLUnavailableError(VitalNodeError):
    def __init__(self, reason: str = "ML engine is not available"):
        super().__init__(reason, code="ML_UNAVAILABLE")


class DemoModeError(VitalNodeError):
    def __init__(self):
        super().__init__(
            "This endpoint is only available in DEMO_MODE",
            code="DEMO_MODE_ONLY",
        )
