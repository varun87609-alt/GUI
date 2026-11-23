import React from "react";
import { BookOpen, ShieldCheck, Cpu, AlertTriangle, Layers, Terminal } from "lucide-react";

export const DocumentationView: React.FC = () => {
  return (
    <div style={{ maxWidth: 1000, margin: "0 auto" }}>
      <div className="card" style={{ marginBottom: 24 }}>
        <h2 style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
          <BookOpen className="text-cyan" size={24} />
          Automated OpenFOAM STL Meshing Guide
        </h2>
        <p className="text-muted" style={{ lineHeight: 1.7 }}>
          This application automatically converts an uploaded STL surface into an OpenFOAM polyhedral
          hexahedron-dominant computational grid using OpenFOAM v2506's <code>blockMesh</code> and{" "}
          <code>snappyHexMesh</code> tools inside an isolated container.
        </p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24, marginBottom: 24 }}>
        <div className="card">
          <h3 style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 14 }}>
            <Layers className="text-cyan" size={20} />
            CFD Pipeline Stages
          </h3>
          <ol style={{ paddingLeft: 20, fontSize: "0.875rem", lineHeight: 1.8, color: "var(--text-muted)" }}>
            <li>
              <strong style={{ color: "var(--text-main)" }}>1. STL Geometry Validation:</strong> Checks for NaN/Inf
              coordinates, watertightness, degenerate faces, and aspect ratios.
            </li>
            <li>
              <strong style={{ color: "var(--text-main)" }}>2. Domain Computation:</strong> Calculates bounding box
              and expands external wind-tunnel domain with upstream and wake margins.
            </li>
            <li>
              <strong style={{ color: "var(--text-main)" }}>3. Dictionary Generation:</strong> Generates typed{" "}
              <code>blockMeshDict</code>, <code>snappyHexMeshDict</code>, and <code>controlDict</code>.
            </li>
            <li>
              <strong style={{ color: "var(--text-main)" }}>4. Feature Extraction:</strong> Runs{" "}
              <code>surfaceFeatureExtract</code> to preserve sharp geometry edges.
            </li>
            <li>
              <strong style={{ color: "var(--text-main)" }}>5. SnappyHexMesh:</strong> Castellates, refines, and snaps
              the hex background grid onto the STL surface.
            </li>
            <li>
              <strong style={{ color: "var(--text-main)" }}>6. CheckMesh Validation:</strong> Validates face
              orthogonality, skewness, aspect ratios, and ensures topology is manifold.
            </li>
          </ol>
        </div>

        <div className="card">
          <h3 style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 14 }}>
            <ShieldCheck className="text-cyan" size={20} />
            Security & Isolation Architecture
          </h3>
          <ul style={{ paddingLeft: 20, fontSize: "0.875rem", lineHeight: 1.8, color: "var(--text-muted)" }}>
            <li>
              <strong style={{ color: "var(--text-main)" }}>Container Sandboxing:</strong> Each job runs in an
              isolated Docker container with <code>no-new-privileges</code> and zero network access (<code>network_mode: none</code>).
            </li>
            <li>
              <strong style={{ color: "var(--text-main)" }}>Path Traversal Prevention:</strong> Client filenames are
              never trusted. UUIDs are used for all disk staging.
            </li>
            <li>
              <strong style={{ color: "var(--text-main)" }}>Resource Limits:</strong> Bounded concurrency (2 jobs max),
              memory limits (4GB), and hard execution timeouts prevent server exhaustion.
            </li>
            <li>
              <strong style={{ color: "var(--text-main)" }}>No Arbitrary Shell:</strong> Dictionaries are serialized
              from validated typed schemas; arbitrary user script execution is prevented.
            </li>
          </ul>
        </div>
      </div>

      <div className="card">
        <h3 style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 14 }}>
          <AlertTriangle className="text-warning" size={20} />
          Common Troubleshooting & Solutions
        </h3>
        <div style={{ display: "flex", flexDirection: "column", gap: 14, fontSize: "0.875rem" }}>
          <div>
            <div style={{ fontWeight: 600, color: "var(--text-main)" }}>Docker Daemon Disconnected:</div>
            <div className="text-muted">
              Ensure Docker Desktop is running on Windows. Verify with <code>docker ps</code> in PowerShell.
            </div>
          </div>
          <div>
            <div style={{ fontWeight: 600, color: "var(--text-main)" }}>SnappyHexMesh "locationInMesh" Warning:</div>
            <div className="text-muted">
              For external flow, the keep-point must reside strictly outside the geometry inside the background domain.
              For internal flow, it must reside inside the enclosed cavity.
            </div>
          </div>
          <div>
            <div style={{ fontWeight: 600, color: "var(--text-main)" }}>Non-Watertight Geometry:</div>
            <div className="text-muted">
              Open boundaries in STL files will cause internal flow mesh generation to leak into the outer domain.
              Ensure your CAD export forms a closed solid body.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
