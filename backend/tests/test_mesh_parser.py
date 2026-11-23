"""Unit tests for checkMesh output parser."""

from backend.app.services.mesh_parser import parse_check_mesh_log

SAMPLE_CHECK_MESH = """/*---------------------------------------------------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  2506                                  |
|   \\\\  /    A nd           | Website:  www.openfoam.com                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
Create mesh for time = constant

Mesh stats 
    points:           1848
    internal points:  0
    faces:            4520
    internal faces:   3200
    cells:            1350
    faces per cell:   6
    boundary patches: 7

Overall number of cells of each type:
    hexahedra:     1250
    prisms:        50
    wedges:        0
    pyramids:      0
    tet wedges:    0
    tetrahedra:    0
    polyhedra:     50

Checking geometry...
    Overall domain bounding box (-2 -1 -1) (4 1 1)
    Boundary openness (1.2e-16 2.3e-16 1.1e-16) OK.
    Max cell openness = 1.5e-16 OK.
    Max aspect ratio = 2.15 OK.
    Mesh non-orthogonality Max: 42.5 average: 14.2
    Non-orthogonality check OK.
    Face pyramids OK.
    Max skewness = 0.85 OK.

Mesh OK.

End
"""

def test_parse_check_mesh_log():
    result = parse_check_mesh_log("job-123", SAMPLE_CHECK_MESH)
    assert result.mesh_ok is True
    assert result.is_valid is True
    assert result.num_points == 1848
    assert result.num_faces == 4520
    assert result.num_internal_faces == 3200
    assert result.num_cells == 1350
    assert result.cell_types.get("hexahedra") == 1250
    assert result.cell_types.get("polyhedra") == 50
    assert result.max_non_ortho == 42.5
    assert result.avg_non_ortho == 14.2
    assert result.max_skewness == 0.85
    assert result.max_aspect_ratio == 2.15
    assert result.bounding_box is not None
    assert result.bounding_box.min_x == -2.0
    assert result.bounding_box.max_x == 4.0
    assert len(result.warnings) == 0
