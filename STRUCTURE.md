# Project Structure

## Overview

```
parallama/
├── config/                     # Configuration files
│   ├── config.yaml            # Example configuration
│   └── config.dev.yaml        # Development configuration
├── src/parallama/             # Main package
│   ├── api/                   # FastAPI application
│   │   ├── __init__.py
│   │   └── app.py            # Main API application
│   ├── cli/                   # CLI application
│   │   ├── commands/         # CLI command modules
│   │   │   ├── key.py       # API key management
│   │   │   ├── ratelimit.py # Rate limit management
│   │   │   ├── serve.py     # Server management
│   │   │   ├── usage.py     # Usage statistics
│   │   │   └── user.py      # User management
│   │   ├── core/            # CLI core functionality
│   │   │   └── db.py       # Database session management
│   │   └── __init__.py      # CLI entry point
│   ├── core/                 # Core functionality
│   │   ├── config.py        # Configuration management
│   │   ├── database.py      # Database configuration
│   │   ├── exceptions.py    # Custom exceptions
│   │   ├── permissions.py   # Permission management
│   │   └── redis.py         # Redis configuration
│   ├── gateway/              # API gateway functionality
│   │   ├── base.py          # Base gateway class
│   │   ├── config.py        # Gateway configuration
│   │   ├── ollama.py        # Ollama gateway
│   │   ├── openai.py        # OpenAI compatibility
│   │   ├── registry.py      # Gateway registry
│   │   └── router.py        # FastAPI router
│   ├── models/               # SQLAlchemy models
│   │   ├── api_key.py       # API key model
│   │   ├── base.py          # Base model class
│   │   ├── rate_limit.py    # Rate limit model
│   │   ├── refresh_token.py # Refresh token model
│   │   ├── role.py          # Role model
│   │   ├── user.py          # User model
│   │   └── user_role.py     # User-role association
│   └── services/            # Business logic
│       ├── api_key.py       # API key service
│       ├── auth.py          # Authentication service
│       ├── rate_limit.py    # Rate limiting service
│       ├── role.py          # Role management service
│       └── token_counter.py # Token counting service
├── systemd/                  # Systemd service files
│   └── parallama.service    # Systemd service definition
├── tests/                    # Test suite
│   ├── conftest.py          # Test configuration
│   ├── test_api/            # API tests
│   ├── test_cli/            # CLI tests
│   └── test_services/       # Service tests
├── LICENSE                   # MIT license
├── README.md                # Project overview
├── USAGE.md                 # Usage documentation
├── parallama.spec           # RPM spec file
└── pyproject.toml           # Project metadata
```

## Component Details

### API Layer (`api/`)
- FastAPI application handling HTTP requests
- Endpoint definitions and routing
- Request/response models
- Middleware (authentication, rate limiting)

### CLI Layer (`cli/`)
- Typer-based command-line interface
- User and API key management commands
- Server management commands
- Usage statistics and reporting

### Core (`core/`)
- Configuration management
- Database and Redis setup
- Permission system
- Exception handling

### Gateway (`gateway/`)
- API gateway implementation
- Ollama API proxy
- OpenAI compatibility layer
- Gateway registry and routing

### Models (`models/`)
- SQLAlchemy model definitions
- Database schema
- Model relationships
- Data validation

### Services (`services/`)
- Business logic implementation
- Authentication and authorization
- Rate limiting
- Usage tracking

### System Services (`systemd/`)
- Systemd service configuration
- Service dependencies
- Runtime directories
- Security settings

## Key Files

### Configuration
- `config/config.yaml`: Example configuration file
- `config/config.dev.yaml`: Development configuration
- `src/parallama/core/config.py`: Configuration management
- `systemd/parallama.service`: Service configuration

### Entry Points
- `src/parallama/cli/__init__.py`: CLI entry point
- `src/parallama/api/app.py`: API entry point

### Package Management
- `pyproject.toml`: Project metadata and dependencies
- `parallama.spec`: RPM package specification

### Documentation
- `README.md`: Project overview
- `USAGE.md`: Usage documentation
- `STRUCTURE.md`: This file

## Development Workflow

1. Code Organization:
   - New features start in `services/`
   - Expose via API in `api/`
   - Add CLI commands in `cli/commands/`
   - Update tests in `tests/`

2. System Services:
   - PostgreSQL for database
   - Redis for rate limiting and caching
   - Ollama for LLM inference
   - Parallama service for API gateway

3. Configuration:
   - Development: `config/config.dev.yaml`
   - Production: `/etc/parallama/config.yaml`
   - Environment variables override config
   - Service configuration in systemd files

4. Testing:
   - Unit tests in `tests/`
   - Integration tests with system services
   - Service health checks
   - API endpoint testing

5. Deployment:
   - Build RPM package
   - Install system dependencies
   - Configure system services
   - Initialize database
   - Deploy service configuration
