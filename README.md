![alt_text](https://github.com/lancealot/parallama/blob/main/parallama.png?raw=true)

# Parallama

Parallama is a multi-user authentication and access management service for Ollama. It provides a secure API gateway that enables multiple users to access Ollama services over a network with individual API keys, rate limiting, and usage tracking.

## Features

### API Gateway Support
- Multiple API compatibility modes:
  - Native Ollama API (/ollama/v1)
  - OpenAI-compatible API (/openai/v1)
  - Extensible framework for future API types
- API discovery and status monitoring
- Per-gateway rate limiting and usage tracking

### Authentication & Security
- JWT-based authentication with refresh tokens
- API key management with automatic rotation
- Role-based access control (admin, premium, basic)
- Secure password and token handling
- Gateway-specific security headers

### Core Features
- REST API for authenticated access to Ollama services
- Configurable rate limiting (per gateway, user, and model)
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
parallama-cli user create myuser
parallama-cli key generate myuser
```

5. Test the API:
```bash
# Using native Ollama API
curl http://localhost:8000/ollama/v1/models \
  -H "Authorization: Bearer your-api-key"

# Using OpenAI compatibility mode
curl http://localhost:8000/openai/v1/models \
  -H "Authorization: Bearer your-api-key"
```

## Installation

This project can be installed via RPM package:

```bash
sudo dnf install parallama
```

See USAGE.md for detailed setup and configuration instructions.
