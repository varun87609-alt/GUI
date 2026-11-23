"""Geometry Analysis Service.

Performs robust parsing, validation, bounding-box computation, scale detection,
and topology sanity checks on uploaded STL files.
"""

import os
import struct
from pathlib import Path
from typing import Dict, Any, List, Tuple
import numpy as np
import trimesh

from backend.app.config import settings
from backend.app.schemas import BoundingBox, GeometryAnalysisResponse

class GeometryAnalysisError(Exception):
    """Raised when an STL file is invalid, corrupt, or exceeds limits."""
    pass

def detect_stl_format(file_path: Path) -> str:
    """Detects whether an STL file is binary or ASCII format."""
    file_size = file_path.stat().st_size
    if file_size < 84:
        # Too small to even be a valid binary header
        with open(file_path, "r", errors="ignore") as f:
            chunk = f.read(200).strip().lower()
            if chunk.startswith("solid"):
                return "ascii"
            raise GeometryAnalysisError("STL file is too small to be valid.")

    with open(file_path, "rb") as f:
        header = f.read(80)
        num_faces_bytes = f.read(4)

    expected_faces = struct.unpack("<I", num_faces_bytes)[0]
    expected_binary_size = 84 + (expected_faces * 50)

    # Check if exact binary size matches
    if file_size == expected_binary_size:
        return "binary"

    # Otherwise check if ASCII
    try:
        with open(file_path, "r", encoding="utf-8", errors="strict") as f:
            first_chars = f.read(100).strip().lower()
            if first_chars.startswith("solid"):
                return "ascii"
    except (UnicodeDecodeError, ValueError):
        pass

    # If it starts with solid and passes ASCII checks
    with open(file_path, "rb") as f:
        first_80 = f.read(80).decode("latin-1", errors="ignore").strip().lower()
        if first_80.startswith("solid") and b"\x00" not in f.read(512):
            return "ascii"

    return "binary"

def analyze_stl(file_path: Path, upload_id: str, original_filename: str) -> GeometryAnalysisResponse:
    """Analyzes an uploaded STL geometry file and produces a structured report."""
    if not file_path.exists():
        raise GeometryAnalysisError(f"Geometry file not found at {file_path}")

    file_size = file_path.stat().st_size
    if file_size == 0:
        raise GeometryAnalysisError("Uploaded STL file is empty (0 bytes).")
    if file_size > settings.max_upload_size_bytes:
        raise GeometryAnalysisError(
            f"File size ({file_size / (1024 * 1024):.2f} MB) exceeds maximum allowed limit "
            f"({settings.max_upload_size_bytes / (1024 * 1024):.2f} MB)."
        )

    stl_format = detect_stl_format(file_path)

    try:
        mesh = trimesh.load(
            str(file_path),
            file_type="stl",
            force="mesh",
            process=False,  # do not alter raw vertices
        )
    except Exception as e:
        raise GeometryAnalysisError(f"Failed to parse STL geometry: {str(e)}")

    if not isinstance(mesh, trimesh.Trimesh):
        raise GeometryAnalysisError("Loaded geometry is not a valid triangle mesh.")

    vertices = np.asarray(mesh.vertices, dtype=np.float64)
    faces = np.asarray(mesh.faces, dtype=np.int64)

    if len(vertices) == 0 or len(faces) == 0:
        raise GeometryAnalysisError("Geometry contains no vertices or faces.")

    triangle_count = int(len(faces))
    clean_mesh = mesh.copy()
    clean_mesh.merge_vertices()
    vertex_count = int(len(clean_mesh.vertices))

    if triangle_count > settings.max_triangle_count:
        raise GeometryAnalysisError(
            f"Triangle count ({triangle_count:,}) exceeds limit of {settings.max_triangle_count:,}."
        )

    # Check for non-finite values (NaN, Inf)
    if not np.all(np.isfinite(vertices)):
        raise GeometryAnalysisError("Geometry contains non-finite coordinates (NaN or Inf).")

    # Compute bounds component-wise
    min_x, min_y, min_z = np.min(vertices, axis=0)
    max_x, max_y, max_z = np.max(vertices, axis=0)

    dim_x = float(max_x - min_x)
    dim_y = float(max_y - min_y)
    dim_z = float(max_z - min_z)

    bounding_box = BoundingBox(
        min_x=float(min_x),
        min_y=float(min_y),
        min_z=float(min_z),
        max_x=float(max_x),
        max_y=float(max_y),
        max_z=float(max_z),
        dim_x=dim_x,
        dim_y=dim_y,
        dim_z=dim_z,
    )

    warnings: List[str] = []

    # Check for flat or zero-thickness geometry
    min_dim = min(dim_x, dim_y, dim_z)
    max_dim = max(dim_x, dim_y, dim_z)

    if min_dim <= 1e-7:
        warnings.append(
            f"Zero or near-zero thickness detected in one dimension (dims: {dim_x:.4f} x {dim_y:.4f} x {dim_z:.4f}). "
            "Geometry may be 2D, planar, or collapsed."
        )

    # Scale warnings (OpenFOAM assumes SI units: meters)
    scale_warning = None
    if max_dim < 0.005:
        scale_warning = (
            f"Maximum dimension is very small ({max_dim:.4e} m). If the CAD model was designed in "
            "millimeters or inches, OpenFOAM will treat these values directly as meters unless scaled."
        )
        warnings.append(scale_warning)
    elif max_dim > 1000.0:
        scale_warning = (
            f"Maximum dimension is very large ({max_dim:.2f} m). If designed in millimeters, this may "
            "represent an unscaled model (e.g. 1000 mm interpreted as 1000 meters)."
        )
        warnings.append(scale_warning)

    # Aspect ratio check
    aspect_ratio_warning = None
    if min_dim > 1e-7:
        aspect_ratio = max_dim / min_dim
        if aspect_ratio > 50.0:
            aspect_ratio_warning = (
                f"High geometry aspect ratio ({aspect_ratio:.1f}:1). May require specialized anisotropic refinement."
            )
            warnings.append(aspect_ratio_warning)

    # Watertight & Volume Check
    is_watertight = bool(clean_mesh.is_watertight)
    if not is_watertight:
        warnings.append(
            "Geometry is not watertight (has open boundary edges or non-manifold junctions). "
            "SnappyHexMesh can still snap to open surfaces, but internal fluid region extraction may fail."
        )

    # Degenerate face check
    try:
        # Cross product of edges for area
        v0 = vertices[faces[:, 0]]
        v1 = vertices[faces[:, 1]]
        v2 = vertices[faces[:, 2]]
        cross_prod = np.cross(v1 - v0, v2 - v0)
        areas = 0.5 * np.linalg.norm(cross_prod, axis=1)
        degenerate_count = int(np.sum(areas <= 1e-14))
        if degenerate_count > 0:
            warnings.append(
                f"Geometry contains {degenerate_count} degenerate triangle(s) with zero or near-zero area."
            )
    except Exception:
        pass

    return GeometryAnalysisResponse(
        upload_id=upload_id,
        filename=original_filename,
        file_size_bytes=file_size,
        format=stl_format,
        triangle_count=triangle_count,
        vertex_count=vertex_count,
        is_watertight=is_watertight,
        bounding_box=bounding_box,
        scale_warning=scale_warning,
        aspect_ratio_warning=aspect_ratio_warning,
        recommended_units="m",
        warnings=warnings,
    )
