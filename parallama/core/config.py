"""Configuration management for Parallama."""

import os
from typing import Optional

import yaml
from pydantic import BaseModel, Field


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
