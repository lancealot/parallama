![alt_text](https://github.com/lancealot/parallama/blob/main/assets/parallama.png?raw=true)

# Parallama

Multi-user authentication and access management service for Ollama.

## Features

- **Multi-User Support**: Create and manage multiple user accounts with different roles and permissions
- **API Key Management**: Generate and manage API keys for secure access
- **Rate Limiting**: Configure per-user rate limits to control API usage
- **Usage Tracking**: Monitor and analyze API usage patterns
- **Ollama Gateway**: Secure proxy to Ollama API endpoints
- **OpenAI Compatibility**: OpenAI-compatible API endpoints that map to Ollama models

## Requirements

- Python 3.9 or higher
- PostgreSQL 13 or higher
- Redis 5.0 or higher
- Ollama

## Quick Start

1. Install the package:
```bash
sudo dnf install parallama-0.1.0-1.el9.x86_64.rpm
```

2. Start the service:
```bash
sudo systemctl start parallama
sudo systemctl enable parallama
```

3. Create a user:
```bash
parallama-cli user create myuser --role basic
```

4. Create an API key:
```bash
parallama-cli key create USER_ID --name "My API Key"
```

5. Use the API:
```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"model": "llama2", "messages": [{"role": "user", "content": "Hello!"}]}' \
     http://localhost:8000/ollama/v1/chat/completions
```

## Documentation

- [Usage Guide](USAGE.md) - Detailed usage instructions
- [Project Structure](STRUCTURE.md) - Code organization and architecture
- [Project Plan](projectplan.md) - Development roadmap and plans

## Development

1. Clone the repository:
```bash
git clone https://github.com/yourusername/parallama.git
cd parallama
```

2. Install system dependencies:
```bash
sudo dnf install postgresql postgresql-server redis
sudo postgresql-setup --initdb
sudo systemctl start postgresql redis
sudo systemctl enable postgresql redis
```

3. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate
```

4. Install package dependencies:
```bash
pip install -e .
```

5. Configure development database:
```bash
sudo -u postgres createuser parallama
sudo -u postgres createdb parallama_dev
sudo -u postgres psql -c "ALTER USER parallama WITH PASSWORD 'development';"
```

6. Run development server:
```bash
parallama-cli serve start --reload --config config/config.dev.yaml
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

## License

MIT License - see [LICENSE](LICENSE) for details
