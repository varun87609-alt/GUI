"""End-to-End OpenFOAM Docker Integration Test.

Meshes a real geometry using the verified openeuler/openfoam:2506-oe2403sp4 image,
executing blockMesh, snappyHexMesh, and checkMesh, and validating results.
"""

import time
import re
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile
import pytest
from starlette.testclient import TestClient

from backend.app.main import app
from backend.app.services.docker_runner import docker_runner
from backend.app.config import settings

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "workspace_dir_name", str(tmp_path))
    with TestClient(app) as test_client:
        yield test_client

@pytest.mark.integration
def test_full_openfoam_meshing_pipeline(client):
    """Executes the full automated OpenFOAM meshing workflow against Docker."""
    if not docker_runner.ping():
        pytest.skip("Docker daemon not reachable.")
    if not docker_runner.is_image_available(settings.docker_image):
        pytest.skip(f"Docker image {settings.docker_image} not present.")

    cube_path = Path(__file__).resolve().parent.parent.parent / "sample_geometries" / "cube.stl"
    assert cube_path.exists(), f"Sample geometry not found at {cube_path}"

    # 1. Upload geometry
    with open(cube_path, "rb") as f:
        up_resp = client.post(
            "/api/v1/uploads",
            files={"file": ("cube.stl", f, "application/sla")},
        )
    assert up_resp.status_code == 201, up_resp.text
    up_data = up_resp.json()
    upload_id = up_data["upload_id"]
    assert up_data["triangle_count"] == 12

    # 2. Submit meshing job
    job_payload = {
        "upload_id": upload_id,
        "workflow_type": "external_flow",
        "target_cells_x": 10,
        "target_cells_y": 10,
        "target_cells_z": 10,
        "domain_margin": {
            "min_x_multiplier": 1.0,
            "max_x_multiplier": 1.0,
            "min_y_multiplier": 1.0,
            "max_y_multiplier": 1.0,
            "min_z_multiplier": 1.0,
            "max_z_multiplier": 1.0,
        },
        "surface_refinement": {
            "min_level": 1,
            "max_level": 1,
        },
        "feature_refinement": {
            "enabled": True,
            "included_angle": 150.0,
            "level": 1,
        },
        "boundary_layers": {
            "enabled": False,
        },
        "timeout_seconds": 120,
    }

    job_resp = client.post("/api/v1/jobs", json=job_payload)
    assert job_resp.status_code == 201, job_resp.text
    job_id = job_resp.json()["job_id"]

    # 3. Poll until completed or timeout (max 60s)
    max_wait = 60
    start_t = time.time()
    final_status = None

    while time.time() - start_t < max_wait:
        poll_resp = client.get(f"/api/v1/jobs/{job_id}")
        assert poll_resp.status_code == 200
        poll_data = poll_resp.json()
        final_status = poll_data["status"]
        if final_status in ("completed", "failed", "cancelled"):
            break
        time.sleep(1.5)

    assert final_status == "completed", f"Job ended in status '{final_status}'. Details: {poll_data.get('error_message')}"

    # 4. Verify logs
    log_resp = client.get(f"/api/v1/jobs/{job_id}/logs")
    assert log_resp.status_code == 200
    logs_data = log_resp.json()
    assert logs_data["total_lines"] > 20
    all_logs = "\n".join(logs_data["lines"])
    assert "=== ALL COMPLETE ===" in all_logs
    assert "Mesh OK." in all_logs

    # 5. Verify results endpoint
    results_resp = client.get(f"/api/v1/jobs/{job_id}/results")
    assert results_resp.status_code == 200
    res_data = results_resp.json()
    assert res_data["mesh_ok"] is True
    assert res_data["num_cells"] > 0
    assert res_data["num_points"] > 0

    # 6. Verify download endpoint
    dl_resp = client.get(f"/api/v1/jobs/{job_id}/download")
    assert dl_resp.status_code == 200
    assert dl_resp.headers["content-type"] == "application/zip"
    assert len(dl_resp.content) > 1000  # valid zip archive

    case_dir = settings.workspace_path / "jobs" / "cube"
    assert 'filename="cube.zip"' in dl_resp.headers["content-disposition"]
    assert (case_dir / "cube.zip").is_file()
    assert (case_dir / "0").is_dir()
    assert (case_dir / "constant/polyMesh/points").is_file()
    assert (case_dir / "system/blockMeshDict").is_file()
    with ZipFile(BytesIO(dl_resp.content)) as archive:
        assert {"0/", "system/blockMeshDict", "constant/polyMesh/points", "run_mesh.sh"} <= set(archive.namelist())

    job_url = f"/api/v1/jobs/{job_id}"
    case_status = client.get(job_url).json()
    assert case_status["case_path"] == str(case_dir)
    assert case_status["can_remesh"]

    block_dict = case_dir / "system/blockMeshDict"
    edited_dict = block_dict.read_text().replace("(10 10 10) simpleGrading", "(12 10 10) simpleGrading")
    assert "(12 10 10) simpleGrading" in edited_dict
    block_dict.write_text(edited_dict)
    field = case_dir / "0/test-field"
    field.write_text("preserve this field")

    def wait_for_run(url=job_url):
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            run = client.get(url).json()
            if run["status"] in ("completed", "failed", "cancelled"):
                return run
            time.sleep(0.25)
        pytest.fail("Remesh did not finish in 60 seconds")

    remesh = client.post(f"{job_url}/remesh")
    assert remesh.status_code == 202, remesh.text
    assert client.post(f"{job_url}/remesh").status_code == 409
    remeshed = wait_for_run()
    assert remeshed["status"] == "completed", remeshed
    assert remeshed["case_path"] == str(case_dir)
    assert client.get(f"{job_url}/results").json()["num_cells"] != res_data["num_cells"]
    assert field.read_text() == "preserve this field"
    remesh_archive = client.get(f"{job_url}/download").content
    points = case_dir / "constant/polyMesh/points"
    remesh_points = points.read_bytes()

    snappy_dict = case_dir / "system/snappyHexMeshDict"
    snappy_dict.write_text("invalid dictionary")
    assert client.post(f"{job_url}/remesh").status_code == 202
    failed_run = wait_for_run()
    assert failed_run["status"] == "failed", failed_run
    assert failed_run["has_archive"]
    assert points.read_bytes() == remesh_points
    assert client.get(f"{job_url}/download").content == remesh_archive
    assert field.read_text() == "preserve this field"

    repeated = client.post("/api/v1/jobs", json=job_payload)
    assert repeated.status_code == 201, repeated.text
    second = repeated.json()
    assert re.fullmatch(r"cube_\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}", second["case_folder"])
    second_url = f"/api/v1/jobs/{second['job_id']}"
    assert client.delete(f"{second_url}/history").status_code == 409
    assert client.delete(f"{job_url}/history").json() == {"cleared": 1}
    assert client.delete("/api/v1/jobs/history").json() == {"cleared": 0}
    assert [entry["job_id"] for entry in client.get("/api/v1/jobs").json()] == [second["job_id"]]
    assert wait_for_run(second_url)["status"] == "completed"
    second_dir = Path(second["case_path"])
    second_archive = second_dir / f"{second_dir.name}.zip"
    assert second_archive.is_file()
    assert client.delete("/api/v1/jobs/history").json() == {"cleared": 1}
    assert client.get("/api/v1/jobs").json() == []
    assert points.is_file() and second_archive.is_file()
    assert client.get(f"{job_url}/download").content == remesh_archive
