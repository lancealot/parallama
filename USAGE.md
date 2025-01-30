# Parallama Usage Guide

## API Gateway Overview

Parallama provides multiple API compatibility modes through different base paths:

### Base URLs
- Ollama Native API: `http://server:port/ollama/v1`
- OpenAI Compatible API: `http://server:port/openai/v1`

### Authentication
All API requests require Bearer token authentication:
```
# Using API Key
Authorization: Bearer <api_key>

# Using JWT Access Token
Authorization: Bearer <jwt_token>
```

### API Discovery
```
GET /

Response:
{
    "name": "Parallama API Gateway",
    "version": "1.0.0",
    "gateways": {
        "ollama": {
            "base_path": "/ollama/v1",
            "status": "active",
            "features": ["text generation", "chat completion", "model management"],
            "endpoints": [...]
        },
        "openai": {
            "base_path": "/openai/v1",
            "status": "active",
            "features": ["text completion", "chat completion"],
            "model_mappings": {
                "gpt-3.5-turbo": "llama2",
                "gpt-4": "llama2:70b"
            }
        }
    }
}
```

### Gateway Status
```
GET /status

Response:
{
    "timestamp": "2024-01-30T16:45:00Z",
    "gateways": {
        "ollama": {
            "status": "operational",
            "latency_ms": 42,
            "requests_per_second": 150
        },
        "openai": {
            "status": "operational",
            "latency_ms": 38,
            "requests_per_second": 120
        }
    }
}
```

## API Reference

### Authentication Endpoints

#### Register User
```
POST /auth/register
Request:
{
    "username": "myuser",
    "password": "securepass123"
}

Response:
{
    "user_id": "uuid",
    "username": "myuser",
    "role": "basic",
    "refresh_token": "rt_..."
}
```

#### Login
```
POST /auth/login
Request:
{
    "username": "myuser",
    "password": "securepass123"
}

Response:
{
    "access_token": "eyJ...",
    "refresh_token": "rt_...",
    "token_type": "bearer",
    "expires_in": 1800
}
```

#### Refresh Token
```
POST /auth/token
Request:
{
    "refresh_token": "rt_..."
}

Response:
{
    "access_token": "eyJ...",
    "token_type": "bearer",
    "expires_in": 1800
}
```

### Ollama Native API

#### List Models
```
GET /ollama/v1/models

Response:
{
    "models": [
        {
            "name": "llama2",
            "size": "7B",
            "modified": "2024-01-29T12:00:00Z",
            "details": {
                "format": "gguf",
                "family": "llama"
            }
        }
    ]
}
```

#### Generate Text
```
POST /ollama/v1/generate

Request:
{
    "model": "llama2",
    "prompt": "Write a poem about AI",
    "parameters": {
        "temperature": 0.7,
        "max_tokens": 500
    }
}

Response:
{
    "text": "Generated text...",
    "usage": {
        "prompt_tokens": 5,
        "completion_tokens": 150,
        "total_tokens": 155
    }
}
```

#### Chat Completion
```
POST /ollama/v1/chat

Request:
{
    "model": "llama2",
    "messages": [
        {"role": "user", "content": "Hello!"}
    ],
    "parameters": {
        "temperature": 0.7,
        "max_tokens": 500
    }
}

Response:
{
    "messages": [
        {"role": "assistant", "content": "Hi! How can I help you today?"}
    ],
    "usage": {
        "prompt_tokens": 5,
        "completion_tokens": 8,
        "total_tokens": 13
    }
}
```

### OpenAI Compatible API

#### List Models
```
GET /openai/v1/models

Response:
{
    "data": [
        {
            "id": "gpt-3.5-turbo",
            "object": "model",
            "created": 1677610602,
            "owned_by": "parallama"
        }
    ]
}
```

#### Create Completion
```
POST /openai/v1/completions

Request:
{
    "model": "gpt-3.5-turbo",
    "prompt": "Write a poem about AI",
    "max_tokens": 500,
    "temperature": 0.7
}

Response:
{
    "id": "cmpl-123",
    "object": "text_completion",
    "created": 1677858242,
    "model": "gpt-3.5-turbo",
    "choices": [{
        "text": "Generated text...",
        "index": 0,
        "logprobs": null,
        "finish_reason": "stop"
    }],
    "usage": {
        "prompt_tokens": 5,
        "completion_tokens": 150,
        "total_tokens": 155
    }
}
```

#### Create Chat Completion
```
POST /openai/v1/chat/completions

Request:
{
    "model": "gpt-3.5-turbo",
    "messages": [
        {"role": "user", "content": "Hello!"}
    ],
    "temperature": 0.7,
    "max_tokens": 500
}

Response:
{
    "id": "chatcmpl-123",
    "object": "chat.completion",
    "created": 1677858242,
    "model": "gpt-3.5-turbo",
    "choices": [{
        "message": {
            "role": "assistant",
            "content": "Hi! How can I help you today?"
        },
        "finish_reason": "stop",
        "index": 0
    }],
    "usage": {
        "prompt_tokens": 5,
        "completion_tokens": 8,
        "total_tokens": 13
    }
}
```

### Usage Statistics

#### Get Usage Statistics
```
GET /admin/v1/usage

Response:
{
    "gateways": {
        "ollama": {
            "today": {
                "total_tokens": 1500,
                "total_requests": 25,
                "remaining_tokens": 8500,
                "remaining_requests": 75
            },
            "current_hour": {
                "total_tokens": 500,
                "total_requests": 10,
                "remaining_tokens": 1500,
                "remaining_requests": 40
            }
        },
        "openai": {
            "today": {
                "total_tokens": 800,
                "total_requests": 15,
                "remaining_tokens": 9200,
                "remaining_requests": 85
            },
            "current_hour": {
                "total_tokens": 300,
                "total_requests": 6,
                "remaining_tokens": 1700,
                "remaining_requests": 44
            }
        }
    }
}
```

## Client Libraries

### Python Client
```python
from parallama import ParallamaClient

# Using Ollama native API
client = ParallamaClient(
    base_url="http://server:port",
    api_key="your-api-key",
    gateway="ollama"  # or "openai" for OpenAI compatibility
)

# List models
models = client.list_models()

# Generate text (Ollama native)
response = client.generate(
    model="llama2",
    prompt="Write a poem about AI",
    temperature=0.7
)

# Generate text (OpenAI style)
response = client.completions.create(
    model="gpt-3.5-turbo",
    prompt="Write a poem about AI",
    temperature=0.7
)

# Chat
response = client.chat(
    model="llama2",
    messages=[
        {"role": "user", "content": "Hello!"}
    ]
)
```

### JavaScript Client
```javascript
const { ParallamaClient } = require('parallama');

// Using Ollama native API
const client = new ParallamaClient({
    baseUrl: 'http://server:port',
    apiKey: 'your-api-key',
    gateway: 'ollama'  // or 'openai' for OpenAI compatibility
});

// List models
const models = await client.listModels();

// Generate text (Ollama native)
const response = await client.generate({
    model: 'llama2',
    prompt: 'Write a poem about AI',
    temperature: 0.7
});

// Generate text (OpenAI style)
const response = await client.completions.create({
    model: 'gpt-3.5-turbo',
    prompt: 'Write a poem about AI',
    temperature: 0.7
});

// Chat
const response = await client.chat({
    model: 'llama2',
    messages: [
        {role: 'user', content: 'Hello!'}
    ]
});
```

## Command Line Interface

### User Management
```bash
# Create new user
parallama-cli user create <username> \
    --role basic \
    --gateway ollama \
    --token-limit-daily 10000 \
    --token-limit-hourly 1000 \
    --request-limit-daily 1000 \
    --request-limit-hourly 100

# Create admin user
parallama-cli user create <username> --admin

# List users
parallama-cli user list [--role <role>]

# Get user info
parallama-cli user info <username>

# Update user role
parallama-cli user update <username> --role premium

# Delete user
parallama-cli user delete <username>
```

### Authentication Management
```bash
# Generate new API key
parallama-cli key generate <username>

# Revoke API key
parallama-cli key revoke <key-id>

# List API keys
parallama-cli key list --username <username>

# Force refresh token rotation
parallama-cli auth rotate-tokens <username>

# Revoke all tokens
parallama-cli auth revoke-all <username>
```

### Gateway Management
```bash
# Show gateway status
parallama-cli gateway status

# Enable/disable gateway
parallama-cli gateway toggle openai --enabled true

# Update gateway configuration
parallama-cli gateway config openai \
    --model-mapping gpt-4=llama2:70b

# Show gateway metrics
parallama-cli gateway metrics [--gateway <name>]
```

### Usage Information
```bash
# Show current usage
parallama-cli usage show <username> [--gateway <name>]

# Generate usage report
parallama-cli usage report \
    --start-date YYYY-MM-DD \
    --end-date YYYY-MM-DD \
    --gateway <name> \
    --format json

# Export usage data
parallama-cli usage export --format csv > usage.csv
```

### Rate Limit Management
```bash
# Set user limits for specific gateway
parallama-cli limits set <username> \
    --gateway ollama \
    --token-limit-daily 20000 \
    --token-limit-hourly 2000 \
    --request-limit-daily 2000 \
    --request-limit-hourly 200

# Show user limits
parallama-cli limits show <username> [--gateway <name>]

# Reset rate limits
parallama-cli limits reset <username> [--gateway <name>]
```

## Configuration

### Service Configuration
The Parallama service can be configured through the following files:
- `/etc/parallama/config.yaml` - Main configuration file
- `/etc/parallama/jwt_secret` - JWT signing key
- `/etc/parallama/db_password` - Database password
- `/var/log/parallama/` - Log directory

### Gateway Configuration
Each gateway can be configured in the main config file:
```yaml
api_gateways:
  enabled:
    - ollama
    - openai
  
  discovery:
    enabled: true
    cache_ttl: 300
  
  ollama:
    host: http://localhost
    port: 11434
    base_path: /ollama/v1
    default_model: llama2
  
  openai:
    base_path: /openai/v1
    model_mappings:
      gpt-3.5-turbo: llama2
      gpt-4: llama2:70b
```

### Rate Limiting
Rate limits can be configured per user and per gateway:
- Token limits (hourly and daily)
- Request limits (hourly and daily)
- Different limits for different gateways
- Role-based limit templates

### Authentication
JWT configuration options:
- Token expiration times
- Refresh token rotation
- Password hashing strength
- API key formats

### Logging
Logs are stored in `/var/log/parallama/` with the following files:
- `api.log` - API access logs
- `gateway.log` - Gateway-specific logs
- `usage.log` - Token usage logs
- `auth.log` - Authentication events
- `error.log` - Error logs

### Monitoring
Prometheus metrics available at `/metrics`:
- Request rates and latencies
- Token usage
- Error rates
- Gateway status
- System resources
