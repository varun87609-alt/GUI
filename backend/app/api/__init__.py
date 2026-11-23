"""API Package."""
from backend.app.api.health import router as health_router
from backend.app.api.uploads import router as uploads_router
from backend.app.api.jobs import router as jobs_router

__all__ = ["health_router", "uploads_router", "jobs_router"]
