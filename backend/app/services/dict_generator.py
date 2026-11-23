"""OpenFOAM Dictionary Generation Module.

Generates strongly-typed, validated OpenFOAM v2506 configuration dictionaries
and execution runner scripts without shell-injection vulnerabilities.
"""

from pathlib import Path
from typing import Tuple, Dict, Any, Optional
import math
import re

from backend.app.schemas import (
    BoundingBox,
    MeshJobCreateRequest,
    DomainMargin,
    SurfaceRefinement,
    FeatureRefinement,
    BoundaryLayers,
)
from backend.app.models import WorkflowType

def sanitize_identifier(name: str) -> str:
    """Sanitizes names for OpenFOAM identifiers (alphanumeric and underscores only)."""
    clean = re.sub(r"[^a-zA-Z0-9_]", "_", name)
    if not clean or clean[0].isdigit():
        clean = "geom_" + clean
    return clean

def compute_domain_bounds(
    bbox: BoundingBox, margin: DomainMargin, workflow_type: WorkflowType
) -> Tuple[BoundingBox, Tuple[int, int, int], Tuple[float, float, float]]:
    """Calculates background domain bounds, cell counts, and default locationInMesh."""
    # Ensure minimum non-zero dimensions to prevent division by zero or collapsed boxes
    dim_x = max(bbox.dim_x, 1e-4)
    dim_y = max(bbox.dim_y, 1e-4)
    dim_z = max(bbox.dim_z, 1e-4)

    if workflow_type == WorkflowType.EXTERNAL_FLOW:
        # Wind tunnel / external flow margins
        d_min_x = bbox.min_x - (dim_x * margin.min_x_multiplier)
        d_max_x = bbox.max_x + (dim_x * margin.max_x_multiplier)
        d_min_y = bbox.min_y - (dim_y * margin.min_y_multiplier)
        d_max_y = bbox.max_y + (dim_y * margin.max_y_multiplier)
        d_min_z = bbox.min_z - (dim_z * margin.min_z_multiplier)
        d_max_z = bbox.max_z + (dim_z * margin.max_z_multiplier)

        # External keep-point: in the outer margin space
        loc_x = d_min_x + (dim_x * margin.min_x_multiplier * 0.4)
        loc_y = bbox.min_y + (dim_y * 0.5)
        loc_z = bbox.min_z + (dim_z * 0.5)

    elif workflow_type == WorkflowType.INTERNAL_FLOW:
        # Internal flow domain tightly bounding or enclosing the geometry
        d_min_x = bbox.min_x - (dim_x * 0.1)
        d_max_x = bbox.max_x + (dim_x * 0.1)
        d_min_y = bbox.min_y - (dim_y * 0.1)
        d_max_y = bbox.max_y + (dim_y * 0.1)
        d_min_z = bbox.min_z - (dim_z * 0.1)
        d_max_z = bbox.max_z + (dim_z * 0.1)

        # Internal keep-point: center of bounding box
        loc_x = (bbox.min_x + bbox.max_x) * 0.5
        loc_y = (bbox.min_y + bbox.max_y) * 0.5
        loc_z = (bbox.min_z + bbox.max_z) * 0.5

    else:  # GENERIC_SURFACE
        d_min_x = bbox.min_x - (dim_x * margin.min_x_multiplier)
        d_max_x = bbox.max_x + (dim_x * margin.max_x_multiplier)
        d_min_y = bbox.min_y - (dim_y * margin.min_y_multiplier)
        d_max_y = bbox.max_y + (dim_y * margin.max_y_multiplier)
        d_min_z = bbox.min_z - (dim_z * margin.min_z_multiplier)
        d_max_z = bbox.max_z + (dim_z * margin.max_z_multiplier)

        loc_x = d_min_x + (dim_x * margin.min_x_multiplier * 0.5)
        loc_y = d_min_y + (dim_y * margin.min_y_multiplier * 0.5)
        loc_z = d_min_z + (dim_z * margin.min_z_multiplier * 0.5)

    domain_bbox = BoundingBox(
        min_x=d_min_x,
        min_y=d_min_y,
        min_z=d_min_z,
        max_x=d_max_x,
        max_y=d_max_y,
        max_z=d_max_z,
        dim_x=d_max_x - d_min_x,
        dim_y=d_max_y - d_min_y,
        dim_z=d_max_z - d_min_z,
    )

    return domain_bbox, (loc_x, loc_y, loc_z)

def generate_control_dict() -> str:
    """Generates system/controlDict."""
    return """/*--------------------------------*- C++ -*----------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  v2506                                 |
|   \\\\  /    A nd           | Website:  www.openfoam.com                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      controlDict;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

application     snappyHexMesh;
startFrom       startTime;
startTime       0;
stopAt          endTime;
endTime         1;
deltaT          1;
writeControl    timeStep;
writeInterval   1;
purgeWrite      0;
writeFormat     ascii;
writePrecision  6;
writeCompression off;
timeFormat      general;
timePrecision   6;
runTimeModifiable true;

// ************************************************************************* //
"""

def generate_fv_schemes() -> str:
    """Generates system/fvSchemes."""
    return """/*--------------------------------*- C++ -*----------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  v2506                                 |
|   \\\\  /    A nd           | Website:  www.openfoam.com                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      fvSchemes;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

ddtSchemes
{
    default         Euler;
}

gradSchemes
{
    default         Gauss linear;
    grad(p)         Gauss linear;
}

divSchemes
{
    default         none;
    div(phi,U)      Gauss linear;
}

laplacianSchemes
{
    default         Gauss linear orthogonal;
}

interpolationSchemes
{
    default         linear;
}

snGradSchemes
{
    default         orthogonal;
}

// ************************************************************************* //
"""

def generate_fv_solution() -> str:
    """Generates system/fvSolution."""
    return """/*--------------------------------*- C++ -*----------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  v2506                                 |
|   \\\\  /    A nd           | Website:  www.openfoam.com                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      fvSolution;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

solvers
{
    p
    {
        solver          PCG;
        preconditioner  DIC;
        tolerance       1e-06;
        relTol          0.05;
    }

    pFinal
    {
        $p;
        relTol          0;
    }

    U
    {
        solver          smoothSolver;
        smoother        symGaussSeidel;
        tolerance       1e-05;
        relTol          0;
    }
}

SIMPLE
{
    nNonOrthogonalCorrectors 0;
}

// ************************************************************************* //
"""

def generate_mesh_quality_dict() -> str:
    """Generates system/meshQualityDict."""
    return """/*--------------------------------*- C++ -*----------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  v2506                                 |
|   \\\\  /    A nd           | Website:  www.openfoam.com                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      meshQualityDict;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

#includeEtc "caseDicts/meshQualityDict"

// Relaxed face weight for snappyHexMesh stability
minFaceWeight 0.02;

// ************************************************************************* //
"""

def generate_block_mesh_dict(
    domain_bbox: BoundingBox, cells_x: int, cells_y: int, cells_z: int
) -> str:
    """Generates system/blockMeshDict with hex topology and patch boundaries."""
    return f"""/*--------------------------------*- C++ -*----------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  v2506                                 |
|   \\\\  /    A nd           | Website:  www.openfoam.com                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      blockMeshDict;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

scale   1;

vertices
(
    ({domain_bbox.min_x:.6f} {domain_bbox.min_y:.6f} {domain_bbox.min_z:.6f}) // 0
    ({domain_bbox.max_x:.6f} {domain_bbox.min_y:.6f} {domain_bbox.min_z:.6f}) // 1
    ({domain_bbox.max_x:.6f} {domain_bbox.max_y:.6f} {domain_bbox.min_z:.6f}) // 2
    ({domain_bbox.min_x:.6f} {domain_bbox.max_y:.6f} {domain_bbox.min_z:.6f}) // 3
    ({domain_bbox.min_x:.6f} {domain_bbox.min_y:.6f} {domain_bbox.max_z:.6f}) // 4
    ({domain_bbox.max_x:.6f} {domain_bbox.min_y:.6f} {domain_bbox.max_z:.6f}) // 5
    ({domain_bbox.max_x:.6f} {domain_bbox.max_y:.6f} {domain_bbox.max_z:.6f}) // 6
    ({domain_bbox.min_x:.6f} {domain_bbox.max_y:.6f} {domain_bbox.max_z:.6f}) // 7
);

blocks
(
    hex (0 1 2 3 4 5 6 7) ({cells_x} {cells_y} {cells_z}) simpleGrading (1 1 1)
);

edges ();

boundary
(
    inlet
    {{
        type patch;
        faces
        (
            (0 4 7 3)
        );
    }}
    outlet
    {{
        type patch;
        faces
        (
            (1 2 6 5)
        );
    }}
    bottom
    {{
        type wall;
        faces
        (
            (0 1 5 4)
        );
    }}
    top
    {{
        type patch;
        faces
        (
            (3 7 6 2)
        );
    }}
    front
    {{
        type patch;
        faces
        (
            (0 3 2 1)
        );
    }}
    back
    {{
        type patch;
        faces
        (
            (4 5 6 7)
        );
    }}
);

// ************************************************************************* //
"""

def generate_surface_feature_extract_dict(
    stl_filename: str, included_angle: float
) -> str:
    """Generates system/surfaceFeatureExtractDict."""
    return f"""/*--------------------------------*- C++ -*----------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  v2506                                 |
|   \\\\  /    A nd           | Website:  www.openfoam.com                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      surfaceFeatureExtractDict;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

{stl_filename}
{{
    extractionMethod    extractFromSurface;
    includedAngle       {included_angle:.1f};

    subsetFeatures
    {{
        nonManifoldEdges   no;
        openEdges          yes;
    }}

    writeObj            yes;
}}

// ************************************************************************* //
"""

def generate_snappy_hex_mesh_dict(
    stl_filename: str,
    surface_name: str,
    feature_file: Optional[str],
    config: MeshJobCreateRequest,
    location_in_mesh: Tuple[float, float, float],
) -> str:
    """Generates system/snappyHexMeshDict with validated typed controls."""
    features_block = ""
    if config.feature_refinement.enabled and feature_file:
        features_block = f"""
    features
    (
        {{
            file "{feature_file}";
            level {config.feature_refinement.level};
        }}
    );"""
    else:
        features_block = "\n    features ();"

    layers_enabled = "true" if config.boundary_layers.enabled else "false"
    layers_dict_block = ""
    if config.boundary_layers.enabled:
        layers_dict_block = f"""
    layers
    {{
        "{surface_name}"
        {{
            nSurfaceLayers {config.boundary_layers.n_surface_layers};
        }}
    }}"""
    else:
        layers_dict_block = "\n    layers {};"

    return f"""/*--------------------------------*- C++ -*----------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  v2506                                 |
|   \\\\  /    A nd           | Website:  www.openfoam.com                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      snappyHexMeshDict;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

castellatedMesh true;
snap            true;
addLayers       {layers_enabled};

geometry
{{
    {stl_filename}
    {{
        type triSurfaceMesh;
        name {surface_name};
    }}
}}

castellatedMeshControls
{{
    maxLocalCells 100000;
    maxGlobalCells 2000000;
    minRefinementCells 10;
    maxLoadUnbalance 0.10;
    nCellsBetweenLevels 2;
{features_block}

    refinementSurfaces
    {{
        {surface_name}
        {{
            level ({config.surface_refinement.min_level} {config.surface_refinement.max_level});
            patchInfo
            {{
                type wall;
            }}
        }}
    }}

    resolveFeatureAngle {config.resolve_feature_angle:.1f};

    refinementRegions {{}}

    locationInMesh ({location_in_mesh[0]:.6f} {location_in_mesh[1]:.6f} {location_in_mesh[2]:.6f});

    allowFreeStandingZoneFaces true;
}}

snapControls
{{
    nSmoothPatch 3;
    tolerance 2.0;
    nSolveIter {config.snap_iterations};
    nRelaxIter 5;
    nFeatureSnapIter 10;
    implicitFeatureSnap false;
    explicitFeatureSnap true;
    multiRegionFeatureSnap false;
}}

addLayersControls
{{{layers_dict_block}
    relativeSizes true;
    expansionRatio {config.boundary_layers.expansion_ratio:.2f};
    finalLayerThickness {config.boundary_layers.final_layer_thickness:.2f};
    minThickness {config.boundary_layers.min_thickness:.3f};
    nGrow 0;
    featureAngle 60;
    slipFeatureAngle 30;
    nRelaxIter 3;
    nSmoothSurfaceNormals 1;
    nSmoothNormals 3;
    nSmoothThickness 10;
    maxFaceThicknessRatio 0.5;
    maxThicknessToMedialRatio 0.3;
    minMedialAxisAngle 90;
    nBufferCellsNoExtrude 0;
    nLayerIter 50;
}}

meshQualityControls
{{
    #include "meshQualityDict"
    maxNonOrtho {config.max_non_ortho:.1f};
    maxBoundarySkewness {config.max_skewness:.1f};
    maxInternalSkewness {config.max_skewness:.1f};
    nSmoothScale 4;
    errorReduction 0.75;
}}

mergeTolerance 1e-6;

// ************************************************************************* //
"""

def generate_runner_script(
    stl_filename: str, has_features: bool
) -> str:
    """Generates the container run_mesh.sh entrypoint script."""
    feature_cmd = "echo \"=== STAGE: surfaceFeatureExtract ===\"\nsurfaceFeatureExtract" if has_features else "echo \"=== STAGE: surfaceFeatureExtract skipped ===\""

    return f"""#!/bin/bash
source /opt/OpenFOAM-v2506/etc/bashrc
set -e
cd /workspace

echo "=== STAGE: surfaceCheck ==="
surfaceCheck constant/triSurface/{stl_filename}

{feature_cmd}

echo "=== STAGE: blockMesh ==="
blockMesh

echo "=== STAGE: snappyHexMesh ==="
snappyHexMesh -overwrite

echo "=== STAGE: checkMesh ==="
checkMesh

echo "=== ALL COMPLETE ==="
"""

def write_case_files(
    job_dir: Path,
    stl_source_path: Path,
    config: MeshJobCreateRequest,
    bbox: BoundingBox,
) -> Dict[str, Any]:
    """Generates and writes all required case dictionaries and scripts into job_dir."""
    system_dir = job_dir / "system"
    constant_dir = job_dir / "constant"
    tri_surface_dir = constant_dir / "triSurface"

    (job_dir / "0").mkdir(parents=True, exist_ok=True)
    system_dir.mkdir(parents=True, exist_ok=True)
    tri_surface_dir.mkdir(parents=True, exist_ok=True)

    # Copy STL safely
    stl_filename = "geometry.stl"
    dest_stl = tri_surface_dir / stl_filename
    with open(stl_source_path, "rb") as src, open(dest_stl, "wb") as dst:
        dst.write(src.read())

    # Compute domain bounds and keep-point
    domain_bbox, default_keep_point = compute_domain_bounds(
        bbox, config.domain_margin, config.workflow_type
    )

    keep_point = config.location_in_mesh or default_keep_point

    # Write system dictionaries
    (system_dir / "controlDict").write_text(generate_control_dict(), encoding="utf-8")
    (system_dir / "fvSchemes").write_text(generate_fv_schemes(), encoding="utf-8")
    (system_dir / "fvSolution").write_text(generate_fv_solution(), encoding="utf-8")
    (system_dir / "meshQualityDict").write_text(generate_mesh_quality_dict(), encoding="utf-8")
    (system_dir / "blockMeshDict").write_text(
        generate_block_mesh_dict(
            domain_bbox,
            config.target_cells_x,
            config.target_cells_y,
            config.target_cells_z,
        ),
        encoding="utf-8",
    )

    surface_name = "geometry"
    e_mesh_name = "geometry.eMesh" if config.feature_refinement.enabled else None

    if config.feature_refinement.enabled:
        (system_dir / "surfaceFeatureExtractDict").write_text(
            generate_surface_feature_extract_dict(
                stl_filename, config.feature_refinement.included_angle
            ),
            encoding="utf-8",
        )

    (system_dir / "snappyHexMeshDict").write_text(
        generate_snappy_hex_mesh_dict(
            stl_filename=stl_filename,
            surface_name=surface_name,
            feature_file=e_mesh_name,
            config=config,
            location_in_mesh=keep_point,
        ),
        encoding="utf-8",
    )

    # Write runner script with UNIX newlines
    runner_path = job_dir / "run_mesh.sh"
    runner_content = generate_runner_script(
        stl_filename=stl_filename,
        has_features=config.feature_refinement.enabled,
    )
    with open(runner_path, "wb") as f:
        f.write(runner_content.replace("\r\n", "\n").encode("utf-8"))

    return {
        "domain_bbox": domain_bbox,
        "location_in_mesh": keep_point,
        "estimated_cells": config.target_cells_x * config.target_cells_y * config.target_cells_z,
    }
