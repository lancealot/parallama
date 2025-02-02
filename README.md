![alt_text](https://github.com/lancealot/parallama/blob/main/parallama.png?raw=true)

# Parallama

Parallama is a multi-user authentication and access management service for Ollama. It provides a secure API gateway that enables multiple users to access Ollama services over a network with individual API keys, rate limiting, and usage tracking.

## Features

### API Gateway Support
- Multiple API compatibility modes:
  - Native Ollama API (/ollama/v1)
  - OpenAI-compatible API (/openai/v1) (Coming Soon)
  - Extensible framework for future API types
- API discovery and status monitoring
- Per-gateway rate limiting and usage tracking
- Wildcard gateway support for shared limits
- Token accumulation tracking

### Authentication & Security
- JWT-based authentication with refresh tokens
  - Automatic token rotation
  - Token reuse detection
  - Rate limiting
  - Chain revocation
- API key management with automatic rotation
- Role-based access control (RBAC)
  - Flexible permission system
  - Role hierarchy (admin, premium, basic)
  - Per-gateway permissions
  - Role expiration support
  - Comprehensive test coverage
- Secure password and token handling
- Gateway-specific security headers
- Comprehensive test coverage for all security features

### Core Features
- REST API for authenticated access to Ollama services
- Advanced rate limiting:
  - Per-gateway, user, and model limits
  - Token and request counting
  - Hourly and daily limits
  - Wildcard gateway support
  - Token accumulation tracking
- Detailed usage tracking and reporting
- Command-line interface for system management
- Systemd service integration
- Prometheus metrics and Grafana dashboards

### Storage & Caching
- PostgreSQL backend for persistent storage
- Redis for rate limiting and token management
- Connection pooling and query optimization

## Requirements

- RHEL 9 or compatible
- Python 3.9+
- PostgreSQL 13+
- Redis 5+
- Ollama
- podman
- podman-compose

## Quick Start

1. Install dependencies:
```bash
sudo dnf install postgresql-server redis ollama
```

2. Install Parallama:
```bash
sudo dnf install parallama
```

3. Initialize and start services:
```bash
sudo systemctl enable --now postgresql redis ollama parallama
```

4. Create your first user and API key:
```bash
# Create a basic user
parallama-cli user create myuser

# Create an admin user with premium role
parallama-cli user create adminuser --admin --role premium

# Generate an API key
parallama-cli key generate myuser --description "Development key"

# List API keys
parallama-cli key list --username myuser

# Revoke an API key
parallama-cli key revoke <key-id>

# List users
parallama-cli user list

# Get user info
parallama-cli user info myuser

# Update user
parallama-cli user update myuser --role premium --admin

# Delete user
parallama-cli user delete myuser

# Manage rate limits
parallama-cli ratelimit set myuser ollama --token-hourly 1000 --token-daily 10000
parallama-cli ratelimit get myuser [gateway_type]
parallama-cli ratelimit reset myuser ollama

# View usage information
parallama-cli usage list myuser [--gateway ollama] [--days 7] [--model llama2]
parallama-cli usage summary myuser [--gateway ollama] [--days 30]
parallama-cli usage export myuser json|csv [--output file.json] [--gateway ollama] [--model llama2]
```

5. Test the API:
```bash
# Using native Ollama API
curl http://localhost:8000/ollama/v1/models \
  -H "Authorization: Bearer your-api-key"

# Using OpenAI compatibility mode (Coming Soon)
curl http://localhost:8000/openai/v1/models \
  -H "Authorization: Bearer your-api-key"
```

## Installation

This project can be installed via RPM package:

```bash
sudo dnf install parallama
```

See USAGE.md for detailed setup and configuration instructions.

## Development

This project uses a src-layout Python package structure. For detailed information about the project structure, components, and development conventions, see [STRUCTURE.md](STRUCTURE.md).

### Development Setup

1. Clone the repository:
```bash
git clone https://github.com/lancealot/parallama.git
cd parallama
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install development dependencies:
```bash
pip install -e ".[dev]"
```

4. Start development services:
```bash
podman-compose up -d  # Starts PostgreSQL and Redis
```

5. Initialize the database:
```bash
alembic upgrade head  # Applies all database migrations
```

6. Run development server:
```bash
python scripts/run_dev.py
```

7. Run tests:
```bash
pytest tests/  # Run all tests
pytest tests/ -v  # Run with verbose output
pytest tests/test_auth_service.py  # Run specific test file
```

### Project Structure

The project follows a clean, modular structure:
- `src/parallama/` - Main package source code
  * `api/` - FastAPI application and routes
  * `core/` - Core functionality and configuration
  * `db/` - Database connection and session management
  * `middleware/` - Authentication and authorization middleware
  * `models/` - SQLAlchemy database models
  * `services/` - Business logic implementation
- `tests/` - Comprehensive test suite
- `alembic/` - Database migrations
- `config/` - Configuration files
- `scripts/` - Development and utility scripts

See [STRUCTURE.md](STRUCTURE.md) for complete documentation of the project structure.

### Current Status

#### Completed Features
- Authentication Service with JWT and API keys
- Role-Based Access Control (RBAC)
- Database Models and Migrations
- Authentication Middleware
- Rate Limiting Service
  * Per-gateway and shared limits
  * Token accumulation tracking
  * Redis integration with mocking support
  * Comprehensive test coverage
- Ollama Gateway Implementation
- Usage Tracking and Logging
- Comprehensive Test Coverage

#### In Progress
- OpenAI Compatibility Gateway
- Usage Analytics Dashboard
- Deployment Documentation

See [NEXT_SESSION.md](NEXT_SESSION.md) for detailed development planning.
