import React, { useEffect, useState } from "react";
import {
  CheckCircle2,
  AlertTriangle,
  Download,
  RotateCcw,
  Box,
  Layers,
  FileText,
} from "lucide-react";
import { api } from "../services/api";
import { JobStatusResponse, MeshStatsResponse } from "../types";
import { CaseControls } from "./CaseControls";

interface ResultsViewProps {
  jobId: string;
  onNewJob: () => void;
  onRemesh: () => void;
}

export const ResultsView: React.FC<ResultsViewProps> = ({ jobId, onNewJob, onRemesh }) => {
  const [results, setResults] = useState<MeshStatsResponse | null>(null);
  const [job, setJob] = useState<JobStatusResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchResults = async () => {
      try {
        const [data, jobData] = await Promise.all([api.getMeshResults(jobId), api.getJob(jobId)]);
        setResults(data);
        setJob(jobData);
      } catch (err: any) {
        setError(err.message || "Failed to load mesh results.");
      }
    };
    fetchResults();
  }, [jobId]);

  if (error) {
    return (
      <div className="card" style={{ maxWidth: 900, margin: "0 auto" }}>
        <div className="alert alert-danger">
          <AlertTriangle size={20} />
          <div>
            <div style={{ fontWeight: 600 }}>Error Loading Mesh Results</div>
            <div>{error}</div>
          </div>
        </div>
        <button className="btn btn-secondary" onClick={onNewJob}>
          <RotateCcw size={16} />
          Start New Job
        </button>
      </div>
    );
  }

  if (!results) {
    return (
      <div className="card text-center" style={{ maxWidth: 900, margin: "0 auto", padding: 60 }}>
        <div className="text-cyan font-mono">Loading mesh metrics...</div>
      </div>
    );
  }

  const downloadUrl = api.getDownloadUrl(jobId);

  return (
    <div style={{ maxWidth: 1050, margin: "0 auto" }}>
      {/* Top Hero Banner */}
      <div className="card" style={{ marginBottom: 24 }}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            flexWrap: "wrap",
            gap: 16,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
            <div
              style={{
                width: 48,
                height: 48,
                borderRadius: "50%",
                background: results.mesh_ok ? "var(--success-bg)" : "var(--warning-bg)",
                color: results.mesh_ok ? "var(--success)" : "var(--warning)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              {results.mesh_ok ? <CheckCircle2 size={28} /> : <AlertTriangle size={28} />}
            </div>
            <div>
              <h2 style={{ fontSize: "1.4rem" }}>
                {results.mesh_ok ? "Mesh ready" : "Mesh generated with warnings"}
              </h2>
            </div>
          </div>

          <div style={{ display: "flex", gap: 12 }}>
            <a href={downloadUrl} className="btn btn-secondary" download>
              <Download size={16} />
              Download ZIP
            </a>
            <button className="btn btn-secondary" onClick={onNewJob}>
              <RotateCcw size={16} />
              New Job
            </button>
          </div>
        </div>
        {job && <CaseControls job={job} onRemesh={onRemesh} />}
      </div>

      {/* Metrics Grid */}
      <div className="metrics-grid">
        <div className="metric-card">
          <div className="metric-label">Total Cells</div>
          <div className="metric-value font-mono text-cyan">
            {results.num_cells.toLocaleString()}
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-label">Points / Vertices</div>
          <div className="metric-value font-mono">
            {results.num_points.toLocaleString()}
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-label">Faces (Internal / Total)</div>
          <div className="metric-value font-mono" style={{ fontSize: "1.2rem", paddingTop: 4 }}>
            {results.num_internal_faces.toLocaleString()} / {results.num_faces.toLocaleString()}
          </div>
        </div>

      </div>

      <details className="card disclosure">
        <summary>Mesh details</summary>
        <div className="metrics-grid">
          <div className="metric-card">
            <div className="metric-label">Max Non-Orthogonality</div>
            <div
              className={`metric-value font-mono ${
                results.max_non_ortho && results.max_non_ortho > 70 ? "text-warning" : "text-success"
              }`}
            >
              {results.max_non_ortho !== null && results.max_non_ortho !== undefined
                ? `${results.max_non_ortho.toFixed(1)}°`
                : "N/A"}
            </div>
          </div>

          <div className="metric-card">
            <div className="metric-label">Max Skewness</div>
            <div
              className={`metric-value font-mono ${
                results.max_skewness && results.max_skewness > 4.0 ? "text-warning" : "text-success"
              }`}
            >
              {results.max_skewness !== null && results.max_skewness !== undefined
                ? results.max_skewness.toFixed(2)
                : "N/A"}
            </div>
          </div>

          <div className="metric-card">
            <div className="metric-label">Max Aspect Ratio</div>
            <div className="metric-value font-mono">
              {results.max_aspect_ratio !== null && results.max_aspect_ratio !== undefined
                ? results.max_aspect_ratio.toFixed(2)
                : "N/A"}
            </div>
          </div>
        </div>
        {/* Cell Types Breakdown & Domain Bounds */}
        <div className="result-details">
          <div className="card">
            <h4 style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 16 }}>
              <Layers size={18} className="text-cyan" />
              Cell Type Distribution
            </h4>
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {Object.entries(results.cell_types).map(([typeName, count]) => {
                const pct = results.num_cells > 0 ? ((count / results.num_cells) * 100).toFixed(1) : "0";
                return (
                  <div key={typeName}>
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        fontSize: "0.85rem",
                        marginBottom: 4,
                      }}
                    >
                      <span style={{ textTransform: "capitalize" }}>{typeName}</span>
                      <span className="font-mono text-muted">
                        {count.toLocaleString()} ({pct}%)
                      </span>
                    </div>
                    <div
                      style={{
                        height: 6,
                        background: "var(--bg-input)",
                        borderRadius: 3,
                        overflow: "hidden",
                      }}
                    >
                      <div
                        style={{
                          width: `${pct}%`,
                          height: "100%",
                          background:
                            typeName === "hexahedra"
                              ? "var(--accent-cyan)"
                              : typeName === "polyhedra"
                              ? "var(--accent-indigo)"
                              : "var(--text-muted)",
                        }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="card">
            <h4 style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 16 }}>
              <Box size={18} className="text-cyan" />
              Mesh Bounding Box & Volume
            </h4>
            {results.bounding_box ? (
              <div className="font-mono" style={{ fontSize: "0.85rem", display: "flex", flexDirection: "column", gap: 8 }}>
                <div>
                  <span className="text-dim">Min: </span>
                  ({results.bounding_box.min_x.toFixed(4)}, {results.bounding_box.min_y.toFixed(4)},{" "}
                  {results.bounding_box.min_z.toFixed(4)})
                </div>
                <div>
                  <span className="text-dim">Max: </span>
                  ({results.bounding_box.max_x.toFixed(4)}, {results.bounding_box.max_y.toFixed(4)},{" "}
                  {results.bounding_box.max_z.toFixed(4)})
                </div>
                <div>
                  <span className="text-dim">Dims: </span>
                  {results.bounding_box.dim_x.toFixed(4)} × {results.bounding_box.dim_y.toFixed(4)} ×{" "}
                  {results.bounding_box.dim_z.toFixed(4)} m
                </div>
                {results.total_volume !== null && results.total_volume !== undefined && (
                  <div style={{ marginTop: 8, paddingTop: 8, borderTop: "1px solid var(--border-color)" }}>
                    <span className="text-dim">Total Fluid Volume: </span>
                    <span className="text-cyan">{results.total_volume.toFixed(6)} m³</span>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-muted">Bounding box not available in checkMesh output.</div>
            )}
          </div>
        </div>

        {results.raw_summary && (
          <details className="disclosure">
            <summary><FileText size={14} /> checkMesh output</summary>
            <pre className="terminal-console">{results.raw_summary}</pre>
          </details>
        )}
      </details>
    </div>
  );
};
