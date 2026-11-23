"""Domain Models and State Enums."""

from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel, Field

class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class PipelineStage(str, Enum):
    UPLOAD = "upload"
    GEOMETRY_ANALYSIS = "geometry_analysis"
    DICT_GENERATION = "dict_generation"
    SURFACE_CHECK = "surface_check"
    FEATURE_EXTRACT = "feature_extract"
    BLOCK_MESH = "block_mesh"
    SNAPPY_HEX_MESH = "snappy_hex_mesh"
    CHECK_MESH = "check_mesh"
    PACKAGING = "packaging"
    COMPLETED = "completed"

class WorkflowType(str, Enum):
    EXTERNAL_FLOW = "external_flow"
    GENERIC_SURFACE = "generic_surface"
    INTERNAL_FLOW = "internal_flow"

class JobRecord(BaseModel):
    job_id: str
    upload_id: str
    filename: str
    workflow_type: WorkflowType
    status: JobStatus
    stage: PipelineStage
    config_json: str
    geometry_analysis_json: Optional[str] = None
    mesh_stats_json: Optional[str] = None
    error_message: Optional[str] = None
    created_at: float
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    container_id: Optional[str] = None
    log_file: Optional[str] = None
    archive_file: Optional[str] = None
    case_folder: Optional[str] = None
