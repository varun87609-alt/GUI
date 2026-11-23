# OpenFOAM AutoMesh - System Architecture

## 1. Overview and Design Philosophy

OpenFOAM AutoMesh is a production-quality, automated computational fluid dynamics (CFD) geometry meshing web application. It bridges the gap between raw CAD surface exports (`.stl`) and computational meshes ready for OpenFOAM solvers.

The system is designed with four core tenets:
1. **Zero Uncontrolled Shell Execution**: OpenFOAM dictionaries are serialized directly from validated, strongly-typed Pydantic schemas. User-supplied parameters never touch shell commands.
2. **Containerized Sandbox Isolation**: Meshing computations execute in short-lived, isolated Docker containers with non-root identities, memory and CPU constraints, no new privileges, and complete network isolation (`network_mode: none`).
3. **Deterministic State Machine**: Job lifecycles follow a strict state progression (`QUEUED` -> `RUNNING` -> `COMPLETED` / `FAILED` / `CANCELLED`) with persistent SQLite tracking and graceful recovery on server restarts.
4. **CFD-Centric Visual Feedback**: Interactive Three.js preview allows inspection of bounding dimensions, aspect ratios, and watertight topology before triggering expensive Docker workloads.

---

## 2. Component Architecture

```mermaid
graph TD
    Client[React + Vite Frontend (Three.js 3D Viewer)]
    API[FastAPI Backend (Port 8000)]
    DB[(SQLite Persistent Metadata jobs.db)]
    Queue[Bounded Background Job Queue (ThreadPool)]
    Docker[Docker Engine Desktop]
    Container[OpenFOAM v2506 Container Sandbox]

    Client -->|1. Upload STL & Check Health| API
    API -->|2. Validate & Analyze Geometry| Client
    Client -->|3. Submit Meshing Job| API
    API -->|4. Store Job Record| DB
    API -->|5. Enqueue Work| Queue
    Queue -->|6. Generate Dictionaries| Queue
    Queue -->|7. Launch Isolated Container| Docker
    Docker -->|8. Run blockMesh + snappyHexMesh| Container
    Container -->|9. Stream Real-Time Logs| Queue
    Queue -->|10. Parse checkMesh Output| Queue
    Queue -->|11. Package Archive & Update DB| DB
    Client -->|12. Poll Status & Stream Logs| API
    Client -->|13. Download Result Archive| API
```

### Component Responsibilities:

- **Frontend (React + Vite + TypeScript + Three.js)**:
  - Renders 3D geometry with OrbitControls, bounding-box helpers, wireframe, and dimension annotations.
  - Guided form with CFD workflow selection (External Flow, Generic Surface, Internal Flow).
  - Visual stage tracker (stepper) with live streaming terminal logs.
  - Results viewer displaying checkMesh quality metrics, cell breakdowns, and download triggers.
  - Infrastructure health and job monitor dashboard.

- **API Layer (FastAPI + Pydantic v2)**:
  - Versioned API (`/api/v1/health`, `/api/v1/capabilities`, `/api/v1/uploads`, `/api/v1/jobs`).
  - Strict input validation: file size limits (100 MB), triangle limits (1M), estimated background cell limits (3M).
  - Path traversal and arbitrary upload prevention using random UUIDs and server-controlled directory trees.
  - Security headers and CORS origin restrictions.

- **Storage & State Layer (SQLite with WAL mode)**:
  - Persistent job metadata (`jobs.db`) with Write-Ahead Logging for concurrency.
  - Automatic stale job recovery upon backend restart.

- **Execution Engine (Docker SDK + Background Job Queue)**:
  - Managed ThreadPool with bounded concurrency (default 2 simultaneous jobs).
  - Mounts only the isolated per-job working directory (`/workspace`).
  - Enforces CPU and memory limits (`mem_limit: 4g`, `cpus: 2.0`).
  - Disables container network access (`network_mode: none`).
  - Enforces hard execution timeouts and enables immediate user cancellation.

---

## 3. Directory Layout

```
c:\Desktop\GUI\
├── backend\
│   ├── app\
│   │   ├── api\
│   │   │   ├── health.py        # /health and /capabilities endpoints
│   │   │   ├── uploads.py       # /uploads validation and geometry analysis
│   │   │   └── jobs.py          # /jobs creation, status, logs, results, download
│   │   ├── services\
│   │   │   ├── geometry.py      # STL parsing, bounding box, topology checks
│   │   │   ├── dict_generator.py# OpenFOAM v2506 dictionary serializer
│   │   │   ├── docker_runner.py # Docker SDK container runner & isolation
│   │   │   ├── job_queue.py     # Background worker pool & zip packaging
│   │   │   └── mesh_parser.py   # checkMesh structured log parser
│   │   ├── config.py            # Environment configuration & absolute paths
│   │   ├── database.py          # SQLite database connection & queries
│   │   ├── models.py            # Enums and job data records
│   │   ├── schemas.py           # Pydantic request & response models
│   │   └── main.py              # FastAPI application entrypoint & middleware
│   ├── tests\
│   │   ├── test_geometry.py     # Geometry parsing and scale warning tests
│   │   ├── test_dict_generator.py # OpenFOAM dictionary generation tests
│   │   ├── test_mesh_parser.py  # checkMesh regex and metrics parser tests
│   │   ├── test_api.py          # REST API endpoint tests
│   │   └── test_integration_openfoam.py # Real Docker container meshing test
│   ├── requirements.txt         # Pinned backend dependencies
│   └── run_backend.py           # Server runner script
├── frontend\
│   ├── src\
│   │   ├── components\
│   │   │   ├── Navbar.tsx       # Header with health badge and tab switcher
│   │   │   ├── STLViewer.tsx    # Three.js 3D viewport with bounding box
│   │   │   ├── UploadZone.tsx   # Drag-and-drop upload & demo loader
│   │   │   ├── ConfigForm.tsx   # Guided meshing parameters form
│   │   │   ├── JobProgress.tsx  # Live stepper & streaming log console
│   │   │   ├── ResultsView.tsx  # Mesh validation metrics & download
│   │   │   ├── Dashboard.tsx    # Infrastructure cards & recent jobs
│   │   │   └── DocumentationView.tsx # In-app documentation
│   │   ├── services\
│   │   │   ├── api.ts           # Typed API client
│   │   │   └── api.test.ts      # Frontend API client tests
│   │   ├── types\index.ts       # TypeScript interfaces
│   │   ├── App.tsx              # Main layout
│   │   ├── index.css            # CFD dark design system
│   │   └── main.tsx             # React entrypoint
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts           # Vite config with backend proxy
├── sample_geometries\
│   └── cube.stl                 # Non-sensitive benchmark geometry
├── docs\
│   ├── ARCHITECTURE.md          # Architecture specification (this file)
│   ├── API.md                   # REST API documentation
│   ├── SECURITY.md              # Threat model & security controls
│   ├── OPENFOAM_PIPELINE.md     # OpenFOAM dictionary & meshing guide
│   └── TROUBLESHOOTING.md       # Diagnostic and recovery manual
├── scripts\
│   ├── verify_environment.ps1   # Environment verification script
│   ├── run_tests.ps1            # Automated test runner script
│   └── start_dev.ps1            # One-command startup script
├── .env.example
├── .gitignore
├── docker-compose.yml
└── README.md
```

---

## 4. Failure Handling & Resilience

1. **Backend Crash Recovery**: On startup, `recover_stale_jobs()` identifies any jobs left in `QUEUED` or `RUNNING` state from an unexpected termination and updates them to `FAILED` with an informative error message.
2. **Container Cleanup**: Containers are assigned unique names, and `try...finally` blocks guarantee `container.remove(force=True)` runs whether the job completes, fails, or is cancelled.
3. **Execution Timeouts**: `docker_runner.py` monitors elapsed time against the user-configured `timeout_seconds`. If exceeded, `container.kill()` is invoked and the job is marked `FAILED (Timeout)`.
4. **Immediate Cancellation**: When a user cancels a job via `POST /api/v1/jobs/{job_id}/cancel`, an atomic flag is set in memory, the active Docker container is terminated immediately, and resources are reclaimed.
