"""Docker Execution Service for OpenFOAM Jobs.

Launches isolated containers with strict resource limits, security profiles,
real-time log collection, stage tracking, cancellation, and timeout enforcement.
"""

import time
import threading
from pathlib import Path
from typing import Optional, Callable, Dict, Any
import docker
from docker.errors import DockerException, NotFound, APIError

from backend.app.config import settings
from backend.app.models import PipelineStage

class DockerRunnerError(Exception):
    """Raised when container orchestration fails."""
    pass

class DockerRunner:
    def __init__(self):
        self._client: Optional[docker.DockerClient] = None
        self._lock = threading.Lock()

    def get_client(self) -> docker.DockerClient:
        """Lazily initializes and returns the Docker client."""
        with self._lock:
            if self._client is None:
                try:
                    self._client = docker.from_env()
                except Exception as e:
                    raise DockerRunnerError(f"Failed to connect to Docker daemon: {str(e)}")
            return self._client

    def ping(self) -> bool:
        """Pings Docker daemon."""
        try:
            return bool(self.get_client().ping())
        except Exception:
            return False

    def is_image_available(self, image_name: str) -> bool:
        """Checks if the required OpenFOAM Docker image is available locally."""
        try:
            client = self.get_client()
            client.images.get(image_name)
            return True
        except Exception:
            return False

    def run_mesh_job(
        self,
        job_dir: Path,
        log_file_path: Path,
        timeout_seconds: int = 600,
        on_stage_change: Optional[Callable[[PipelineStage], None]] = None,
        on_container_started: Optional[Callable[[str], None]] = None,
        is_cancelled: Optional[Callable[[], bool]] = None,
    ) -> Dict[str, Any]:
        """Runs the meshing job inside an isolated Docker container."""
        client = self.get_client()
        job_dir_abs = str(job_dir.resolve())
        log_file_path.parent.mkdir(parents=True, exist_ok=True)

        # Open log file for streaming
        log_file = open(log_file_path, "w", encoding="utf-8", errors="replace")

        container = None
        start_time = time.time()
        container_id = None

        try:
            # Map stages to console markers
            stage_markers = {
                "=== STAGE: surfaceCheck ===": PipelineStage.SURFACE_CHECK,
                "=== STAGE: surfaceFeatureExtract ===": PipelineStage.FEATURE_EXTRACT,
                "=== STAGE: blockMesh ===": PipelineStage.BLOCK_MESH,
                "=== STAGE: snappyHexMesh ===": PipelineStage.SNAPPY_HEX_MESH,
                "=== STAGE: checkMesh ===": PipelineStage.CHECK_MESH,
                "=== ALL COMPLETE ===": PipelineStage.PACKAGING,
            }

            # Security options: no new privileges, restricted network
            container = client.containers.run(
                image=settings.docker_image,
                entrypoint="/bin/bash",
                command=["/workspace/run_mesh.sh"],
                volumes={job_dir_abs: {"bind": "/workspace", "mode": "rw"}},
                working_dir="/workspace",
                nano_cpus=int(settings.container_cpu_limit * 1e9),
                mem_limit=settings.container_mem_limit,
                security_opt=["no-new-privileges:true"],
                network_mode="none",  # complete network isolation
                detach=True,
                stdout=True,
                stderr=True,
                remove=False,
            )

            container_id = container.id
            if on_container_started:
                on_container_started(container_id)

            # Stream logs in real time
            for chunk in container.logs(stream=True, follow=True):
                # Check for cancellation
                if is_cancelled and is_cancelled():
                    log_file.write("\n[JOB CANCELLED BY USER]\n")
                    log_file.flush()
                    try:
                        container.kill()
                    except Exception:
                        pass
                    raise DockerRunnerError("Job was cancelled by user.")

                # Check for timeout
                elapsed = time.time() - start_time
                if elapsed > timeout_seconds:
                    log_file.write(f"\n[JOB TIMEOUT AFTER {elapsed:.1f}s]\n")
                    log_file.flush()
                    try:
                        container.kill()
                    except Exception:
                        pass
                    raise DockerRunnerError(f"Job execution exceeded timeout of {timeout_seconds}s.")

                text = chunk.decode("utf-8", errors="replace")
                log_file.write(text)
                log_file.flush()

                # Detect stage transitions
                if on_stage_change:
                    for marker, stage in stage_markers.items():
                        if marker in text:
                            on_stage_change(stage)

            # Wait for container termination
            result = container.wait(timeout=10)
            exit_code = result.get("StatusCode", -1)

            if exit_code != 0:
                raise DockerRunnerError(
                    f"OpenFOAM pipeline exited with non-zero exit code: {exit_code}. See logs for details."
                )

            return {
                "exit_code": exit_code,
                "duration_seconds": time.time() - start_time,
                "container_id": container_id,
            }

        finally:
            log_file.close()
            if container:
                try:
                    container.remove(v=True, force=True)
                except Exception:
                    pass

    def stop_container(self, container_id: str) -> bool:
        """Safely stops and removes a running container by ID."""
        try:
            client = self.get_client()
            container = client.containers.get(container_id)
            container.kill()
            container.remove(v=True, force=True)
            return True
        except Exception:
            return False

docker_runner = DockerRunner()
