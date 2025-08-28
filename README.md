# Atlassian OAuth Proxy v1

A secure OAuth proxy service for Atlassian integrations built with FastAPI. This service handles OAuth authentication flows and proxies authenticated requests to MCP (Model Context Protocol) servers.

## Features

- 🔐 Secure OAuth 2.0 authentication with Atlassian
- 🚀 High-performance FastAPI backend
- 🔄 Request proxying to MCP servers
- 📝 Comprehensive logging and monitoring
- 🧪 Full test coverage
- 🏗️ Modular, extensible architecture
- 📚 Complete API documentation
- 🔧 Configuration management

## Architecture

The project follows a modular design with clear separation of concerns:

- **Authentication Layer**: OAuth 2.0 flow handling
- **Proxy Layer**: Request forwarding and response handling
- **Configuration Management**: Environment-based settings
- **Logging & Monitoring**: Structured logging with correlation IDs
- **Security**: Token validation and secure storage

## Quick Start

### Prerequisites

- Python 3.11+
- pip or poetry
- Docker (optional)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/arch-faustocorrea/atlassian-oauth-proxy-v1.git
cd atlassian-oauth-proxy-v1
```

2. Install dependencies:
```bash
pip install -r requirements.txt
# or
poetry install
```

3. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your Atlassian OAuth credentials
```

4. Run the application:
```bash
uvicorn src.main:app --reload
```

The API will be available at `http://localhost:8000` with interactive docs at `http://localhost:8000/docs`.

## Configuration

The application uses environment-based configuration. Key settings include:

- `ATLASSIAN_CLIENT_ID`: Your Atlassian OAuth client ID
- `ATLASSIAN_CLIENT_SECRET`: Your Atlassian OAuth client secret
- `ATLASSIAN_REDIRECT_URI`: OAuth callback URL
- `MCP_SERVER_URL`: Target MCP server URL
- `SECRET_KEY`: Application secret key for JWT signing

See `config/settings.py` for all available options.

## API Documentation

### Authentication Endpoints

- `GET /auth/login` - Initiate OAuth flow
- `GET /auth/callback` - Handle OAuth callback
- `POST /auth/refresh` - Refresh access token
- `POST /auth/logout` - Revoke tokens

### Proxy Endpoints

- `POST /proxy/{path:path}` - Proxy authenticated requests to MCP server

### Health & Monitoring

- `GET /health` - Health check endpoint
- `GET /metrics` - Application metrics

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_auth.py -v
```

### Code Quality

```bash
# Format code
black src/ tests/
isort src/ tests/

# Lint code
flake8 src/ tests/
mypy src/

# Pre-commit hooks
pre-commit install
pre-commit run --all-files
```

### Docker

```bash
# Build image
docker build -t atlassian-oauth-proxy .

# Run container
docker run -p 8000:8000 --env-file .env atlassian-oauth-proxy
```

## Project Structure

```
atlassian-oauth-proxy-v1/
├── src/
│   ├── auth/                 # Authentication modules
│   ├── proxy/               # Proxy functionality
│   ├── core/                # Core utilities and base classes
│   ├── models/              # Pydantic models
│   └── main.py              # FastAPI application
├── tests/                   # Test suite
├── config/                  # Configuration files
├── docs/                    # Documentation
├── scripts/                 # Utility scripts
└── requirements.txt         # Dependencies
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Security

- All tokens are stored securely with encryption
- HTTPS is enforced in production
- CORS is properly configured
- Rate limiting is implemented
- Input validation on all endpoints

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For questions and support, please open an issue in the GitHub repository.
