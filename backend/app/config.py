"""Application Configuration Module.

Loads settings from environment variables or .env with secure defaults.
Computes absolute filesystem paths to ensure reliable Docker volume mounting on Windows.
"""

import os
from pathlib import Path
from pydantic import BaseModel, Field

# Determine project base directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseModel):
    # Host & Server
    app_host: str = Field(default=os.getenv("APP_HOST", "127.0.0.1"))
    app_port: int = Field(default=int(os.getenv("APP_PORT", "8000")))
    debug: bool = Field(default=os.getenv("DEBUG", "false").lower() == "true")

    # Docker & OpenFOAM
    docker_image: str = Field(default=os.getenv("DOCKER_IMAGE", "openeuler/openfoam:2506-oe2403sp4"))
    openfoam_install_dir: str = Field(default=os.getenv("OPENFOAM_INSTALL_DIR", "/opt/OpenFOAM-v2506"))

    # Storage & Workspace
    workspace_dir_name: str = Field(default=os.getenv("WORKSPACE_DIR", "workspace_jobs"))
    db_file_name: str = Field(default="jobs.db")

    # Upload & Mesh Limits
    max_upload_size_bytes: int = Field(default=int(os.getenv("MAX_UPLOAD_SIZE_BYTES", str(100 * 1024 * 1024))))  # 100 MB
    max_triangle_count: int = Field(default=int(os.getenv("MAX_TRIANGLE_COUNT", "1000000")))
    max_estimated_cells: int = Field(default=int(os.getenv("MAX_ESTIMATED_CELLS", "3000000")))
    default_job_timeout_seconds: int = Field(default=int(os.getenv("DEFAULT_JOB_TIMEOUT_SECONDS", "600")))
    max_concurrent_jobs: int = Field(default=int(os.getenv("MAX_CONCURRENT_JOBS", "2")))

    # Container limits
    container_cpu_limit: float = Field(default=float(os.getenv("CONTAINER_CPU_LIMIT", "2.0")))
    container_mem_limit: str = Field(default=os.getenv("CONTAINER_MEM_LIMIT", "4g"))

    # CORS
    allowed_origins: list[str] = Field(
        default_factory=lambda: [
            origin.strip()
            for origin in os.getenv(
                "ALLOWED_ORIGINS",
                "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8000,http://127.0.0.1:8000",
            ).split(",")
            if origin.strip()
        ]
    )

    @property
    def workspace_path(self) -> Path:
        """Returns the absolute path to the workspace jobs directory."""
        path = BASE_DIR / self.workspace_dir_name
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def uploads_path(self) -> Path:
        """Returns the absolute path to the uploads staging directory."""
        path = self.workspace_path / "uploads"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def db_path(self) -> Path:
        """Returns the absolute path to the SQLite database file."""
        return self.workspace_path / self.db_file_name


settings = Settings()
