"""Unit tests for geometry analysis and validation."""

import os
import tempfile
from pathlib import Path
import pytest

from backend.app.services.geometry import (
    analyze_stl,
    detect_stl_format,
    GeometryAnalysisError,
)

CUBE_ASCII = """solid cube
  facet normal 0 0 1
    outer loop
      vertex 0 0 1
      vertex 1 0 1
      vertex 1 1 1
    endloop
  endfacet
  facet normal 0 0 1
    outer loop
      vertex 0 0 1
      vertex 1 1 1
      vertex 0 1 1
    endloop
  endfacet
  facet normal 0 0 -1
    outer loop
      vertex 0 0 0
      vertex 1 1 0
      vertex 1 0 0
    endloop
  endfacet
  facet normal 0 0 -1
    outer loop
      vertex 0 0 0
      vertex 0 1 0
      vertex 1 1 0
    endloop
  endfacet
  facet normal 0 1 0
    outer loop
      vertex 0 1 0
      vertex 0 1 1
      vertex 1 1 1
    endloop
  endfacet
  facet normal 0 1 0
    outer loop
      vertex 0 1 0
      vertex 1 1 1
      vertex 1 1 0
    endloop
  endfacet
  facet normal 0 -1 0
    outer loop
      vertex 0 0 0
      vertex 1 0 1
      vertex 0 0 1
    endloop
  endfacet
  facet normal 0 -1 0
    outer loop
      vertex 0 0 0
      vertex 1 0 0
      vertex 1 0 1
    endloop
  endfacet
  facet normal 1 0 0
    outer loop
      vertex 1 0 0
      vertex 1 1 0
      vertex 1 1 1
    endloop
  endfacet
  facet normal 1 0 0
    outer loop
      vertex 1 0 0
      vertex 1 1 1
      vertex 1 0 1
    endloop
  endfacet
  facet normal -1 0 0
    outer loop
      vertex 0 0 0
      vertex 0 0 1
      vertex 0 1 1
    endloop
  endfacet
  facet normal -1 0 0
    outer loop
      vertex 0 0 0
      vertex 0 1 1
      vertex 0 1 0
    endloop
  endfacet
endsolid cube
"""

def test_detect_format_ascii(tmp_path: Path):
    stl_file = tmp_path / "test.stl"
    stl_file.write_text(CUBE_ASCII)
    assert detect_stl_format(stl_file) == "ascii"

def test_analyze_cube_ascii(tmp_path: Path):
    stl_file = tmp_path / "cube.stl"
    stl_file.write_text(CUBE_ASCII)

    result = analyze_stl(stl_file, upload_id="test-1", original_filename="cube.stl")
    assert result.triangle_count == 12
    assert result.vertex_count == 8
    assert result.is_watertight is True
    assert result.bounding_box.min_x == 0.0
    assert result.bounding_box.max_x == 1.0
    assert result.bounding_box.dim_x == 1.0
    assert result.bounding_box.dim_y == 1.0
    assert result.bounding_box.dim_z == 1.0
    assert result.scale_warning is None

def test_empty_file_rejected(tmp_path: Path):
    empty_file = tmp_path / "empty.stl"
    empty_file.write_bytes(b"")

    with pytest.raises(GeometryAnalysisError, match="empty"):
        analyze_stl(empty_file, upload_id="test-2", original_filename="empty.stl")

def test_small_scale_warning(tmp_path: Path):
    # Scale cube down to 0.001 (1 mm)
    small_stl = CUBE_ASCII.replace(" 1", " 0.001")
    stl_file = tmp_path / "small.stl"
    stl_file.write_text(small_stl)

    result = analyze_stl(stl_file, upload_id="test-3", original_filename="small.stl")
    assert result.scale_warning is not None
    assert "very small" in result.scale_warning

def test_large_scale_warning(tmp_path: Path):
    # Scale cube up to 2000 (2000 m)
    large_stl = CUBE_ASCII.replace(" 1", " 2000")
    stl_file = tmp_path / "large.stl"
    stl_file.write_text(large_stl)

    result = analyze_stl(stl_file, upload_id="test-4", original_filename="large.stl")
    assert result.scale_warning is not None
    assert "very large" in result.scale_warning
