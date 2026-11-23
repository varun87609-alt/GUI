# OpenFOAM AutoMesh - REST API Specification

All endpoints are versioned under `/api/v1`.

---

## 1. Health & Capabilities

### `GET /api/v1/health`
Checks application readiness, Docker daemon connectivity, OpenFOAM image presence, and workspace disk space.

**Response `200 OK`**:
```json
{
  "status": "healthy",
  "docker_ready": true,
  "openfoam_image_ready": true,
  "openfoam_version": "v2506",
  "workspace_disk_free_gb": 31.84,
  "active_jobs": 0,
  "max_concurrent_jobs": 2
}
```

### `GET /api/v1/capabilities`
Returns supported CFD meshing capabilities, workflows, and resource limits.

**Response `200 OK`**:
```json
{
  "supported_workflows": ["external_flow", "generic_surface", "internal_flow"],
  "supported_formats": ["stl_ascii", "stl_binary"],
  "max_upload_size_bytes": 104857600,
  "max_triangle_count": 1000000,
  "max_estimated_cells": 3000000,
  "default_timeout_seconds": 600,
  "openfoam_image": "openeuler/openfoam:2506-oe2403sp4"
}
```

---

## 2. Geometry Upload & Analysis

### `POST /api/v1/uploads`
Accepts a multipart file upload of an STL geometry file. Validates structure, computes bounding box dimensions, and performs topology and scale sanity checks.

**Request**: Multipart form data with field `file` containing `.stl` file.

**Response `201 Created`**:
```json
{
  "upload_id": "4b684cb3-00f3-42e1-872f-50d4ad64a13d",
  "filename": "cube.stl",
  "file_size_bytes": 1509,
  "format": "ascii",
  "triangle_count": 12,
  "vertex_count": 8,
  "is_watertight": true,
  "bounding_box": {
    "min_x": -0.2,
    "min_y": -0.2,
    "min_z": -0.2,
    "max_x": 0.2,
    "max_y": 0.2,
    "max_z": 0.2,
    "dim_x": 0.4,
    "dim_y": 0.4,
    "dim_z": 0.4
  },
  "scale_warning": null,
  "aspect_ratio_warning": null,
  "recommended_units": "m",
  "warnings": []
}
```

**Errors**:
- `400 Bad Request`: Invalid file extension (not `.stl`).
- `413 Payload Too Large`: Upload exceeds size limit (100 MB).
- `422 Unprocessable Content`: Corrupt STL, non-finite coordinates (NaN/Inf), or empty file.

### `GET /api/v1/uploads/{upload_id}`
Retrieves cached geometry analysis for an uploaded file.

**Response `200 OK`**: Same schema as `POST /api/v1/uploads`.

---

## 3. Meshing Jobs

### `POST /api/v1/jobs`
Submits a new automated OpenFOAM meshing job.

**Request Body (`application/json`)**:
```json
{
  "upload_id": "4b684cb3-00f3-42e1-872f-50d4ad64a13d",
  "workflow_type": "external_flow",
  "target_cells_x": 15,
  "target_cells_y": 15,
  "target_cells_z": 15,
  "domain_margin": {
    "min_x_multiplier": 1.5,
    "max_x_multiplier": 3.0,
    "min_y_multiplier": 1.5,
    "max_y_multiplier": 1.5,
    "min_z_multiplier": 1.5,
    "max_z_multiplier": 1.5
  },
  "surface_refinement": {
    "min_level": 1,
    "max_level": 2
  },
  "feature_refinement": {
    "enabled": true,
    "included_angle": 150.0,
    "level": 2
  },
  "boundary_layers": {
    "enabled": false,
    "n_surface_layers": 2,
    "expansion_ratio": 1.2,
    "final_layer_thickness": 0.3,
    "min_thickness": 0.05
  },
  "timeout_seconds": 600,
  "max_non_ortho": 65.0
}
```

**Response `201 Created`**:
```json
{
  "job_id": "2d1a3c74-ef29-45d2-9988-1a2b3c4d5e6f",
  "upload_id": "4b684cb3-00f3-42e1-872f-50d4ad64a13d",
  "filename": "cube.stl",
  "workflow_type": "external_flow",
  "status": "queued",
  "stage": "upload",
  "created_at": 1792837880.12,
  "started_at": null,
  "completed_at": null,
  "elapsed_seconds": null,
  "error_message": null,
  "has_results": false,
  "has_archive": false
}
```

**Errors**:
- `404 Not Found`: Upload ID does not exist.
- `422 Unprocessable Content`: Estimated background cell count exceeds 3,000,000 limit.

### `GET /api/v1/jobs`
Lists recent meshing jobs ordered by creation timestamp descending.

**Query Parameters**:
- `limit` (int, default: 50, max: 100)
- `offset` (int, default: 0)

**Response `200 OK`**: Array of `JobStatusResponse` objects.

### `GET /api/v1/jobs/{job_id}`
Returns current status, active pipeline stage, and elapsed time for a job.

**Response `200 OK`**: `JobStatusResponse` object.

### `GET /api/v1/jobs/{job_id}/logs`
Retrieves live streaming terminal output from the job execution container.

**Query Parameters**:
- `offset` (int, default: 0): Line offset for incremental polling.

**Response `200 OK`**:
```json
{
  "job_id": "2d1a3c74-ef29-45d2-9988-1a2b3c4d5e6f",
  "total_lines": 342,
  "offset": 0,
  "lines": [
    "=== STAGE: surfaceCheck ===",
    "Reading surface from constant/triSurface/geometry.stl...",
    "Surface is closed.",
    "=== STAGE: blockMesh ===",
    "Mesh Information: boundingBox: (-0.8 -0.8 -0.8) (1.4 0.8 0.8)",
    "=== STAGE: snappyHexMesh ===",
    "Refining mesh...",
    "=== STAGE: checkMesh ===",
    "Mesh OK.",
    "=== ALL COMPLETE ==="
  ]
}
```

### `POST /api/v1/jobs/{job_id}/cancel`
Immediately signals cancellation for a running or queued job and stops its Docker container.

**Response `200 OK`**:
```json
{
  "message": "Job 2d1a3c74-ef29-45d2-9988-1a2b3c4d5e6f cancelled."
}
```

### `GET /api/v1/jobs/{job_id}/results`
Retrieves parsed mesh quality metrics and `checkMesh` validation details.

**Response `200 OK`**:
```json
{
  "job_id": "2d1a3c74-ef29-45d2-9988-1a2b3c4d5e6f",
  "is_valid": true,
  "mesh_ok": true,
  "num_points": 9902,
  "num_faces": 24676,
  "num_internal_faces": 22302,
  "num_cells": 7432,
  "cell_types": {
    "hexahedra": 6386,
    "prisms": 24,
    "polyhedra": 1022
  },
  "bounding_box": {
    "min_x": -0.8,
    "min_y": -0.8,
    "min_z": -0.8,
    "max_x": 1.4,
    "max_y": 0.8,
    "max_z": 0.8,
    "dim_x": 2.2,
    "dim_y": 1.6,
    "dim_z": 1.6
  },
  "max_non_ortho": 41.6,
  "avg_non_ortho": 14.2,
  "max_skewness": 2.35,
  "max_aspect_ratio": 4.26,
  "total_volume": 5.568,
  "warnings": [],
  "raw_summary": "..."
}
```

### `GET /api/v1/jobs/{job_id}/download`
Downloads the complete OpenFOAM case package archive as a `.zip` file. Contains `constant/polyMesh/`, `system/` dictionaries, and logs.

**Response `200 OK`**: Binary stream (`application/zip`) with a download filename based on the uploaded STL and case name.
