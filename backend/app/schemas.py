"""Pydantic Data Schemas for API Requests, Responses, and Validation."""

from typing import Optional, List, Dict, Tuple, Any
from pydantic import BaseModel, Field, model_validator
from backend.app.models import JobStatus, PipelineStage, WorkflowType

# --- Bounding Box & Geometry Analysis ---

class BoundingBox(BaseModel):
    min_x: float
    min_y: float
    min_z: float
    max_x: float
    max_y: float
    max_z: float
    dim_x: float
    dim_y: float
    dim_z: float

class GeometryAnalysisResponse(BaseModel):
    upload_id: str
    filename: str
    file_size_bytes: int
    format: str = Field(description="'ascii' or 'binary'")
    triangle_count: int
    vertex_count: int
    is_watertight: bool
    bounding_box: BoundingBox
    scale_warning: Optional[str] = None
    aspect_ratio_warning: Optional[str] = None
    recommended_units: str = "m"
    warnings: List[str] = Field(default_factory=list)

# --- Meshing Configuration Schemas ---

class DomainMargin(BaseModel):
    # Multipliers relative to bounding box dimensions, or absolute buffer
    min_x_multiplier: float = Field(default=1.5, ge=0.0, le=20.0, description="Margin on -X side relative to dim_x")
    max_x_multiplier: float = Field(default=3.0, ge=0.0, le=20.0, description="Margin on +X side (wake/downstream) relative to dim_x")
    min_y_multiplier: float = Field(default=1.5, ge=0.0, le=20.0, description="Margin on -Y side relative to dim_y")
    max_y_multiplier: float = Field(default=1.5, ge=0.0, le=20.0, description="Margin on +Y side relative to dim_y")
    min_z_multiplier: float = Field(default=1.5, ge=0.0, le=20.0, description="Margin on -Z side relative to dim_z")
    max_z_multiplier: float = Field(default=1.5, ge=0.0, le=20.0, description="Margin on +Z side relative to dim_z")

class SurfaceRefinement(BaseModel):
    min_level: int = Field(default=1, ge=0, le=8, description="Minimum surface refinement level")
    max_level: int = Field(default=2, ge=0, le=8, description="Maximum surface refinement level")

    @model_validator(mode="after")
    def validate_levels(self):
        if self.min_level > self.max_level:
            raise ValueError("min_level cannot be greater than max_level")
        return self

class FeatureRefinement(BaseModel):
    enabled: bool = Field(default=True)
    included_angle: float = Field(default=150.0, ge=1.0, le=180.0, description="Feature angle threshold (degrees)")
    level: int = Field(default=2, ge=0, le=8, description="Feature refinement level")

class BoundaryLayers(BaseModel):
    enabled: bool = Field(default=False)
    n_surface_layers: int = Field(default=2, ge=1, le=10, description="Number of prism boundary layers")
    expansion_ratio: float = Field(default=1.2, ge=1.0, le=2.5, description="Layer expansion ratio")
    final_layer_thickness: float = Field(default=0.3, ge=0.01, le=1.0, description="Relative thickness of outer layer")
    min_thickness: float = Field(default=0.1, ge=0.001, le=1.0, description="Minimum allowed layer thickness")

class MeshJobCreateRequest(BaseModel):
    upload_id: str = Field(..., description="ID returned from successful STL upload")
    workflow_type: WorkflowType = Field(default=WorkflowType.EXTERNAL_FLOW)
    
    # Background mesh resolution: target cells in primary directions or base cell size
    target_cells_x: int = Field(default=15, ge=2, le=200, description="Number of background cells in X")
    target_cells_y: int = Field(default=15, ge=2, le=200, description="Number of background cells in Y")
    target_cells_z: int = Field(default=15, ge=2, le=200, description="Number of background cells in Z")

    domain_margin: DomainMargin = Field(default_factory=DomainMargin)
    surface_refinement: SurfaceRefinement = Field(default_factory=SurfaceRefinement)
    feature_refinement: FeatureRefinement = Field(default_factory=FeatureRefinement)
    boundary_layers: BoundaryLayers = Field(default_factory=BoundaryLayers)

    # locationInMesh: optional point override. If None, automatically computed based on workflow
    location_in_mesh: Optional[Tuple[float, float, float]] = None

    # Snappy controls
    resolve_feature_angle: float = Field(default=30.0, ge=1.0, le=90.0)
    snap_iterations: int = Field(default=30, ge=5, le=100)
    
    # Quality & timeout
    max_non_ortho: float = Field(default=65.0, ge=30.0, le=85.0)
    max_skewness: float = Field(default=4.0, ge=1.0, le=20.0)
    timeout_seconds: int = Field(default=600, ge=30, le=1800)

# --- Job Response & Status Schemas ---

class JobStatusResponse(BaseModel):
    job_id: str
    upload_id: str
    filename: str
    workflow_type: WorkflowType
    status: JobStatus
    stage: PipelineStage
    created_at: float
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    elapsed_seconds: Optional[float] = None
    error_message: Optional[str] = None
    has_results: bool = False
    has_archive: bool = False
    case_path: str | None = None
    case_folder: str | None = None
    can_remesh: bool = False

class JobLogsResponse(BaseModel):
    job_id: str
    total_lines: int
    offset: int
    lines: List[str]

class MeshStatsResponse(BaseModel):
    job_id: str
    is_valid: bool
    mesh_ok: bool
    num_points: int
    num_faces: int
    num_internal_faces: int
    num_cells: int
    cell_types: Dict[str, int] = Field(default_factory=dict)
    bounding_box: Optional[BoundingBox] = None
    max_non_ortho: Optional[float] = None
    avg_non_ortho: Optional[float] = None
    max_skewness: Optional[float] = None
    max_aspect_ratio: Optional[float] = None
    total_volume: Optional[float] = None
    warnings: List[str] = Field(default_factory=list)
    raw_summary: Optional[str] = None

# --- Capabilities & Health Schemas ---

class HealthResponse(BaseModel):
    status: str
    docker_ready: bool
    openfoam_image_ready: bool
    openfoam_version: str
    workspace_disk_free_gb: float
    active_jobs: int
    max_concurrent_jobs: int

class CapabilitiesResponse(BaseModel):
    supported_workflows: List[str]
    supported_formats: List[str]
    max_upload_size_bytes: int
    max_triangle_count: int
    max_estimated_cells: int
    default_timeout_seconds: int
    openfoam_image: str
