# FastAPI Boilerplate

A production-ready FastAPI boilerplate with authentication, database management, AI chatbot, and essential middleware.

## Features

### Core Features
- **Authentication & Authorization**
  - Email/Password registration with email verification
  - OAuth2 (Google, Apple Sign-In)
  - JWT access tokens with secure refresh token rotation
  - Device tracking and multi-device session management
  - Password reset with rate-limited verification codes

- **User Management**
  - Extensible user model with timezone support
  - Profile management endpoints
  - Account deactivation
  - User repository pattern

- **AI Chatbot**
  - Real-time streaming responses via WebSocket
  - Thread-based conversation management
  - File attachments support (images, documents, audio, video)
  - Automatic message summarization
  - Content moderation with fallback safety
  - Context-aware conversations

- **Database & ORM**
  - PostgreSQL with async SQLAlchemy
  - Alembic migrations
  - Base repository pattern for CRUD operations
  - Proper foreign key relationships and indexes

### Production-Ready Middleware
- **Security Headers**: HSTS, CSP, X-Frame-Options, X-Content-Type-Options
- **Request Logging**: Structured JSON logging for production
- **Rate Limiting**: Redis-backed rate limiting
- **CORS**: Configurable cross-origin requests
- **Max Request Size**: File upload size limits

### Additional Features
- **Caching**: Redis response caching decorator
- **Storage**: S3-compatible file storage
- **Email**: AWS SES email service
- **Celery**: Background task processing
- **Countries API**: Country list with timezone inference
- **OpenAPI**: Bearer token auth in Swagger UI

---

## Architecture

```
fastapi-boilerplate/
├── api.py                      # FastAPI application entry point
├── src/
│   ├── core/                   # Core application logic
│   │   ├── config.py          # Settings and environment variables
│   │   ├── database.py        # Database connection and session
│   │   ├── security.py        # JWT, password hashing, tokens
│   │   ├── logging.py         # JSON/structured logging
│   │   ├── exception.py       # Custom exception classes
│   │   ├── handler.py         # Global exception handlers
│   │   ├── repository.py      # Base repository pattern
│   │   ├── schema.py          # Base Pydantic schemas
│   │   ├── websocket.py       # WebSocket base handler
│   │   ├── middlewares/       # Request/response middlewares
│   │   │   ├── security.py    # Security headers
│   │   │   ├── logging.py     # Request logging
│   │   │   ├── ratelimit.py   # Rate limiting
│   │   │   └── cache.py       # Response caching
│   │   ├── services/          # Shared services
│   │   │   ├── email_service.py   # AWS SES
│   │   │   ├── storage.py         # S3 storage
│   │   │   └── redis_service.py   # Redis operations
│   │   ├── utils/             # Utility functions
│   │   │   └── timezone.py    # Timezone inference
│   │   └── models/            # Core database models
│   │       └── user.py        # BaseUser model
│   └── modules/               # Feature modules
│       ├── auth/              # Authentication
│       │   ├── router.py      # Auth endpoints
│       │   ├── service.py     # Auth business logic
│       │   ├── schemas.py     # Request/response models
│       │   ├── dependencies.py # Auth dependencies
│       │   └── repositories/  # Refresh token repo
│       ├── users/             # User management
│       │   ├── router.py      # User endpoints (/users/me)
│       │   ├── service.py     # User business logic
│       │   ├── models.py      # User model (extends BaseUser)
│       │   ├── repository.py  # User data access
│       │   └── schemas.py     # User schemas
│       ├── chatbot/           # AI Chatbot
│       │   ├── routes.py      # Chat WebSocket endpoint
│       │   ├── models/        # Thread, Message, Summary models
│       │   ├── repositories/  # Data access layer
│       │   └── services/      # Business logic
│       │       ├── chat_service.py       # Main orchestrator
│       │       ├── agent_service.py      # AI streaming
│       │       ├── context_service.py    # Context building
│       │       └── moderation_service.py # Content safety
│       └── countries/         # Countries & Timezones
│           ├── router.py      # Countries endpoint
│           └── service.py     # Country data with timezones
├── alembic/                   # Database migrations
│   ├── env.py                # Alembic environment
│   └── versions/             # Migration files
├── pyproject.toml            # Dependencies (uv)
├── docker-compose.yml        # Docker setup
├── Dockerfile               # Application container
└── .env.example             # Environment template
```

---

## Installation

### Prerequisites
- Python 3.13+
- PostgreSQL 15+
- Redis 7+
- AWS Account (for S3 and SES) or compatible alternatives

### 1. Install uv (Python Package Manager)

**Mac/Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows:**
```bash
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 2. Clone and Install Dependencies

```bash
git clone <your-repo-url>
cd fastapi-boilerplate
uv sync
```

### 3. Environment Setup

Copy the example environment file and configure:
```bash
cp .env.example .env
```

Edit `.env` with your settings (see Environment Variables section below).

### 4. Database Setup

Create PostgreSQL database:
```bash
createdb fastapi_boilerplate
```

Run migrations:
```bash
uv run alembic upgrade head
```

### 5. Run the Application

**Development:**
```bash
uv run uvicorn api:app --reload --port 8000
```

**Production:**
```bash
uv run uvicorn api:app --host 0.0.0.0 --port 8000 --workers 4
```

**With Docker:**
```bash
docker compose up -d --build
```

Access the API:
- API: http://localhost:8000
- Swagger UI: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc

---

## Environment Variables

### Core Settings
```bash
# Application
PROJECT_NAME=FastAPI Boilerplate
ENVIRONMENT=development  # development, staging, production
SECRET_KEY=your-secret-key-min-32-chars
DEBUG_RETURN_VERIFICATION_CODE=true  # Return codes in response (dev only)

# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/dbname

# Redis
REDIS_URL=redis://localhost:6379/0

# Security
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=30
```

### Authentication
```bash
# Google OAuth
GOOGLE_CLIENT_ID=your-google-client-id

# Apple Sign-In
APPLE_BUNDLE_ID=com.yourapp.bundle
APPLE_SERVICE_ID=com.yourapp.service
```

### AWS Services
```bash
# S3 Storage
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_S3_BUCKET=your-bucket-name
AWS_REGION=us-east-1

# SES Email
AWS_SES_REGION=us-east-1
EMAIL_FROM=noreply@yourdomain.com
```

### AI Chatbot
```bash
# Google Gemini
GOOGLE_API_KEY=your-gemini-api-key
GEMINI_CHAT_MODEL=gemini-2.0-flash-exp
GEMINI_MODEL_LOW=gemini-2.0-flash-exp

# Chat Settings
CHAT_SUMMARY_TRIGGER_COUNT=50  # Messages before auto-summary
```

### API Settings
```bash
# CORS
BACKEND_CORS_ORIGINS=["http://localhost:3000"]

# Swagger Auth (production)
SWAGGER_USER=admin
SWAGGER_PASSWORD=secure-password
```

---

## Usage Examples

### Authentication

**Register with Email:**
```bash
POST /api/v1/auth/register
{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "full_name": "John Doe"
}
```

**Login:**
```bash
POST /api/v1/auth/login
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}

Response:
{
  "access_token": "eyJ...",
  "refresh_token": "...",
  "token_type": "bearer"
}
```

### User Management

**Get Profile:**
```bash
GET /api/v1/users/me
Authorization: Bearer <access_token>
```

**Update Profile:**
```bash
PATCH /api/v1/users/me
Authorization: Bearer <access_token>
{
  "full_name": "Jane Doe",
  "timezone": "America/New_York"
}
```

### AI Chatbot

**WebSocket Connection:**
```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/chat/ws?token=<jwt_token>');

// Send message
ws.send(JSON.stringify({
  type: 'send_message',
  thread_id: null,  // null for new thread
  content: 'Hello, AI!',
  upload_ids: []
}));

// Receive streaming response
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data.type, data.content);
};
```

### Response Caching

```python
from src.core.middlewares.cache import cache_response

@router.get("/countries")
@cache_response(expire=3600)  # Cache for 1 hour
async def get_countries():
    return {"countries": [...]}
```

---

## Database Migrations

### Create a New Migration
```bash
uv run alembic revision --autogenerate -m "Add new field"
```

### Apply Migrations
```bash
uv run alembic upgrade head
```

### Rollback
```bash
uv run alembic downgrade -1
```

### View History
```bash
uv run alembic history
```

---

## Deployment

### Docker Production

Build and run:
```bash
docker compose -f docker-compose.prod.yml up -d --build
```

### Environment-Specific Settings

**Production Checklist:**
- [ ] Set `ENVIRONMENT=production`
- [ ] Use strong `SECRET_KEY` (32+ characters)
- [ ] Set `DEBUG_RETURN_VERIFICATION_CODE=false`
- [ ] Configure secure `SWAGGER_USER` and `SWAGGER_PASSWORD`
- [ ] Enable HTTPS and set proper `BACKEND_CORS_ORIGINS`
- [ ] Set up proper database connection pooling
- [ ] Configure Redis persistence
- [ ] Set up log aggregation (JSON logs ready for ELK/CloudWatch)
- [ ] Enable security headers (already configured)
- [ ] Set up rate limiting thresholds
- [ ] Configure Celery workers for background tasks

### Scaling Considerations

**Horizontal Scaling:**
- Run multiple uvicorn workers: `--workers 4`
- Use load balancer (nginx, AWS ALB)
- Redis for shared session state
- PostgreSQL read replicas

**Performance:**
- Use Redis caching for read-heavy endpoints
- Enable connection pooling in SQLAlchemy
- Implement database indexes (already configured)
- Use CDN for static assets

---

## Development

### Code Style

Format code with Ruff:
```bash
uv run ruff check .
uv run ruff format .
```

### Pre-commit Hooks

Install pre-commit:
```bash
uv run pre-commit install
```

---

## Project Structure Explained

### Module Pattern
Each feature is a self-contained module with:
- `router.py` - API endpoints
- `service.py` - Business logic
- `repository.py` - Data access
- `schemas.py` - Pydantic models
- `models.py` - SQLAlchemy models (if needed)

### Repository Pattern
All database operations go through repositories:
```python
class UserRepository(BaseRepository[User]):
    async def get_by_email(self, email: str) -> User | None:
        result = await self.db.scalars(
            select(self.model).where(self.model.email == email)
        )
        return result.one_or_none()
```

### Service Layer
Business logic is separated from API routes:
```python
class UserService:
    def __init__(self, db: AsyncSession):
        self.user_repo = UserRepository(db)
    
    async def update_profile(self, user_id, update_data):
        user = await self.user_repo.get(user_id)
        return await self.user_repo.update(user, update_data)
```

---

## Security Features

- **Password Hashing**: bcrypt with SHA-256 pre-hashing
- **JWT Tokens**: HS256 algorithm with configurable expiration
- **Refresh Token Rotation**: Automatic rotation with reuse detection
- **Rate Limiting**: Redis-backed request throttling
- **Content Moderation**: AI + keyword fallback for chatbot safety
- **Security Headers**: HSTS, CSP, X-Frame-Options, etc.
- **Input Validation**: Pydantic v2 schemas
- **SQL Injection Prevention**: SQLAlchemy parameterized queries

---

## API Documentation

Once the server is running, access:
- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc
- **OpenAPI Schema**: http://localhost:8000/api/openapi.json

In production, these are protected by HTTP Basic Auth (configured via `SWAGGER_USER` and `SWAGGER_PASSWORD`).

---

## License

MIT License - feel free to use this boilerplate for your projects.

---

## Support

For issues and questions:
- Create an issue in the repository
- Contact: support@neonapps.co

---

## Credits

Built with:
- [FastAPI](https://fastapi.tiangolo.com/)
- [SQLAlchemy](https://www.sqlalchemy.org/)
- [Pydantic AI](https://ai.pydantic.dev/)
- [Google Gemini](https://ai.google.dev/)
- [uv](https://docs.astral.sh/uv/)
