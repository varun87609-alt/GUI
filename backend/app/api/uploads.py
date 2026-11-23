"""STL File Upload and Pre-Meshing Analysis API."""

import os
import uuid
import json
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException, status
from backend.app.config import settings
from backend.app.schemas import GeometryAnalysisResponse
from backend.app.services.geometry import analyze_stl, GeometryAnalysisError

router = APIRouter(prefix="/uploads", tags=["STL Uploads"])

@router.post("", response_model=GeometryAnalysisResponse, status_code=status.HTTP_201_CREATED)
async def upload_stl(file: UploadFile = File(...)):
    """Uploads an STL file, validates structure, computes bounding box, and checks geometry."""
    # Sanitize and validate filename
    filename = os.path.basename(file.filename or "geometry.stl")
    if not (filename.lower().endswith(".stl")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file extension. Only .stl files are supported.",
        )

    # Generate unpredictable upload identifier
    upload_id = str(uuid.uuid4())
    upload_dir = settings.uploads_path / upload_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    target_path = upload_dir / "geometry.stl"

    # Stream to disk with size limit enforcement
    total_bytes = 0
    chunk_size = 1024 * 1024  # 1 MB chunks
    try:
        with open(target_path, "wb") as f:
            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break
                total_bytes += len(chunk)
                if total_bytes > settings.max_upload_size_bytes:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"Uploaded file exceeds maximum limit of {settings.max_upload_size_bytes / (1024 * 1024):.1f} MB.",
                    )
                f.write(chunk)
    except HTTPException:
        # Clean up partial upload
        if target_path.exists():
            target_path.unlink()
        raise
    except Exception as e:
        if target_path.exists():
            target_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save uploaded file: {str(e)}",
        )

    # Perform geometry analysis
    try:
        analysis = analyze_stl(target_path, upload_id=upload_id, original_filename=filename)
        # Cache analysis json
        (upload_dir / "analysis.json").write_text(
            json.dumps(analysis.model_dump()), encoding="utf-8"
        )
        return analysis
    except GeometryAnalysisError as e:
        # Clean up invalid file
        if target_path.exists():
            target_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )

@router.get("/{upload_id}", response_model=GeometryAnalysisResponse)
def get_upload_analysis(upload_id: str):
    """Retrieves cached geometry analysis for a previous upload."""
    upload_dir = settings.uploads_path / upload_id
    analysis_file = upload_dir / "analysis.json"

    if not analysis_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Upload ID '{upload_id}' not found.",
        )

    data = json.loads(analysis_file.read_text(encoding="utf-8"))
    return GeometryAnalysisResponse(**data)
