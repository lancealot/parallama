"""Core exceptions for the application."""

class ParallamaError(Exception):
    """Base class for all application errors."""
    pass

class DatabaseError(ParallamaError):
    """Database-related errors."""
    pass

class AuthenticationError(ParallamaError):
    """Authentication-related errors."""
    pass

class AuthorizationError(ParallamaError):
    """Authorization-related errors."""
    pass

class RateLimitError(ParallamaError):
    """Rate limit-related errors."""
    pass

class GatewayError(ParallamaError):
    """Gateway-related errors."""
    pass

class ConfigurationError(ParallamaError):
    """Configuration-related errors."""
    pass

class ValidationError(ParallamaError):
    """Validation-related errors."""
    pass

class ServiceError(ParallamaError):
    """Service-related errors."""
    pass

class NotFoundError(ParallamaError):
    """Resource not found errors."""
    pass

class ResourceNotFoundError(NotFoundError):
    """Specific resource not found errors."""
    pass

class DuplicateError(ParallamaError):
    """Duplicate resource errors."""
    pass

class DuplicateResourceError(DuplicateError):
    """Specific duplicate resource errors."""
    pass

class ConnectionError(ParallamaError):
    """Connection-related errors."""
    pass

class TimeoutError(ParallamaError):
    """Timeout-related errors."""
    pass

class LLMServiceError(ParallamaError):
    """LLM service-related errors."""
    pass

class CLIError(ParallamaError):
    """CLI-related errors."""
    pass

__all__ = [
    'ParallamaError',
    'DatabaseError',
    'AuthenticationError',
    'AuthorizationError',
    'RateLimitError',
    'GatewayError',
    'ConfigurationError',
    'ValidationError',
    'ServiceError',
    'NotFoundError',
    'ResourceNotFoundError',
    'DuplicateError',
    'DuplicateResourceError',
    'ConnectionError',
    'TimeoutError',
    'LLMServiceError',
    'CLIError'
]
