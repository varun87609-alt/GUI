"""Unit tests for OpenFOAM dictionary generation."""

from pathlib import Path
from backend.app.schemas import (
    BoundingBox,
    MeshJobCreateRequest,
    DomainMargin,
    SurfaceRefinement,
    FeatureRefinement,
    BoundaryLayers,
)
from backend.app.models import WorkflowType
from backend.app.services.dict_generator import (
    compute_domain_bounds,
    generate_block_mesh_dict,
    generate_snappy_hex_mesh_dict,
    generate_surface_feature_extract_dict,
    write_case_files,
)

def test_compute_domain_bounds_external():
    bbox = BoundingBox(
        min_x=-1.0, min_y=-1.0, min_z=-1.0,
        max_x=1.0, max_y=1.0, max_z=1.0,
        dim_x=2.0, dim_y=2.0, dim_z=2.0,
    )
    margin = DomainMargin(
        min_x_multiplier=1.0, max_x_multiplier=2.0,
        min_y_multiplier=1.0, max_y_multiplier=1.0,
        min_z_multiplier=1.0, max_z_multiplier=1.0,
    )
    domain_bbox, keep_point = compute_domain_bounds(bbox, margin, WorkflowType.EXTERNAL_FLOW)

    assert domain_bbox.min_x == -3.0  # -1 - 2*1
    assert domain_bbox.max_x == 5.0   # 1 + 2*2
    assert domain_bbox.min_y == -3.0
    assert domain_bbox.max_y == 3.0
    # Keep point should be outside the original bbox [-1, 1]
    assert keep_point[0] < -1.0 or keep_point[0] > 1.0

def test_generate_block_mesh_dict():
    domain_bbox = BoundingBox(
        min_x=-5.0, min_y=-2.0, min_z=-2.0,
        max_x=10.0, max_y=2.0, max_z=2.0,
        dim_x=15.0, dim_y=4.0, dim_z=4.0,
    )
    content = generate_block_mesh_dict(domain_bbox, 30, 10, 10)
    assert "hex (0 1 2 3 4 5 6 7) (30 10 10)" in content
    assert "inlet" in content
    assert "outlet" in content
    assert "bottom" in content
    assert "top" in content

def test_generate_snappy_dict():
    req = MeshJobCreateRequest(
        upload_id="test",
        workflow_type=WorkflowType.EXTERNAL_FLOW,
        surface_refinement=SurfaceRefinement(min_level=2, max_level=3),
        feature_refinement=FeatureRefinement(enabled=True, level=3, included_angle=140),
        boundary_layers=BoundaryLayers(enabled=True, n_surface_layers=3),
    )
    content = generate_snappy_hex_mesh_dict(
        stl_filename="geometry.stl",
        surface_name="geometry",
        feature_file="geometry.eMesh",
        config=req,
        location_in_mesh=(0.5, 0.5, 0.5),
    )
    assert "level (2 3);" in content
    assert 'file "geometry.eMesh";' in content
    assert "level 3;" in content
    assert "nSurfaceLayers 3;" in content
    assert "addLayers       true;" in content
