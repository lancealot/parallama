# Parallama Project Plan

## Phase 1: Infrastructure Setup
- [x] Project structure creation
- [x] Basic documentation
- [x] Git repository initialization
- [x] RPM spec file creation

## Phase 2: Core API Development
- [x] FastAPI application setup
- [ ] Authentication middleware
- [ ] Ollama API integration
- [ ] Rate limiting implementation
- [ ] Usage tracking

## Phase 3: Database Integration
- [ ] PostgreSQL schema design
- [ ] Database migrations
- [ ] User management
- [ ] Usage logging

## Phase 4: CLI Tool Development
- [ ] User management commands
- [ ] API key management
- [ ] Usage reporting
- [ ] Rate limit configuration

## Phase 5: System Integration
- [ ] Systemd service configuration
- [ ] Logging setup
- [ ] Configuration management
- [ ] RPM packaging

## Phase 6: Testing & Documentation
- [ ] Unit tests
- [ ] Integration tests
- [ ] API documentation
- [ ] Deployment guide

## Future Enhancements
- Multi-model support
- Advanced rate limiting features
- Usage analytics dashboard
- Backup and restore utilities

## Technical Specifications

### Database Schema
```sql
-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- API Keys table
CREATE TABLE api_keys (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    key_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    revoked_at TIMESTAMP WITH TIME ZONE
);

-- Rate Limits table
CREATE TABLE rate_limits (
    user_id UUID PRIMARY KEY REFERENCES users(id),
    token_limit_hourly INTEGER,
    token_limit_daily INTEGER,
    request_limit_hourly INTEGER,
    request_limit_daily INTEGER,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Usage Logs table
CREATE TABLE usage_logs (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    endpoint VARCHAR(255) NOT NULL,
    model_name VARCHAR(255),
    tokens_used INTEGER,
    request_duration FLOAT,
    status_code INTEGER
);
```

### API Components
- Authentication Middleware
- Rate Limiting Middleware
- Token Counting Service
- Usage Tracking Service
- Model Management Service
- User Management Service

### System Requirements
- Python 3.9+
- PostgreSQL 13+
- Redis (for rate limiting)
- Ollama
- Systemd

### Configuration Files
```yaml
# /etc/parallama/config.yaml
server:
  host: 0.0.0.0
  port: 8000
  workers: 4

database:
  host: localhost
  port: 5432
  name: parallama
  user: parallama
  password_file: /etc/parallama/db_password

redis:
  host: localhost
  port: 6379
  db: 0

ollama:
  host: http://localhost
  port: 11434

logging:
  level: INFO
  dir: /var/log/parallama
  max_size: 100M
  backup_count: 10
```

## Implementation Notes

### Security Considerations
- API keys must be securely hashed before storage
- All database passwords stored in separate files
- Rate limiting to prevent abuse
- Input validation on all endpoints
- Secure headers middleware
- Regular security audits

### Performance Optimization
- Connection pooling for database
- Caching for frequently accessed data
- Async API endpoints
- Batch processing for logs
- Regular maintenance tasks

### Monitoring
- Prometheus metrics
- Grafana dashboards
- Error alerting
- Resource usage monitoring
- API usage analytics
