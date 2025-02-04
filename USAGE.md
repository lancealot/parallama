# Parallama Usage Guide

## Installation

### Production Installation

1. Install required system services:
```bash
sudo dnf install postgresql postgresql-server redis
sudo postgresql-setup --initdb
```

2. Install the RPM package:
```bash
sudo dnf install parallama-0.1.0-1.el9.x86_64.rpm
```

3. Configure PostgreSQL:
```bash
sudo -u postgres createuser parallama
sudo -u postgres createdb parallama
sudo -u postgres psql -c "ALTER USER parallama WITH PASSWORD '$(sudo cat /etc/parallama/db_password)';"
```

4. Start required services:
```bash
sudo systemctl start postgresql redis ollama
sudo systemctl enable postgresql redis ollama
```

5. Start Parallama service:
```bash
sudo systemctl start parallama
sudo systemctl enable parallama
```

## Configuration

### Configuration Files

- `/etc/parallama/config.yaml` - Main configuration file
- `/etc/parallama/jwt_secret` - JWT signing key (auto-generated)
- `/etc/parallama/db_password` - Database password (auto-generated)
- `/var/log/parallama/` - Log directory
- `/var/lib/parallama/` - Data directory

### Environment Variables

- `PARALLAMA_DB_URL` - Database connection URL
- `PARALLAMA_REDIS_URL` - Redis connection URL
- `PARALLAMA_JWT_SECRET` - JWT signing key

## CLI Usage

### User Management

Create a new user:
```bash
parallama-cli user create username --role basic
```

List users:
```bash
parallama-cli user list
```

Update user:
```bash
parallama-cli user update username --role premium
```

### API Key Management

Create an API key:
```bash
parallama-cli key create USER_ID --name "My API Key"
```

List API keys:
```bash
parallama-cli key list
```

Revoke an API key:
```bash
parallama-cli key revoke KEY_ID
```

### Rate Limit Management

Set rate limit:
```bash
parallama-cli ratelimit set USER_ID --requests 1000 --window 3600
```

View rate limits:
```bash
parallama-cli ratelimit list
```

### Usage Statistics

View usage:
```bash
parallama-cli usage show USER_ID
```

Export usage report:
```bash
parallama-cli usage export --format csv --output usage.csv
```

### Server Management

Start the API server:
```bash
parallama-cli serve start --workers 4
```

## API Usage

### Authentication

Authenticate with API key:
```bash
curl -H "Authorization: Bearer YOUR_API_KEY" http://localhost:8000/ollama/v1/chat/completions
```

### Endpoints

#### Ollama Gateway

- `/ollama/v1/*` - Proxied Ollama API endpoints
  - `/chat/completions` - Chat completions
  - `/embeddings` - Text embeddings
  - `/models` - Model management

#### OpenAI Compatibility

- `/openai/v1/*` - OpenAI-compatible endpoints
  - `/chat/completions` - GPT-compatible chat
  - `/completions` - Text completions
  - `/embeddings` - Text embeddings

## Development

### Local Setup

1. Install system dependencies:
```bash
sudo dnf install postgresql postgresql-server redis
sudo postgresql-setup --initdb
sudo systemctl start postgresql redis
sudo systemctl enable postgresql redis
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate
```

3. Install package dependencies:
```bash
pip install -e .
```

4. Configure development database:
```bash
sudo -u postgres createuser parallama
sudo -u postgres createdb parallama_dev
sudo -u postgres psql -c "ALTER USER parallama WITH PASSWORD 'development';"
```

5. Create development config:
```bash
cp config/config.yaml config/config.dev.yaml
```

6. Run development server:
```bash
parallama-cli serve start --reload --config config/config.dev.yaml
```
