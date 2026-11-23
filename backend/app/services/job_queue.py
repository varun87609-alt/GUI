"""Background Job Queue and Lifecycle Management.

Coordinates thread-pool job execution, state transitions, packaging of results,
and cancellation handling without blocking HTTP workers.
"""

import json
import re
import shutil
import time
import zipfile
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from itertools import count
from pathlib import Path
from typing import Dict, Any, Optional

from backend.app.config import settings
from backend.app.models import JobStatus, PipelineStage, JobRecord
from backend.app.schemas import MeshJobCreateRequest, BoundingBox
from backend.app.database import (
    get_job,
    queue_remesh,
    update_job_status,
)
from backend.app.services.dict_generator import write_case_files
from backend.app.services.docker_runner import docker_runner, DockerRunnerError
from backend.app.services.mesh_parser import parse_check_mesh_log

def case_name_from_filename(filename: str) -> str:
    """Return a readable folder name that is valid on Windows."""
    name = Path(filename.replace("\\", "/")).stem
    name = re.sub(r"[^\w-]+", "_", name)[:72].strip("_-") or "case"
    if re.fullmatch(r"CON|PRN|AUX|NUL|COM[0-9¹²³]|LPT[0-9¹²³]", name, re.IGNORECASE):
        return f"{name}_case"
    return name


class JobQueueManager:
    def __init__(self):
        self.executor = ThreadPoolExecutor(
            max_workers=settings.max_concurrent_jobs,
            thread_name_prefix="mesh_worker",
        )
        self._cancellation_flags: Dict[str, bool] = {}
        self._active_containers: Dict[str, str] = {}
        self._lock = threading.Lock()

    def get_job_dir(self, job: JobRecord) -> Path:
        """Returns the isolated working directory for a given job."""
        return settings.workspace_path / "jobs" / (job.case_folder or job.job_id)

    def reserve_case_folder(self, filename: str) -> Path:
        """Reserve a unique folder even when equally named jobs arrive together."""
        jobs_dir = settings.workspace_path / "jobs"
        jobs_dir.mkdir(exist_ok=True)
        name = case_name_from_filename(filename)
        folder = jobs_dir / name
        try:
            folder.mkdir()
            return folder
        except FileExistsError:
            timestamped_name = f"{name}_{datetime.now():%Y-%m-%d_%H-%M-%S}"
            for attempt in count(1):
                suffix = f"_{attempt}" if attempt > 1 else ""
                folder = jobs_dir / f"{timestamped_name}{suffix}"
                try:
                    folder.mkdir()
                    return folder
                except FileExistsError:
                    continue

    def submit_remesh(self, job: JobRecord) -> bool:
        """Queue a run of the dictionaries already saved in the shared case."""
        config = MeshJobCreateRequest.model_validate_json(job.config_json)
        with self._lock:
            if job.job_id in self._cancellation_flags or not queue_remesh(job.job_id):
                return False
            self._cancellation_flags[job.job_id] = False
            self.executor.submit(self._execute_job, job.job_id, config)
            return True

    def is_cancelled(self, job_id: str) -> bool:
        """Checks if a job has received a cancellation request."""
        with self._lock:
            return self._cancellation_flags.get(job_id, False)

    def cancel_job(self, job_id: str) -> bool:
        """Flags a job for cancellation and terminates its container if running."""
        with self._lock:
            job = get_job(job_id)
            if job_id not in self._cancellation_flags or not job or job.status not in (
                JobStatus.QUEUED, JobStatus.RUNNING
            ):
                return False
            self._cancellation_flags[job_id] = True
            container_id = self._active_containers.get(job_id)

        if container_id:
            docker_runner.stop_container(container_id)

        return True

    def submit_job(
        self,
        job_id: str,
        config: MeshJobCreateRequest,
        bbox: BoundingBox,
        stl_path: Path,
    ) -> None:
        """Enqueues a new meshing job into the background executor."""
        with self._lock:
            self._cancellation_flags[job_id] = False

        self.executor.submit(
            self._execute_job, job_id, config, bbox, stl_path
        )

    def _execute_job(
        self,
        job_id: str,
        config: MeshJobCreateRequest,
        bbox: Optional[BoundingBox] = None,
        stl_path: Optional[Path] = None,
    ) -> None:
        """Worker thread entrypoint that executes the full meshing pipeline."""
        job = get_job(job_id)
        job_dir = self.get_job_dir(job)
        log_file = job_dir / "pipeline.log"
        archive_name = job.case_folder or f"{case_name_from_filename(job.filename)}_{job_id[:8]}"
        archive_file = job_dir / f"{archive_name}.zip"
        pending_archive = archive_file.with_suffix(".zip.tmp")
        mesh_dir = job_dir / "constant" / "polyMesh"
        backup_mesh = job_dir / ".previous-polyMesh"

        try:
            if self.is_cancelled(job_id):
                raise DockerRunnerError("Job cancelled before start.")

            job_dir.mkdir(parents=True, exist_ok=True)
            log_file.write_text("", encoding="utf-8")
            update_job_status(
                job_id=job_id,
                status=JobStatus.RUNNING,
                stage=PipelineStage.DICT_GENERATION if bbox is not None else PipelineStage.UPLOAD,
                started_at=time.time(),
                log_file=str(log_file),
            )

            if bbox is not None and stl_path is not None:
                write_case_files(job_dir, stl_path, config, bbox)
            else:
                (job_dir / "0").mkdir(exist_ok=True)
                if not backup_mesh.exists() and mesh_dir.is_dir():
                    mesh_dir.rename(backup_mesh)

            # Callbacks for Docker Runner
            def on_stage_change(stage: PipelineStage):
                update_job_status(job_id=job_id, status=JobStatus.RUNNING, stage=stage)

            def on_container_started(cid: str):
                with self._lock:
                    self._active_containers[job_id] = cid
                update_job_status(job_id=job_id, status=JobStatus.RUNNING, container_id=cid)

            # Stage 2: Execute OpenFOAM pipeline inside Docker container
            docker_runner.run_mesh_job(
                job_dir=job_dir,
                log_file_path=log_file,
                timeout_seconds=config.timeout_seconds,
                on_stage_change=on_stage_change,
                on_container_started=on_container_started,
                is_cancelled=lambda: self.is_cancelled(job_id),
            )

            # Stage 3: Packaging & Parsing results
            update_job_status(
                job_id=job_id,
                status=JobStatus.RUNNING,
                stage=PipelineStage.PACKAGING,
            )

            # Parse checkMesh output from log
            log_content = log_file.read_text(encoding="utf-8", errors="replace")
            mesh_stats = parse_check_mesh_log(job_id, log_content)

            # Package result case files into a zip archive
            self._create_case_archive(job_dir, pending_archive, mesh_stats.model_dump())
            with self._lock:
                if self._cancellation_flags[job_id]:
                    raise DockerRunnerError("Cancelled by user.")
                pending_archive.replace(archive_file)
                update_job_status(
                    job_id=job_id,
                    status=JobStatus.COMPLETED,
                    stage=PipelineStage.COMPLETED,
                    completed_at=time.time(),
                    archive_file=str(archive_file),
                    mesh_stats_json=json.dumps(mesh_stats.model_dump()),
                )
            shutil.rmtree(backup_mesh, ignore_errors=True)
        except Exception as e:
            message = str(e)
            try:
                pending_archive.unlink(missing_ok=True)
                if backup_mesh.exists():
                    if mesh_dir.exists():
                        shutil.rmtree(mesh_dir)
                    backup_mesh.rename(mesh_dir)
            except OSError as restore_error:
                message += f" Case cleanup failed: {restore_error}"
            update_job_status(
                job_id=job_id,
                status=JobStatus.CANCELLED if self.is_cancelled(job_id) else JobStatus.FAILED,
                error_message=message,
                completed_at=time.time(),
            )
        finally:
            with self._lock:
                self._active_containers.pop(job_id, None)
                self._cancellation_flags.pop(job_id, None)

    def _create_case_archive(
        self, job_dir: Path, archive_path: Path, mesh_stats: Dict[str, Any]
    ) -> None:
        """Packages the meshing case and logs into a downloadable zip file."""
        with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for case_folder in ("0", "constant", "system"):
                case_path = job_dir / case_folder
                if case_path.is_dir():
                    zf.write(case_path, arcname=case_folder)
                    for path in sorted(case_path.rglob("*")):
                        if not path.is_symlink():
                            zf.write(path, arcname=path.relative_to(job_dir).as_posix())

            zf.write(job_dir / "run_mesh.sh", arcname="run_mesh.sh")

            # Include logs
            log_path = job_dir / "pipeline.log"
            if log_path.exists():
                zf.write(log_path, arcname="pipeline.log")

            # Include summary metadata
            summary_content = json.dumps(mesh_stats, indent=2)
            zf.writestr("mesh_summary.json", summary_content)

job_queue = JobQueueManager()
