"""Main FastAPI Application Entrypoint.

Configures versioned routing (/api/v1), CORS allowlists, security headers,
database lifecycle management, and structured error handling.
"""

from contextlib import asynccontextmanager
import logging
import time
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from backend.app.config import settings
from backend.app.database import init_db, recover_stale_jobs
from backend.app.api.health import router as health_router
from backend.app.api.uploads import router as uploads_router
from backend.app.api.jobs import router as jobs_router

# Configure structured logging
logging.basicConfig(
    level=logging.INFO if not settings.debug else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("openfoam_api")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan handler for startup and shutdown actions."""
    logger.info("Initializing OpenFOAM Meshing Service...")
    init_db()
    recovered = recover_stale_jobs()
    if recovered > 0:
        logger.warning("Recovered and finalized %d stale jobs from previous run.", recovered)
    logger.info("Service initialized. Ready to accept meshing requests.")
    yield
    logger.info("Shutting down OpenFOAM Meshing Service...")

app = FastAPI(
    title="OpenFOAM Automated STL Meshing API",
    description="Production-quality REST API for automated STL geometry validation and OpenFOAM snappyHexMesh generation.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# --- Security Headers Middleware ---
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

app.add_middleware(SecurityHeadersMiddleware)

# --- CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# --- Versioned API Router ---
api_v1_prefix = "/api/v1"
app.include_router(health_router, prefix=api_v1_prefix)
app.include_router(uploads_router, prefix=api_v1_prefix)
app.include_router(jobs_router, prefix=api_v1_prefix)

# Root convenience redirect/status
@app.get("/")
def root():
    return {
        "service": "OpenFOAM Automated Meshing Service",
        "version": "1.0.0",
        "status": "online",
        "api_v1": "/api/v1",
    }

# --- Global Exception Handler (Prevents Internal Traceback Leakage) ---
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception processing %s %s: %s", request.method, request.url.path, str(exc), exc_info=settings.debug)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "InternalServerError",
            "message": "An unexpected server error occurred while processing your request.",
        },
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host=settings.app_host, port=settings.app_port, reload=settings.debug)
