"""API Integration and Endpoint Tests."""

import io
import pytest
from starlette.testclient import TestClient
from backend.app.main import app
from backend.app.database import init_db

init_db()
client = TestClient(app)


@pytest.mark.parametrize(
    ("source", "origin", "fetch_site", "action", "expected_status"),
    [
        ("127.0.0.1", "http://127.0.0.1:5174", "same-origin", "1", 404),
        ("::1", "http://[::1]:4173", "same-origin", "1", 404),
        ("127.0.0.1", "http://localhost:4173", None, "1", 404),
        ("127.0.0.1", "http://localhost:5173", "same-site", "1", 404),
        ("127.0.0.1", "http://localhost:5173", "cross-site", "1", 403),
        ("127.0.0.1", "https://localhost.example.com:5173", "same-origin", "1", 403),
        ("192.0.2.10", "http://127.0.0.1:5173", "same-origin", "1", 403),
        ("127.0.0.1", "http://127.0.0.1:5173", "same-origin", None, 403),
    ],
)
def test_open_case_folder_checks_local_origin(source, origin, fetch_site, action, expected_status, monkeypatch):
    monkeypatch.setattr("backend.app.api.jobs.settings.allowed_origins", ["http://localhost:5173"])
    headers = {"Origin": origin}
    if fetch_site:
        headers["Sec-Fetch-Site"] = fetch_site
    if action:
        headers["X-Open-Case-Folder"] = action
    with TestClient(app, client=(source, 50000)) as local_client:
        response = local_client.post("/api/v1/jobs/nonexistent/open-folder", headers=headers)
    assert response.status_code == expected_status


SAMPLE_STL = """solid test
  facet normal 0 0 1
    outer loop
      vertex 0 0 0
      vertex 1 0 0
      vertex 1 1 0
    endloop
  endfacet
endsolid test
"""

def test_health_endpoint():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "docker_ready" in data
    assert "openfoam_version" in data
    assert data["openfoam_version"] == "v2506"

def test_capabilities_endpoint():
    response = client.get("/api/v1/capabilities")
    assert response.status_code == 200
    data = response.json()
    assert "external_flow" in data["supported_workflows"]
    assert data["max_upload_size_bytes"] > 0

def test_upload_invalid_extension():
    file_bytes = io.BytesIO(b"fake content")
    response = client.post(
        "/api/v1/uploads",
        files={"file": ("test.txt", file_bytes, "text/plain")},
    )
    assert response.status_code == 400
    assert "Only .stl files are supported" in response.json()["detail"]

def test_upload_valid_stl():
    file_bytes = io.BytesIO(SAMPLE_STL.encode("utf-8"))
    response = client.post(
        "/api/v1/uploads",
        files={"file": ("test.stl", file_bytes, "application/sla")},
    )
    assert response.status_code == 201
    data = response.json()
    assert "upload_id" in data
    assert data["triangle_count"] == 1
    assert data["bounding_box"]["dim_x"] == 1.0

def test_create_job_invalid_upload():
    response = client.post(
        "/api/v1/jobs",
        json={"upload_id": "non-existent-upload-id"},
    )
    assert response.status_code == 404

def test_create_job_excessive_cells():
    # First upload valid STL
    file_bytes = io.BytesIO(SAMPLE_STL.encode("utf-8"))
    up_resp = client.post(
        "/api/v1/uploads",
        files={"file": ("test.stl", file_bytes, "application/sla")},
    )
    upload_id = up_resp.json()["upload_id"]

    # Attempt to create job with 200x200x200 = 8,000,000 cells > 3,000,000 limit
    response = client.post(
        "/api/v1/jobs",
        json={
            "upload_id": upload_id,
            "target_cells_x": 200,
            "target_cells_y": 200,
            "target_cells_z": 200,
        },
    )
    assert response.status_code == 422
    assert "exceeds maximum allowed limit" in response.json()["detail"]

def test_list_jobs():
    response = client.get("/api/v1/jobs")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
