from enum import Enum, auto

class Permission(str, Enum):
    """
    Enum defining all available permissions in the system.
    Using string enum for easy serialization and database storage.
    """
    # Admin permissions
    MANAGE_USERS = "manage_users"
    MANAGE_ROLES = "manage_roles"
    VIEW_METRICS = "view_metrics"
    
    # Gateway permissions
    USE_OLLAMA = "use_ollama"
    USE_OPENAI = "use_openai"
    MANAGE_MODELS = "manage_models"
    
    # Rate limit permissions
    PREMIUM_RATE_LIMITS = "premium_rate_limits"
    BASIC_RATE_LIMITS = "basic_rate_limits"

    def __str__(self) -> str:
        return self.value

class DefaultRoles:
    """
    Defines the default roles and their associated permissions.
    """
    ADMIN = {
        "name": "admin",
        "permissions": [
            Permission.MANAGE_USERS,
            Permission.MANAGE_ROLES,
            Permission.VIEW_METRICS,
            Permission.USE_OLLAMA,
            Permission.USE_OPENAI,
            Permission.MANAGE_MODELS,
            Permission.PREMIUM_RATE_LIMITS
        ]
    }
    
    PREMIUM = {
        "name": "premium",
        "permissions": [
            Permission.USE_OLLAMA,
            Permission.USE_OPENAI,
            Permission.PREMIUM_RATE_LIMITS
        ]
    }
    
    BASIC = {
        "name": "basic",
        "permissions": [
            Permission.USE_OLLAMA,
            Permission.BASIC_RATE_LIMITS
        ]
    }

    @classmethod
    def get_all_roles(cls) -> dict:
        """Returns all default roles and their permissions."""
        return {
            "admin": cls.ADMIN,
            "premium": cls.PREMIUM,
            "basic": cls.BASIC
        }
