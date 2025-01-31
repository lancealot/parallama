# Project Structure

## Overview

Parallama follows a src-layout Python package structure, which is considered a best practice for Python projects. This structure separates the package source code from other project files and prevents implicit imports.

## Directory Structure

```
parallama/
├── alembic/                    # Database migrations
│   ├── versions/               # Migration version files
│   ├── env.py                 # Alembic environment configuration
│   └── script.py.mako         # Migration script template
│
├── config/                     # Configuration files
│   ├── config.dev.yaml        # Development configuration
│   └── db_password.dev        # Development database password
│
├── logs/                       # Application logs
│
├── scripts/                    # Utility scripts
│   └── run_dev.py             # Development server script
│
├── src/                        # Source code root
│   └── parallama/             # Main package
│       ├── api/               # API endpoints and routing
│       │   ├── __init__.py
│       │   └── app.py         # FastAPI application
│       │
│       ├── cli/               # Command-line interface
│       │   ├── __init__.py
│       │   ├── commands/      # CLI command implementations
│       │   │   ├── __init__.py
│       │   │   ├── key.py     # API key management commands
│       │   │   └── user.py    # User management commands
│       │   ├── core/          # CLI core functionality
│       │   │   ├── __init__.py
│       │   │   └── db.py      # Database session management
│       │   └── utils/         # CLI utilities
│       │       ├── __init__.py
│       │       └── output.py  # Output formatting
│       │
│       ├── core/              # Core functionality
│       │   ├── __init__.py
│       │   ├── config.py      # Configuration management
│       │   ├── database.py    # Database connection
│       │   ├── exceptions.py  # Custom exceptions
│       │   ├── permissions.py # Permission system
│       │   └── redis.py       # Redis client
│       │
│       ├── db/                # Database
│       │   ├── __init__.py
│       │   └── session.py     # Database session management
│       │
│       ├── middleware/        # Middleware components
│       │   ├── __init__.py
│       │   └── auth.py        # Authentication middleware
│       │
│       ├── models/            # Database models
│       │   ├── __init__.py
│       │   ├── api_key.py     # API key model
│       │   ├── base.py        # Base model class
│       │   ├── rate_limit.py  # Rate limiting model
│       │   ├── refresh_token.py # Refresh token model
│       │   ├── role.py        # Role model
│       │   ├── user_role.py   # User-Role association
│       │   └── user.py        # User model
│       │
│       ├── services/          # Business logic
│       │   ├── __init__.py
│       │   ├── api_key.py     # API key management
│       │   ├── auth.py        # Authentication service
│       │   └── role.py        # Role management
│       │
│       └── __init__.py
│
├── tests/                      # Test suite
│   ├── __init__.py
│   ├── conftest.py            # Test configuration
│   ├── test_api_key_service.py
│   ├── test_auth_middleware.py
│   ├── test_auth_service.py
│   ├── test_cli_commands.py   # CLI command tests
│   ├── test_cli_db.py        # CLI database tests
│   ├── test_cli_output.py    # CLI output tests
│   └── test_role_service.py
│
├── .gitignore                 # Git ignore rules
├── alembic.ini                # Alembic configuration
├── NEXT_SESSION.md            # Development planning
├── parallama.png              # Project logo
├── projectplan.md             # Project roadmap
├── pyproject.toml             # Project metadata and dependencies
├── README.md                  # Project documentation
├── STRUCTURE.md               # This file
└── USAGE.md                   # Usage documentation
```

## Key Components

### Source Code (`src/parallama/`)

The main package code is organized into several modules:

- **api/**: FastAPI application and route definitions
- **cli/**: Command-line interface
  * **commands/**: CLI command implementations
  * **core/**: CLI core functionality
  * **utils/**: CLI utilities
- **core/**: Core functionality and configuration
- **db/**: Database connection and session management
- **middleware/**: Request processing middleware
- **models/**: SQLAlchemy database models
  * String UUIDs for SQLite compatibility
  * Base model with common fields
  * Role-based access control models
- **services/**: Business logic implementation

### Configuration (`config/`)

Configuration files for different environments:
- Development configuration
- Database credentials
- (Production configs should be mounted at runtime)

### Database Migrations (`alembic/`)

Alembic migration management:
- Version-controlled schema changes
- Migration scripts
- Database environment configuration

### Tests (`tests/`)

Comprehensive test suite:
- Unit tests for services
- Integration tests for API
- CLI command tests
- Test fixtures and configuration
- Mock database sessions
- Mock Redis client

### Scripts (`scripts/`)

Utility scripts for development and operations:
- Development server runner
- (Future scripts for deployment, maintenance)

## Import Conventions

The project uses absolute imports throughout:

```python
# Correct
from parallama.models.user import User
from parallama.services.auth import AuthService

# Avoid
from ...models.user import User  # Relative imports
```

## Package Configuration

The project uses `pyproject.toml` for package configuration:
- Package metadata
- Dependencies
- Build system configuration
- Development tools configuration

The src-layout is configured in `pyproject.toml`:
```toml
[tool.setuptools]
package-dir = {"" = "src"}

[tool.setuptools.packages.find]
where = ["src"]
include = ["parallama*"]
```

This ensures proper package installation and import behavior.
