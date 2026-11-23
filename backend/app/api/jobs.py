"""Meshing Jobs API Endpoints.

Handles job creation, status polling, real-time log retrieval, cancellation,
results retrieval, and case archive downloads.
"""

import os
import re
import time
import json
import uuid
from typing import List, Optional
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.responses import FileResponse

from backend.app.config import settings
from backend.app.schemas import (
    MeshJobCreateRequest,
    JobStatusResponse,
    JobLogsResponse,
    MeshStatsResponse,
    BoundingBox,
)
from backend.app.models import JobStatus, PipelineStage, JobRecord
from backend.app.database import (
    clear_job_history,
    create_job,
    get_job,
    list_jobs,
    update_job_status,
)
from backend.app.services.job_queue import case_name_from_filename, job_queue

router = APIRouter(prefix="/jobs", tags=["Meshing Jobs"])
_LOCAL_GUI_ORIGIN = re.compile(r"https?://(?:localhost|127\.0\.0\.1|\[::1\])(?::[0-9]{1,5})?")

@router.post("/{job_id}/open-folder", status_code=status.HTTP_204_NO_CONTENT)
def open_case_folder(job_id: str, request: Request):
    """Open a saved case in Explorer on the local Windows host."""
    origin = request.headers.get("origin", "")
    fetch_site = request.headers.get("sec-fetch-site")
    if (
        not request.client
        or request.client.host not in {"127.0.0.1", "::1"}
        or not _LOCAL_GUI_ORIGIN.fullmatch(origin)
        or fetch_site not in {None, "same-origin", "same-site"}
        or (fetch_site == "same-site" and origin not in settings.allowed_origins)
        or request.headers.get("x-open-case-folder") != "1"
    ):
        raise HTTPException(
            status_code=403,
            detail="Open the GUI using localhost or 127.0.0.1, or use Copy path to open the case manually.",
        )

    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Case not found.")
    case_dir = job_queue.get_job_dir(job)
    jobs_dir = (settings.workspace_path / "jobs").resolve()
    resolved_case = case_dir.resolve()
    if not resolved_case.is_dir() or resolved_case.parent != jobs_dir:
        raise HTTPException(status_code=404, detail="Saved case folder not found.")
    if os.name != "nt":
        raise HTTPException(status_code=501, detail="Open folder requires the Windows backend. Use Copy path instead.")
    try:
        os.startfile(resolved_case, "explore")
    except OSError:
        raise HTTPException(status_code=500, detail="Could not open Explorer. Use Copy path instead.")

def to_job_status_response(job: JobRecord) -> JobStatusResponse:
    """Converts a JobRecord into a JobStatusResponse with calculated elapsed time."""
    elapsed = None
    if job.started_at:
        end_time = job.completed_at if job.completed_at else time.time()
        elapsed = round(end_time - job.started_at, 1)

    has_results = bool(job.mesh_stats_json)
    has_archive = bool(job.archive_file and Path(job.archive_file).exists())

    case_dir = job_queue.get_job_dir(job)
    return JobStatusResponse(
        job_id=job.job_id,
        upload_id=job.upload_id,
        filename=job.filename,
        workflow_type=job.workflow_type,
        status=job.status,
        stage=job.stage,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        elapsed_seconds=elapsed,
        error_message=job.error_message,
        has_results=has_results,
        has_archive=has_archive,
        case_path=str(case_dir) if case_dir.is_dir() else None,
        case_folder=job.case_folder,
        can_remesh=job.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED)
        and (case_dir / "run_mesh.sh").is_file(),
    )

@router.post("/{job_id}/remesh", response_model=JobStatusResponse, status_code=status.HTTP_202_ACCEPTED)
def remesh_job(job_id: str):
    """Run the saved meshing script again in the shared case folder."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Case not found.")
    if not to_job_status_response(job).can_remesh or not job_queue.submit_remesh(job):
        raise HTTPException(status_code=409, detail="The case is busy or its meshing script is missing.")
    return to_job_status_response(get_job(job_id))

@router.post("", response_model=JobStatusResponse, status_code=status.HTTP_201_CREATED)
def create_mesh_job(request: MeshJobCreateRequest):
    """Submits a new OpenFOAM automated meshing job."""
    # Verify upload exists
    upload_dir = settings.uploads_path / request.upload_id
    stl_path = upload_dir / "geometry.stl"
    analysis_file = upload_dir / "analysis.json"

    if not stl_path.exists() or not analysis_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Upload ID '{request.upload_id}' not found. Please upload geometry first.",
        )

    # Estimate background cell count
    estimated_base_cells = request.target_cells_x * request.target_cells_y * request.target_cells_z
    if estimated_base_cells > settings.max_estimated_cells:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Estimated background cell count ({estimated_base_cells:,}) exceeds maximum allowed "
                f"limit of {settings.max_estimated_cells:,}. Please reduce target grid resolutions."
            ),
        )

    # Load cached bounding box from analysis
    analysis_data = json.loads(analysis_file.read_text(encoding="utf-8"))
    bbox = BoundingBox(**analysis_data["bounding_box"])
    filename = analysis_data.get("filename", "geometry.stl")

    # Generate job ID and persist record
    job_id = str(uuid.uuid4())
    now = time.time()
    case_dir = job_queue.reserve_case_folder(filename)

    job_record = JobRecord(
        job_id=job_id,
        upload_id=request.upload_id,
        filename=filename,
        workflow_type=request.workflow_type,
        status=JobStatus.QUEUED,
        stage=PipelineStage.UPLOAD,
        config_json=json.dumps(request.model_dump()),
        geometry_analysis_json=json.dumps(analysis_data),
        created_at=now,
        case_folder=case_dir.name,
    )
    try:
        create_job(job_record)
    except Exception:
        case_dir.rmdir()
        raise

    # Dispatch to background queue
    job_queue.submit_job(
        job_id=job_id,
        config=request,
        bbox=bbox,
        stl_path=stl_path,
    )

    return to_job_status_response(job_record)

@router.get("", response_model=List[JobStatusResponse])
def get_jobs(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """Lists recent meshing jobs ordered by creation time."""
    records = list_jobs(limit=limit, offset=offset)
    return [to_job_status_response(j) for j in records]

@router.delete("/history")
def clear_history():
    """Remove all finished jobs from the history list."""
    return {"cleared": clear_job_history()}

@router.delete("/{job_id}/history")
def clear_history_entry(job_id: str):
    """Remove one finished job from the history list."""
    if not get_job(job_id):
        raise HTTPException(status_code=404, detail="Job not found.")
    cleared = clear_job_history(job_id)
    if not cleared and get_job(job_id).status in (JobStatus.RUNNING, JobStatus.QUEUED):
        raise HTTPException(status_code=409, detail="Wait for the job to finish before clearing it.")
    return {"cleared": cleared}

@router.get("/{job_id}", response_model=JobStatusResponse)
def get_job_by_id(job_id: str):
    """Gets current status and stage of a meshing job."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found.",
        )
    return to_job_status_response(job)

@router.get("/{job_id}/logs", response_model=JobLogsResponse)
def get_job_logs(
    job_id: str,
    offset: int = Query(default=0, ge=0, description="Line offset for incremental streaming"),
):
    """Retrieves standard output and error logs from the OpenFOAM execution."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found.",
        )

    job_dir = job_queue.get_job_dir(job)
    log_file = job_dir / "pipeline.log"

    if job.status == JobStatus.QUEUED or not log_file.exists():
        return JobLogsResponse(job_id=job_id, total_lines=0, offset=offset, lines=[])

    try:
        content = log_file.read_text(encoding="utf-8", errors="replace")
        all_lines = content.splitlines()
        total_lines = len(all_lines)
        requested_lines = all_lines[offset:]

        return JobLogsResponse(
            job_id=job_id,
            total_lines=total_lines,
            offset=offset,
            lines=requested_lines,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read logs: {str(e)}",
        )

@router.post("/{job_id}/cancel", status_code=status.HTTP_200_OK)
def cancel_job_endpoint(job_id: str):
    """Cancels a running or queued meshing job and terminates its Docker container."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found.",
        )

    if job.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
        return {"message": f"Job is already {job.status.value}."}

    if job_queue.cancel_job(job_id):
        return {"message": f"Cancellation requested for job {job_id}."}
    return {"message": f"Job {job_id} is no longer active."}

@router.get("/{job_id}/results", response_model=MeshStatsResponse)
def get_mesh_results(job_id: str):
    """Retrieves parsed checkMesh statistics, cell counts, and quality metrics."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found.",
        )

    if not job.mesh_stats_json:
        if job.status == JobStatus.FAILED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Job failed before mesh generation. Error: {job.error_message}",
            )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mesh results are not yet available for this job.",
        )

    data = json.loads(job.mesh_stats_json)
    return MeshStatsResponse(**data)

@router.get("/{job_id}/download")
def download_mesh_archive(job_id: str):
    """Downloads the complete OpenFOAM case archive (.zip) containing polyMesh and configuration."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found.",
        )

    if not job.archive_file or not Path(job.archive_file).exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Archive file not found or mesh job has not completed successfully.",
        )

    archive_path = Path(job.archive_file)
    filename = (
        archive_path.name if job.case_folder
        else f"{case_name_from_filename(job.filename)}_{job_id[:8]}.zip"
    )

    return FileResponse(
        path=str(archive_path),
        media_type="application/zip",
        filename=filename,
    )
