# Parallama Project Plan

## Phase 1: Infrastructure Setup ✓
- [x] Project structure creation
- [x] Basic documentation
- [x] Git repository initialization
- [x] RPM spec file creation

## Phase 2: Core API Development ✓
- [x] FastAPI application setup
- [x] Authentication Service Core
  - [x] JWT token generation and validation
  - [x] Password hashing with bcrypt
  - [x] Refresh token system with rotation and reuse detection
  - [x] Comprehensive test coverage
- [x] Authentication middleware
  - [x] API key management
  - [x] Role-based access control
  - [x] Middleware implementation
  - [x] Comprehensive test coverage

## Phase 2.5: API Gateway Implementation
- [x] Gateway Architecture Setup
  - [x] Base gateway interface
  - [x] Gateway router and registry
  - [x] Discovery endpoint
  - [x] Status monitoring
  - [x] Configuration system
  - [x] Comprehensive test coverage
- [x] Ollama Gateway Implementation
  - [x] Basic gateway functionality
  - [x] Model discovery
  - [x] Request/response transformation
  - [x] Authentication integration
  - [x] Streaming support
  - [x] Comprehensive test coverage
- [x] Gateway-specific Features
  - [x] Per-gateway rate limiting
  - [x] Model mapping configuration
  - [x] Response transformation
  - [x] Usage tracking
- [ ] OpenAI Compatibility Gateway
  - [ ] Basic gateway functionality
  - [ ] Model mapping
  - [ ] Request format conversion
  - [ ] Response transformation
  - [ ] Streaming support

## Phase 2.6: API Integration ✓
- [x] Rate limiting implementation
  - [x] Redis integration
  - [x] Token counting
  - [x] Per-model limits
  - [x] Usage tracking
  - [x] Wildcard gateway support
  - [x] Token accumulation tracking
  - [x] Redis mock for testing
- [x] Usage tracking
  - [x] Request logging
  - [x] Token usage tracking
  - [x] Analytics generation

## Phase 3: Database Integration
- [x] PostgreSQL/SQLite schema design
- [x] Database migrations with Alembic
- [x] User management with UUID string IDs
- [x] Usage logging
- [x] Session handling improvements

## Phase 4: CLI Tool Development ✓
- [x] User management commands
- [x] API key management with UUID string IDs
- [x] Comprehensive test coverage
- [x] Usage reporting
  - [x] List usage history
  - [x] Generate summaries
  - [x] Export data (JSON/CSV)
- [x] Rate limit configuration
  - [x] Set rate limits
  - [x] View current limits
  - [x] Reset to defaults

## Phase 5: System Integration
- [ ] Systemd service configuration
- [x] Logging setup
- [x] Configuration management
- [ ] RPM packaging

## Phase 6: Testing & Documentation
- [x] Unit tests
- [x] Integration tests
- [x] API documentation
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
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'basic',
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- API Keys table
CREATE TABLE api_keys (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    key_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    revoked_at TIMESTAMP WITH TIME ZONE,
    last_used_at TIMESTAMP WITH TIME ZONE
);

-- Refresh Tokens table
CREATE TABLE refresh_tokens (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    token_hash VARCHAR(255) NOT NULL,
    issued_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    revoked_at TIMESTAMP WITH TIME ZONE,
    replaced_by UUID REFERENCES refresh_tokens(id)
);

-- Gateway Rate Limits table
CREATE TABLE gateway_rate_limits (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    gateway_type VARCHAR(50) NOT NULL,
    token_limit_hourly INTEGER,
    token_limit_daily INTEGER,
    request_limit_hourly INTEGER,
    request_limit_daily INTEGER,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, gateway_type)
);

-- Gateway Usage Logs table
CREATE TABLE gateway_usage_logs (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    gateway_type VARCHAR(50) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    endpoint VARCHAR(255) NOT NULL,
    model_name VARCHAR(255),
    tokens_used INTEGER,
    request_duration FLOAT,
    status_code INTEGER,
    error_message TEXT
);

-- Model Mappings table
CREATE TABLE model_mappings (
    id UUID PRIMARY KEY,
    gateway_type VARCHAR(50) NOT NULL,
    external_model VARCHAR(255) NOT NULL,
    internal_model VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(gateway_type, external_model)
);
```

### API Components

#### Core Components
- Authentication Service
  - JWT token management
  - Password hashing
  - API key management
  - Refresh token handling
- User Management Service
  - User CRUD operations
  - Role management
  - Permission checking
- Rate Limiting Service
  - Per-gateway rate limiting
  - Token counting
  - Request tracking
  - Wildcard gateway support
  - Token accumulation tracking

#### Gateway Components
- Gateway Registry Service
  - Gateway registration
  - Status monitoring
  - Discovery endpoint
- Gateway Router
  - Request routing
  - Authentication validation
  - Error handling
- Gateway Implementations
  - Base gateway interface
  - Protocol-specific transformers
  - Response formatters

#### Integration Services
- Ollama Integration Service
  - Model management
  - Request handling
  - Response processing
- Usage Tracking Service
  - Per-gateway usage logging
  - Analytics processing
  - Report generation

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

authentication:
  jwt_secret_key_file: /etc/parallama/jwt_secret
  access_token_expire_minutes: 30
  refresh_token_expire_days: 30
  password_hash_rounds: 12

api_gateways:
  enabled:
    - ollama
    - openai
  
  discovery:
    enabled: true
    cache_ttl: 300
    include_metrics: true
  
  ollama:
    host: http://localhost
    port: 11434
    base_path: /ollama/v1
    default_model: llama2
  
  openai:
    base_path: /openai/v1
    compatibility_mode: true
    model_mappings:
      gpt-3.5-turbo: llama2
      gpt-4: llama2:70b

logging:
  level: INFO
  dir: /var/log/parallama
  max_size: 100M
  backup_count: 10
```

## Implementation Notes

### Security Considerations

#### Authentication Security
- API keys and passwords securely hashed using bcrypt
- JWT tokens signed with RS256 algorithm
- Refresh tokens with automatic rotation
- Token blacklisting for revoked tokens
- Secure token storage guidelines

#### API Gateway Security
- Per-gateway rate limiting
- Request validation per gateway type
- Model access control
- Error message sanitization
- Gateway-specific security headers

#### System Security
- All sensitive credentials in separate files
- Database connection pooling
- Redis security configuration
- Input validation on all endpoints
- Regular security audits
- Automated vulnerability scanning

#### Operational Security
- Gateway status monitoring
- Error rate alerting
- Access log analysis
- Regular token cleanup
- Automated backup system

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
