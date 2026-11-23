# OpenFOAM AutoMesh

OpenFOAM AutoMesh is a local web app that converts ASCII or binary STL geometry into an OpenFOAM v2506 mesh. Upload an STL, inspect its dimensions and surface in a 3D preview, and configure a background grid, surface refinement, and optional boundary layers. The app supports external flow, internal flow, and general surface-conforming meshing. After the run, review the `checkMesh` report and download the OpenFOAM case as a ZIP archive.

The React, TypeScript, and Three.js frontend calls a FastAPI backend. The backend validates uploads, generates OpenFOAM dictionaries, tracks jobs in SQLite, and runs `surfaceCheck`, `surfaceFeatureExtract`, `blockMesh`, `snappyHexMesh`, and `checkMesh` in a Docker container.

## Run locally on Windows

Install Python 3.12, Node.js 22.12 or later within the Node 22 release line (or Node 24 LTS), and Docker Desktop with its WSL 2 backend and Linux containers enabled. Obtain a copy of this project and open PowerShell in the folder containing this README.

### 1. Prepare Docker

Start Docker Desktop and wait for the engine to be ready. In PowerShell, run:

```powershell
docker info --format '{{.OSType}}'
docker pull openeuler/openfoam:2506-oe2403sp4
```

The first command should print `linux`. Docker is required to generate meshes.

### 2. Install dependencies

From the project root:

```powershell
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r backend/requirements.txt
npm.cmd --prefix frontend ci
```

### 3. Start both servers

In the first PowerShell terminal, from the project root:

```powershell
.\venv\Scripts\python.exe backend/run_backend.py
```

In a second PowerShell terminal, from the project root:

```powershell
npm.cmd --prefix frontend run dev
```

Open <http://127.0.0.1:5173>. The frontend proxies `/api` requests to the backend at `http://127.0.0.1:8000`. To check that both Docker and the image are ready, query the backend:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health
```

For meshing, both `docker_ready` and `openfoam_image_ready` should be `True`. If Docker is unreachable, check Docker Desktop and rerun `docker info` in the same account that starts the backend. If the image is missing, rerun `docker pull`. The supplied Compose file refers to missing Dockerfiles, so use the two-terminal startup above.

### 4. Mesh the sample cube

1. Select **Use sample cube** or upload [sample_geometries/cube.stl](sample_geometries/cube.stl).
2. Inspect the STL in the 3D preview. Select the external-flow workflow and keep the default settings for a first run.
3. Select **Generate mesh**. Follow the current stage and expand the OpenFOAM log as needed.
4. Review the mesh quality metrics and select **Download ZIP** when the run completes.

Press Ctrl+C in each terminal to stop the local servers. Uploads, job files, and the SQLite database are stored in `workspace_jobs/` by default.

## Shared OpenFOAM case files

Each new meshing job has a Windows folder named after its STL, such as `workspace_jobs/jobs/cylinder/`, with a matching ZIP name. A new case with the same name gets a timestamp, such as `cylinder_2026-11-21_14-30-05`. Docker mounts the folder read/write at `/workspace` while it runs the generated `run_mesh.sh`. Edits saved from Windows are visible in the container, and files written by Docker remain in Windows after the container exits. Avoid editing a dictionary while OpenFOAM is reading it. The ZIP captures the case at the end of the job.

| Case path | Contents |
| --- | --- |
| `0/` | Initially empty. Solver initial and boundary field files can be added here. |
| `constant/triSurface/` | Input STL and extracted features when enabled. |
| `constant/polyMesh/` | Mesh written by OpenFOAM. |
| `system/` | Dictionaries for background mesh, surface refinement, and quality settings. |
| `run_mesh.sh` | Generated Bash script that runs the meshing pipeline inside Docker. |

The GUI generates `system/blockMeshDict` using the geometry bounds, domain margins, and background grid divisions. The dictionary defines the block vertices, cell counts, grading, and boundary faces and patch names. `blockMesh` creates the initial grid from it. Then `snappyHexMesh -overwrite` refines and snaps that grid to the STL and writes the result to `constant/polyMesh/`.

Select **Open folder** from Jobs, progress, or results to open the case in Windows Explorer. Use **Copy path** on progress or results to copy the location. To apply dictionary edits, edit and save `system/blockMeshDict` or `system/snappyHexMeshDict`, then select **Remesh this case**. Only one run can use the folder at a time. The rerun uses the saved dictionaries and preserves files in `0/`. If the rerun fails or is cancelled, the previous mesh is restored and the last completed ZIP remains downloadable. A new GUI job generates fresh dictionaries in a separate case folder.

In **Jobs**, select **Clear** to remove a finished entry from history or **Clear all history** to remove all finished entries. Saved case folders and ZIPs stay on disk.

## Configuration

The default settings work for the local setup above. To override a setting, set it in the backend terminal before starting Python. For example, use `$env:DEBUG = 'true'` to enable the interactive API docs at `http://127.0.0.1:8000/docs`. The backend reads process environment variables. Use [.env.example](.env.example) as a reference, since the runner does not load `.env`. SQLite uses `jobs.db` under `WORKSPACE_DIR`. If you change `APP_PORT`, update the proxy target in [frontend/vite.config.ts](frontend/vite.config.ts) to match.

## Tests and build

From the project root, run the backend suite with a separate workspace:

```powershell
$env:WORKSPACE_DIR = 'workspace_jobs/test-run'
.\venv\Scripts\python.exe -m pytest backend/tests
Remove-Item Env:WORKSPACE_DIR
```

The OpenFOAM integration test requires a reachable Docker engine and the image from step 1. To run the backend tests without Docker, add `-m 'not integration'`.

From the project root, run the frontend checks:

```powershell
npm.cmd --prefix frontend exec -- vitest run
npm.cmd --prefix frontend run lint
npm.cmd --prefix frontend run build
```

## More documentation

- [Architecture](docs/ARCHITECTURE.md)
- [REST API](docs/API.md)
- [OpenFOAM pipeline](docs/OPENFOAM_PIPELINE.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)
- [Security](docs/SECURITY.md)
