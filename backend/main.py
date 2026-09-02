from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from contextlib import asynccontextmanager
import os
import sys
import logging
import time
from typing import Dict

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.config import settings
from backend.api.users import router as users_router
from backend.api.risk import router as risk_router
from backend.api.payments import router as payments_router
from backend.api.dashboard import router as dashboard_router
from backend.api.copilot import router as copilot_router
from backend.db import init_db

# Configure logging
logging.basicConfig(level=getattr(logging, settings.log_level.upper()))
logger = logging.getLogger(__name__)


# Simple in-memory rate limiter (for development; use Redis in production)
class RateLimiter:
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, list] = {}

    def is_allowed(self, client_ip: str) -> bool:
        now = time.time()
        if client_ip not in self.requests:
            self.requests[client_ip] = []
        
        # Clean old requests
        self.requests[client_ip] = [
            req_time for req_time in self.requests[client_ip]
            if now - req_time < self.window_seconds
        ]
        
        if len(self.requests[client_ip]) >= self.max_requests:
            return False
        
        self.requests[client_ip].append(now)
        return True


rate_limiter = RateLimiter(max_requests=200, window_seconds=60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    logger.info("TrustBridge API started")
    yield
    # Shutdown (if needed)
    logger.info("TrustBridge API shutting down")


app = FastAPI(
    title="TrustBridge API",
    description="Trust & Risk Intelligence Platform API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# CORS configuration - use environment variable in production
if settings.is_production:
    allow_origins = settings.cors_origins_list
else:
    allow_origins = settings.cors_origins_list

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Request size limit middleware
@app.middleware("http")
async def limit_request_size(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > 1_000_000:  # 1MB limit
        return JSONResponse(
            status_code=413,
            content={"error": "Request payload too large", "code": "PAYLOAD_TOO_LARGE"}
        )
    return await call_next(request)

# Rate limiting middleware (skip for health checks)
@app.middleware("http")
async def rate_limit(request: Request, call_next):
    if request.url.path in ["/api/health", "/"]:
        return await call_next(request)
    
    client_ip = request.client.host if request.client else "unknown"
    if not rate_limiter.is_allowed(client_ip):
        return JSONResponse(
            status_code=429,
            content={"error": "Rate limit exceeded", "code": "RATE_LIMIT_EXCEEDED"}
        )
    return await call_next(request)

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    logger.info(f"{request.method} {request.url.path} - {response.status_code} - {process_time:.3f}s")
    return response


# Global exception handlers for safe error responses
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    logger.warning(f"HTTP {exc.status_code}: {exc.detail} - {request.url.path}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "code": f"HTTP_{exc.status_code}"}
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(f"Validation error: {exc.errors()} - {request.url.path}")
    return JSONResponse(
        status_code=422,
        content={"error": "Invalid request parameters", "code": "VALIDATION_ERROR", "details": exc.errors()}
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {type(exc).__name__}: {exc}", exc_info=settings.debug)
    # Never expose internal error details in production
    if settings.is_production:
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error", "code": "INTERNAL_ERROR"}
        )
    else:
        return JSONResponse(
            status_code=500,
            content={"error": str(exc), "code": "INTERNAL_ERROR", "type": type(exc).__name__}
        )


# Include API routers
app.include_router(dashboard_router, prefix="/api")
app.include_router(users_router, prefix="/api")
app.include_router(risk_router, prefix="/api")
app.include_router(payments_router, prefix="/api")
app.include_router(copilot_router, prefix="/api")


@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "TrustBridge API",
        "version": "1.0.0",
        "environment": settings.app_env,
        "ai_configured": settings.ai_configured,
    }


@app.get("/")
async def root():
    return {
        "service": "TrustBridge API",
        "version": "1.0.0",
        "docs": "/docs" if settings.debug else "disabled",
        "redoc": "/redoc" if settings.debug else "disabled",
    }