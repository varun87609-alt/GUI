"""OpenFOAM checkMesh Output Parser.

Extracts mesh metrics, topological soundness, cell counts, cell type breakdowns,
orthogonality, skewness, aspect ratios, and validity from checkMesh logs.
"""

import re
from typing import Optional, Dict, Any, List
from backend.app.schemas import MeshStatsResponse, BoundingBox

def _safe_float(val: Optional[str]) -> Optional[float]:
    if not val:
        return None
    cleaned = val.strip().rstrip(".,;")
    try:
        return float(cleaned)
    except ValueError:
        return None

def parse_check_mesh_log(job_id: str, log_text: str) -> MeshStatsResponse:
    """Parses OpenFOAM checkMesh output text into a structured MeshStatsResponse."""
    mesh_ok = "Mesh OK." in log_text
    
    # Check for fatal error
    is_valid = mesh_ok or ("End" in log_text and "FATAL" not in log_text)

    # Number of points, faces, internal faces, cells
    points_match = re.search(r"points:\s+(\d+)", log_text)
    faces_match = re.search(r"faces:\s+(\d+)", log_text)
    int_faces_match = re.search(r"internal faces:\s+(\d+)", log_text)
    cells_match = re.search(r"cells:\s+(\d+)", log_text)

    num_points = int(points_match.group(1)) if points_match else 0
    num_faces = int(faces_match.group(1)) if faces_match else 0
    num_internal_faces = int(int_faces_match.group(1)) if int_faces_match else 0
    num_cells = int(cells_match.group(1)) if cells_match else 0

    # Cell types
    cell_types: Dict[str, int] = {}
    types_section = re.search(
        r"Overall number of cells of each type:(.*?)(?:Checking topology|Checking geometry|\n\s*\n)",
        log_text,
        re.DOTALL,
    )
    if types_section:
        for line in types_section.group(1).strip().splitlines():
            line = line.strip()
            if ":" in line:
                k, v = line.split(":", 1)
                try:
                    cell_types[k.strip()] = int(v.strip())
                except ValueError:
                    pass

    # Domain bounding box
    bbox: Optional[BoundingBox] = None
    bbox_match = re.search(
        r"Overall domain bounding box \(([-\d\.e\+]+)\s+([-\d\.e\+]+)\s+([-\d\.e\+]+)\)\s+\(([-\d\.e\+]+)\s+([-\d\.e\+]+)\s+([-\d\.e\+]+)\)",
        log_text,
    )
    if bbox_match:
        min_x = _safe_float(bbox_match.group(1)) or 0.0
        min_y = _safe_float(bbox_match.group(2)) or 0.0
        min_z = _safe_float(bbox_match.group(3)) or 0.0
        max_x = _safe_float(bbox_match.group(4)) or 0.0
        max_y = _safe_float(bbox_match.group(5)) or 0.0
        max_z = _safe_float(bbox_match.group(6)) or 0.0
        bbox = BoundingBox(
            min_x=min_x,
            min_y=min_y,
            min_z=min_z,
            max_x=max_x,
            max_y=max_y,
            max_z=max_z,
            dim_x=max_x - min_x,
            dim_y=max_y - min_y,
            dim_z=max_z - min_z,
        )

    # Non-orthogonality
    max_non_ortho: Optional[float] = None
    avg_non_ortho: Optional[float] = None
    ortho_match = re.search(
        r"Mesh non-orthogonality Max:\s+([-\d\.e\+]+)\s+average:\s+([-\d\.e\+]+)",
        log_text,
    )
    if ortho_match:
        max_non_ortho = _safe_float(ortho_match.group(1))
        avg_non_ortho = _safe_float(ortho_match.group(2))

    # Skewness
    max_skewness: Optional[float] = None
    skew_match = re.search(r"Max skewness\s*=\s*([-\d\.e\+]+)", log_text)
    if skew_match:
        max_skewness = _safe_float(skew_match.group(1))

    # Aspect ratio
    max_aspect_ratio: Optional[float] = None
    ar_match = re.search(r"Max aspect ratio\s*=\s*([-\d\.e\+]+)", log_text)
    if ar_match:
        max_aspect_ratio = _safe_float(ar_match.group(1))

    # Volume
    total_volume: Optional[float] = None
    vol_match = re.search(r"Total volume\s*=\s*([-\d\.e\+]+)", log_text)
    if vol_match:
        total_volume = _safe_float(vol_match.group(1))

    # Collect quality warnings
    warnings: List[str] = []
    if max_non_ortho and max_non_ortho > 70.0:
        warnings.append(
            f"High maximum non-orthogonality ({max_non_ortho:.1f}°). Simulation may require non-orthogonal correctors."
        )
    if max_skewness and max_skewness > 4.0:
        warnings.append(f"High maximum skewness ({max_skewness:.2f}).")
    if max_aspect_ratio and max_aspect_ratio > 100.0:
        warnings.append(f"High maximum aspect ratio ({max_aspect_ratio:.1f}).")

    for line in log_text.splitlines():
        if "***" in line or "Severe" in line or "Failed" in line:
            clean_l = line.strip()
            if clean_l and clean_l not in warnings:
                warnings.append(clean_l)

    # Raw summary
    summary_lines = []
    capture = False
    for line in log_text.splitlines():
        if "Create mesh for time" in line or "Check mesh..." in line:
            capture = True
        if capture:
            summary_lines.append(line)
        if "Mesh OK." in line or "End" in line:
            break

    raw_summary = "\n".join(summary_lines) if summary_lines else None

    return MeshStatsResponse(
        job_id=job_id,
        is_valid=is_valid,
        mesh_ok=mesh_ok,
        num_points=num_points,
        num_faces=num_faces,
        num_internal_faces=num_internal_faces,
        num_cells=num_cells,
        cell_types=cell_types,
        bounding_box=bbox,
        max_non_ortho=max_non_ortho,
        avg_non_ortho=avg_non_ortho,
        max_skewness=max_skewness,
        max_aspect_ratio=max_aspect_ratio,
        total_volume=total_volume,
        warnings=warnings,
        raw_summary=raw_summary,
    )
