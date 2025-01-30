# Parallama Usage Guide

## API Reference

### Authentication
All API requests require Bearer token authentication:
```
Authorization: Bearer <api_key>
```

### Base URL
```
http://server:port/api/v1
```

### Endpoints

#### List Models
```
GET /api/v1/models

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
POST /api/v1/generate

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
POST /api/v1/chat

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

#### Get Usage Statistics
```
GET /api/v1/user/usage

Response:
{
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
}
```

## Client Libraries

### Python Client
```python
from parallama import ParallamaClient

client = ParallamaClient("http://server:port", "your-api-key")

# List models
models = client.list_models()

# Generate text
response = client.generate(
    model="llama2",
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
const ParallamaClient = require('parallama');

const client = new ParallamaClient('http://server:port', 'your-api-key');

// List models
const models = await client.listModels();

// Generate text
const response = await client.generate({
    model: 'llama2',
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
    --token-limit-daily 10000 \
    --token-limit-hourly 1000 \
    --request-limit-daily 1000 \
    --request-limit-hourly 100

# List users
parallama-cli user list

# Get user info
parallama-cli user info <username>

# Delete user
parallama-cli user delete <username>
```

### API Key Management
```bash
# Generate new API key
parallama-cli key generate <username>

# Revoke API key
parallama-cli key revoke <key-id>

# List API keys
parallama-cli key list --username <username>
```

### Usage Information
```bash
# Show current usage
parallama-cli usage show <username>

# Generate usage report
parallama-cli usage report --start-date YYYY-MM-DD --end-date YYYY-MM-DD
```

### Limit Management
```bash
# Set user limits
parallama-cli limits set <username> \
    --token-limit-daily 20000 \
    --token-limit-hourly 2000 \
    --request-limit-daily 2000 \
    --request-limit-hourly 200

# Show user limits
parallama-cli limits show <username>
```

## Configuration

### Service Configuration
The Parallama service can be configured through the following files:
- `/etc/parallama/config.yaml` - Main configuration file
- `/etc/parallama/users.db` - SQLite database (if using SQLite)
- `/var/log/parallama/` - Log directory

### Rate Limiting
Rate limits can be configured per user through the CLI interface. Limits include:
- Token limits (hourly and daily)
- Request limits (hourly and daily)

### Logging
Logs are stored in `/var/log/parallama/` with the following files:
- `api.log` - API access logs
- `usage.log` - Token usage logs
- `error.log` - Error logs
