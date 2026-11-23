# OpenFOAM AutoMesh - Troubleshooting and Diagnostic Manual

This manual provides diagnostic steps and fixes for common operational, container, and OpenFOAM execution errors.

---

## 1. Docker & Container Issues

### Issue: "Docker daemon not reachable" / Docker Offline
- **Cause**: Docker Desktop is not running or the Windows named pipe is blocked.
- **Solution**:
  1. Open Docker Desktop on Windows.
  2. Verify daemon status in PowerShell:
     ```powershell
     docker ps
     ```
  3. Ensure "Use the WSL 2 based engine" is enabled in Docker Desktop Settings -> General.

### Issue: "OpenFOAM image missing"
- **Cause**: The container image `openeuler/openfoam:2506-oe2403sp4` is not present in local Docker storage.
- **Solution**:
  Pull or verify the image:
  ```powershell
  docker pull openeuler/openfoam:2506-oe2403sp4
  docker images | findstr openfoam
  ```

### Issue: Container hangs or halts with `pop_var_context` error
- **Cause**: In bash, calling `set -e` *before* `source /opt/OpenFOAM-v2506/etc/bashrc` causes shell variable scope conflicts inside OpenFOAM's setup script (`/opt/OpenFOAM-v2506/etc/config.sh/setup: line 207: pop_var_context: head of shell_variables not a function context`).
- **Solution**: Always source the OpenFOAM environment *before* enabling strict error modes:
  ```bash
  #!/bin/bash
  source /opt/OpenFOAM-v2506/etc/bashrc
  set -e
  ```

### Issue: Container stays running indefinitely (interactive shell hang)
- **Cause**: The `openeuler/openfoam:2506-oe2403sp4` image sets entrypoint `["/bin/bash", "-c", "source etc/bashrc && exec /bin/bash"]`, launching an interactive shell if not overridden.
- **Solution**: Always specify `--entrypoint /bin/bash` when invoking `docker run` or Docker SDK.

---

## 2. Geometry & Upload Issues

### Issue: "Geometry contains non-finite coordinates (NaN or Inf)"
- **Cause**: The CAD software exported uninitialized floating point numbers or corrupted facet normals.
- **Solution**: Re-export the geometry from CAD using standard binary or ASCII STL with clean vertex coordinates.

### Issue: "Maximum dimension is very small (< 0.005 m)"
- **Cause**: OpenFOAM interprets numbers in meters. A CAD model exported in millimeters (e.g. 10 mm length exported as 10 units) will be treated as a 10-millimeter miniature (0.01 m).
- **Solution**: Ensure your geometry is scaled appropriately before uploading. If 1 unit = 1 meter, confirm your physical dimensions.

### Issue: "Geometry is not watertight"
- **Cause**: The STL has holes, unclosed boundary edges, or non-manifold edges where three or more triangles share an edge.
- **Solution**:
  - For **External Flow**: SnappyHexMesh can still snap to open surfaces (like thin plates or shells).
  - For **Internal Flow**: The geometry *must* be closed; otherwise the fluid extraction will leak into the surrounding box.

---

## 3. OpenFOAM Execution Failures

### Issue: `blockMesh` fails with "Cannot find file system/fvSchemes"
- **Cause**: OpenFOAM requires `system/fvSchemes` and `system/fvSolution` to exist in the case directory even for pre-processing utilities like `checkMesh`.
- **Solution**: The application automatically generates valid default `fvSchemes` and `fvSolution` files in `system/`.

### Issue: `snappyHexMesh` fails with "Point (x y z) is not inside any mesh cell"
- **Cause**: The keep-point `locationInMesh` falls exactly on a face boundary, outside the domain, or inside a solid body for external flow.
- **Solution**: Adjust the `location_in_mesh` coordinates in the configuration form or rely on the automatic keep-point calculation.

### Issue: Job times out or container terminated with exit code 137 (OOM)
- **Cause**: The cell count grew excessively large during high refinement levels, exceeding container RAM (4GB limit).
- **Solution**:
  1. Reduce surface refinement levels (e.g. from 3-4 down to 1-2).
  2. Increase the target base cell size (decrease `cells_x`, `cells_y`, `cells_z`).
  3. Increase container memory limit in `.env` if your system has sufficient RAM:
     ```env
     CONTAINER_MEM_LIMIT=8g
     ```
