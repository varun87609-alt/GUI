"""Health and Capabilities API Endpoints."""

import shutil
from fastapi import APIRouter
from backend.app.config import settings
from backend.app.schemas import HealthResponse, CapabilitiesResponse
from backend.app.services.docker_runner import docker_runner
from backend.app.database import list_jobs
from backend.app.models import JobStatus

router = APIRouter(tags=["Health & System"])

@router.get("/health", response_model=HealthResponse)
def get_health():
    """Returns application health, Docker readiness, and storage statistics."""
    docker_ready = docker_runner.ping()
    image_ready = docker_runner.is_image_available(settings.docker_image) if docker_ready else False

    # Check disk space on workspace drive
    total, used, free = shutil.disk_usage(str(settings.workspace_path))
    disk_free_gb = round(free / (1024 ** 3), 2)

    # Active jobs count
    recent_jobs = list_jobs(limit=100)
    active_count = sum(1 for j in recent_jobs if j.status in (JobStatus.RUNNING, JobStatus.QUEUED))

    overall_status = "healthy" if (docker_ready and image_ready) else "degraded"

    return HealthResponse(
        status=overall_status,
        docker_ready=docker_ready,
        openfoam_image_ready=image_ready,
        openfoam_version="v2506",
        workspace_disk_free_gb=disk_free_gb,
        active_jobs=active_count,
        max_concurrent_jobs=settings.max_concurrent_jobs,
    )

@router.get("/capabilities", response_model=CapabilitiesResponse)
def get_capabilities():
    """Returns supported CFD meshing capabilities, workflows, and resource limits."""
    return CapabilitiesResponse(
        supported_workflows=[
            "external_flow",
            "generic_surface",
            "internal_flow",
        ],
        supported_formats=["stl_ascii", "stl_binary"],
        max_upload_size_bytes=settings.max_upload_size_bytes,
        max_triangle_count=settings.max_triangle_count,
        max_estimated_cells=settings.max_estimated_cells,
        default_timeout_seconds=settings.default_job_timeout_seconds,
        openfoam_image=settings.docker_image,
    )
