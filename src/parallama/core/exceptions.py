"""Custom exceptions for the Parallama application."""

class ParallamaError(Exception):
    """Base class for all Parallama exceptions."""
    pass


class AuthenticationError(ParallamaError):
    """Base class for authentication-related errors."""
    pass


class TokenError(AuthenticationError):
    """Error raised for token-related issues."""
    pass


class ResourceError(ParallamaError):
    """Base class for resource-related errors."""
    pass


class ResourceNotFoundError(ResourceError):
    """Error raised when a requested resource is not found."""
    pass


class DuplicateResourceError(ResourceError):
    """Error raised when attempting to create a duplicate resource."""
    pass


class ValidationError(ParallamaError):
    """Error raised for validation failures."""
    pass


class RateLimitError(ParallamaError):
    """Error raised when rate limits are exceeded."""
    pass


class ConfigurationError(ParallamaError):
    """Error raised for configuration-related issues."""
    pass


class GatewayError(ParallamaError):
    """Base class for gateway-related errors."""
    pass


class GatewayNotFoundError(GatewayError):
    """Error raised when a requested gateway is not found."""
    pass


class GatewayConfigurationError(GatewayError):
    """Error raised for gateway configuration issues."""
    pass


class ModelError(ParallamaError):
    """Base class for model-related errors."""
    pass


class ModelNotFoundError(ModelError):
    """Error raised when a requested model is not found."""
    pass


class ModelConfigurationError(ModelError):
    """Error raised for model configuration issues."""
    pass
