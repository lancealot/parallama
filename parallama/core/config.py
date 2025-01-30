"""Configuration management for Parallama."""

import os
from datetime import timedelta
from typing import Optional

import yaml
from pathlib import Path
from pydantic import BaseModel, Field


class AuthConfig(BaseModel):
    """Authentication configuration settings."""
    jwt_secret_key_file: str = Field(default="/etc/parallama/jwt_secret")
    access_token_expire_minutes: int = Field(default=30)
    refresh_token_expire_days: int = Field(default=30)
    password_hash_rounds: int = Field(default=12)

    @property
    def jwt_secret_key(self) -> str:
        """Read JWT secret key from file."""
        try:
            return Path(self.jwt_secret_key_file).read_text().strip()
        except FileNotFoundError:
            # For development/testing, return a default key
            return "development_secret_key_do_not_use_in_production"
    
    @property
    def access_token_expires_delta(self) -> timedelta:
        """Get access token expiration delta."""
        return timedelta(minutes=self.access_token_expire_minutes)
    
    @property
    def refresh_token_expires_delta(self) -> timedelta:
        """Get refresh token expiration delta."""
        return timedelta(days=self.refresh_token_expire_days)


class DatabaseConfig(BaseModel):
    """Database configuration settings."""
    host: str = Field(default="localhost")
    port: int = Field(default=5432)
    name: str = Field(default="parallama")
    user: str = Field(default="parallama")
    password_file: str = Field(default="/etc/parallama/db_password")


class RedisConfig(BaseModel):
    """Redis configuration settings."""
    host: str = Field(default="localhost")
    port: int = Field(default=6379)
    db: int = Field(default=0)


class OllamaConfig(BaseModel):
    """Ollama configuration settings."""
    host: str = Field(default="http://localhost")
    port: int = Field(default=11434)


class LoggingConfig(BaseModel):
    """Logging configuration settings."""
    level: str = Field(default="INFO")
    dir: str = Field(default="/var/log/parallama")
    max_size: str = Field(default="100M")
    backup_count: int = Field(default=10)


class ServerConfig(BaseModel):
    """Server configuration settings."""
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    workers: int = Field(default=4)


class Config(BaseModel):
    """Main configuration settings."""
    server: ServerConfig = Field(default_factory=ServerConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    ollama: OllamaConfig = Field(default_factory=OllamaConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    auth: AuthConfig = Field(default_factory=AuthConfig)


def load_config(config_path: Optional[str] = None) -> Config:
    """Load configuration from YAML file."""
    if config_path is None:
        config_path = os.environ.get(
            "PARALLAMA_CONFIG",
            "/etc/parallama/config.yaml"
        )

    if not os.path.exists(config_path):
        return Config()

    with open(config_path, 'r') as f:
        config_data = yaml.safe_load(f)

    return Config(**config_data)


# Global configuration instance
config = load_config()
