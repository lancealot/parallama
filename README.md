![alt_text](https://github.com/lancealot/parallama/blob/main/parallama.png?raw=true)

# Parallama

Parallama is a multi-user authentication and access management service for Ollama. It provides a secure API gateway that enables multiple users to access Ollama services over a network with individual API keys, rate limiting, and usage tracking.

## Features

- REST API for authenticated access to Ollama services
- User management with API key authentication
- Configurable rate limiting (requests and tokens)
- Usage tracking and reporting
- Command-line interface for user and API key management
- Systemd service integration
- PostgreSQL backend for persistent storage

## Requirements

- RHEL 9 or compatible
- Python 3.9+
- PostgreSQL 13+
- Ollama

## Installation

This project can be installed via RPM package:

```bash
sudo dnf install parallama
```

See USAGE.md for detailed setup and configuration instructions.
