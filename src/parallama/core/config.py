"""Configuration management."""

import os
from pathlib import Path
from typing import Dict, List, Optional

import yaml
from pydantic import BaseModel, Field


class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: str = "info"

class ServerConfig(BaseModel):
    """Server configuration."""

    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 4
    log_level: str = "info"


class DatabaseConfig(BaseModel):
    """Database configuration."""

    url: str


class RedisConfig(BaseModel):
    """Redis configuration."""

    url: str


class JWTConfig(BaseModel):
    """JWT configuration."""

    secret_file: str
    expiry: int = 3600


class AuthConfig(BaseModel):
    """Authentication configuration."""

    jwt: JWTConfig
    allowed_users: List[str] = Field(default_factory=list)
    admin_users: List[str] = Field(default_factory=list)


class GatewayConfig(BaseModel):
    """Gateway configuration."""

    url: str
    enabled: bool = True


class GatewaysConfig(BaseModel):
    """Gateways configuration."""

    ollama: Optional[GatewayConfig] = None
    openai: Optional[GatewayConfig] = None


class Settings(BaseModel):
    """Application settings."""

    server: ServerConfig
    database: DatabaseConfig
    redis: RedisConfig
    jwt: JWTConfig
    auth: AuthConfig
    gateways: GatewaysConfig
    logging: LoggingConfig = LoggingConfig()


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get application settings."""
    if _settings is None:
        raise RuntimeError("Settings not loaded")
    return _settings


def load_settings(config_path: Path) -> None:
    """Load settings from config file."""
    global _settings

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path) as f:
        config_data = yaml.safe_load(f)

    _settings = Settings.model_validate(config_data)


# Export functions for other modules to use
__all__ = ["get_settings", "load_settings", "Settings", "AuthConfig"]
