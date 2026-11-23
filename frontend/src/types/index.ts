export type WorkflowType = "external_flow" | "generic_surface" | "internal_flow";

export type JobStatus = "queued" | "running" | "completed" | "failed" | "cancelled";

export type PipelineStage =
  | "upload"
  | "geometry_analysis"
  | "dict_generation"
  | "surface_check"
  | "feature_extract"
  | "block_mesh"
  | "snappy_hex_mesh"
  | "check_mesh"
  | "packaging"
  | "completed";

export interface BoundingBox {
  min_x: number;
  min_y: number;
  min_z: number;
  max_x: number;
  max_y: number;
  max_z: number;
  dim_x: number;
  dim_y: number;
  dim_z: number;
}

export interface GeometryAnalysis {
  upload_id: string;
  filename: string;
  file_size_bytes: number;
  format: "ascii" | "binary";
  triangle_count: number;
  vertex_count: number;
  is_watertight: boolean;
  bounding_box: BoundingBox;
  scale_warning?: string | null;
  aspect_ratio_warning?: string | null;
  recommended_units: string;
  warnings: string[];
}

export interface DomainMargin {
  min_x_multiplier: number;
  max_x_multiplier: number;
  min_y_multiplier: number;
  max_y_multiplier: number;
  min_z_multiplier: number;
  max_z_multiplier: number;
}

export interface SurfaceRefinement {
  min_level: number;
  max_level: number;
}

export interface FeatureRefinement {
  enabled: boolean;
  included_angle: number;
  level: number;
}

export interface BoundaryLayers {
  enabled: boolean;
  n_surface_layers: number;
  expansion_ratio: number;
  final_layer_thickness: number;
  min_thickness: number;
}

export interface MeshJobCreateRequest {
  upload_id: string;
  workflow_type: WorkflowType;
  target_cells_x: number;
  target_cells_y: number;
  target_cells_z: number;
  domain_margin: DomainMargin;
  surface_refinement: SurfaceRefinement;
  feature_refinement: FeatureRefinement;
  boundary_layers: BoundaryLayers;
  location_in_mesh?: [number, number, number] | null;
  resolve_feature_angle?: number;
  snap_iterations?: number;
  max_non_ortho?: number;
  max_skewness?: number;
  timeout_seconds: number;
}

export interface JobStatusResponse {
  job_id: string;
  upload_id: string;
  filename: string;
  workflow_type: WorkflowType;
  status: JobStatus;
  stage: PipelineStage;
  created_at: number;
  started_at?: number | null;
  completed_at?: number | null;
  elapsed_seconds?: number | null;
  error_message?: string | null;
  has_results: boolean;
  has_archive: boolean;
  case_path: string | null;
  case_folder: string | null;
  can_remesh: boolean;
}

export interface JobLogsResponse {
  job_id: string;
  total_lines: number;
  offset: number;
  lines: string[];
}

export interface MeshStatsResponse {
  job_id: string;
  is_valid: boolean;
  mesh_ok: boolean;
  num_points: number;
  num_faces: number;
  num_internal_faces: number;
  num_cells: number;
  cell_types: Record<string, number>;
  bounding_box?: BoundingBox | null;
  max_non_ortho?: number | null;
  avg_non_ortho?: number | null;
  max_skewness?: number | null;
  max_aspect_ratio?: number | null;
  total_volume?: number | null;
  warnings: string[];
  raw_summary?: string | null;
}

export interface HealthResponse {
  status: string;
  docker_ready: boolean;
  openfoam_image_ready: boolean;
  openfoam_version: string;
  workspace_disk_free_gb: number;
  active_jobs: number;
  max_concurrent_jobs: number;
}

export interface CapabilitiesResponse {
  supported_workflows: string[];
  supported_formats: string[];
  max_upload_size_bytes: number;
  max_triangle_count: number;
  max_estimated_cells: number;
  default_timeout_seconds: number;
  openfoam_image: string;
}
