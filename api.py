import secrets
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import uvicorn
from fastapi import APIRouter, Depends, FastAPI, HTTPException, status
from fastapi.middleware import Middleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from src.core.config import settings
from src.core.handler import init as init_exception_handlers
from src.core.logging import configure_logging, get_logger
from src.core.middlewares.logging import LoggingMiddleware
from src.core.middlewares.security import MaxRequestSizeMiddleware, SecurityHeadersMiddleware
from src.modules.auth.router import router as auth_router
from src.modules.chatbot.routes import docs_router as chatbot_docs_router
from src.modules.chatbot.routes import router as chatbot_router
from src.modules.countries.router import router as countries_router
from src.modules.health.router import router as health_router
from src.modules.users.router import router as users_router

configure_logging()
logger = get_logger(__name__)

security: HTTPBasic = HTTPBasic(auto_error=False)

environment: str = settings.ENVIRONMENT


def check_swagger_auth(
    credentials: HTTPBasicCredentials | None = Depends(dependency=security),
):
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": 'Basic realm="Swagger UI"'},
        )

    correct_username: bool = secrets.compare_digest(credentials.username, settings.SWAGGER_USER)
    correct_password: bool = secrets.compare_digest(credentials.password, settings.SWAGGER_PASSWORD)

    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": 'Basic realm="Swagger UI"'},
        )
    return True


middleware_list: list[Middleware] = [
    Middleware(SecurityHeadersMiddleware),  # ty:ignore[invalid-argument-type]
    Middleware(MaxRequestSizeMiddleware, max_upload_size=5 * 1024 * 1024),  # ty:ignore[invalid-argument-type]
    Middleware(LoggingMiddleware),  # ty:ignore[invalid-argument-type]
]

if settings.BACKEND_CORS_ORIGINS:
    middleware_list.insert(
        0,
        Middleware(
            CORSMiddleware,  # ty:ignore[invalid-argument-type]
            allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        ),
    )

openapi_tags = [
    {"name": "Authentication", "description": "Authentication"},
    {"name": "Users", "description": "User Management"},
    {"name": "Countries", "description": "Country and Timezone Information"},
    {
        "name": "Chatbot",
        "description": (
            "AI-powered chatbot with real-time streaming responses. "
            "Provides personalized assistance using Google Gemini AI. "
            "\n\nConnection: ws://localhost:8000/api/v1/chat/ws?token=JWT_TOKEN "
            "\n\nSupports text messages and file attachments (images, documents, video, audio). "
            "Rate limits: 10 messages/minute, 100 messages/day per user."
        ),
    },
    {"name": "Health", "description": "Health Check Endpoint"},
]


SWAGGER_UI_PARAMETERS = {
    "persistAuthorization": True,
    "showExtensions": True,
    "showCommonExtensions": True,
    "filter": True,
    "displayRequestDuration": True,
    "operationsSorter": "method",
    "tagsSorter": "alpha",
}


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    """
    Application lifespan events.

    Startup:
        - Initialize countries cache (prevents blocking I/O during validation)

    Shutdown:
        - No cleanup needed
    """
    # Startup
    logger.info("Application startup: Initializing resources...")

    from src.modules.countries.service import initialize_countries_cache

    initialize_countries_cache()
    logger.info("Countries cache initialized successfully")

    yield

    # Shutdown
    logger.info("Application shutdown: Cleaning up resources...")


def custom_openapi() -> dict[str, Any]:
    """Custom OpenAPI schema with Bearer authentication support."""
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        openapi_version=app.openapi_version,
        description=app.description,
        routes=app.routes,
        tags=app.openapi_tags,
        contact=app.contact,
        servers=app.servers,
        license_info=app.license_info,
        terms_of_service=app.terms_of_service,
    )

    # Add Bearer token security scheme
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Enter your JWT token obtained from /api/v1/auth/login or /api/v1/auth/register endpoints",
        }
    }

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API",
    version="1.0",
    middleware=middleware_list,
    openapi_tags=openapi_tags,
    swagger_ui_parameters=SWAGGER_UI_PARAMETERS,
    lifespan=lifespan,
    docs_url=None if environment == "production" else "/api/docs",
    redoc_url=None if environment == "production" else "/api/redoc",
    openapi_url=None if environment == "production" else "/api/openapi.json",
    contact={
        "name": "Baris Cem Ant",
        "url": "https://github.com/0Baris",
        "email": "bariscem@proton.me",
    },
)

# Set custom OpenAPI schema
app.openapi = custom_openapi

init_exception_handlers(app)

if environment == "production":

    @app.get(path="/api/docs", include_in_schema=False)
    async def get_swagger_documentation(
        is_authenticated: bool = Depends(dependency=check_swagger_auth),  # noqa: ARG001
    ):
        """
        Only authenticated users can access Swagger UI.
        """
        return get_swagger_ui_html(
            openapi_url=app.openapi_url or "/api/openapi.json",
            title=f"{app.title} - Swagger UI",
            oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
            swagger_ui_parameters=app.swagger_ui_parameters,
            swagger_favicon_url="https://framerusercontent.com/images/MKB39pOwGKdfFo4cuzAEjz0CpAU.png?scale-down-to=512&width=1024&height=147",
        )

    @app.get(path="/api/redoc", include_in_schema=False)
    async def get_redoc_documentation(
        is_authenticated: bool = Depends(dependency=check_swagger_auth),  # noqa: ARG001
    ):
        """
        Only authenticated users can access Redoc.
        """
        return get_redoc_html(
            openapi_url=app.openapi_url or "/api/openapi.json",
            title=f"{app.title} - ReDoc",
            redoc_js_url="https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js",
        )

    @app.get(path="/api/openapi.json", include_in_schema=False)
    async def openapi(
        is_authenticated: bool = Depends(dependency=check_swagger_auth),  # noqa: ARG001
    ):
        """
        Only authenticated users can access OpenAPI schema.
        """
        return custom_openapi()


# API v1 router
api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(router=auth_router, prefix="/auth", tags=["Authentication"])
api_v1_router.include_router(router=users_router, prefix="/users", tags=["Users"])
api_v1_router.include_router(router=countries_router, prefix="/countries", tags=["Countries"])
api_v1_router.include_router(router=chatbot_router, prefix="/chat", tags=["Chatbot"])
api_v1_router.include_router(router=chatbot_docs_router, prefix="/chat", tags=["Chatbot"])

# Include versioned API and standalone health router
app.include_router(api_v1_router)
app.include_router(router=health_router)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
