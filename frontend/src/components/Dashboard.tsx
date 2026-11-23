import React, { useEffect, useRef, useState } from "react";
import { FolderOpen, Plus, RefreshCw } from "lucide-react";
import { api } from "../services/api";
import { JobStatusResponse } from "../types";

interface DashboardProps {
  onSelectJob: (jobId: string) => void;
  onNewJob: () => void;
}

export const Dashboard: React.FC<DashboardProps> = ({ onSelectJob, onNewJob }) => {
  const [jobs, setJobs] = useState<JobStatusResponse[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState<boolean>(true);
  const [clearing, setClearing] = useState(false);
  const fetchSequence = useRef(0);

  const fetchData = async () => {
    const sequence = ++fetchSequence.current;
    try {
      setLoading(true);
      const entries = await api.getJobs(20);
      if (sequence === fetchSequence.current) setJobs(entries);
    } catch {
      if (sequence === fetchSequence.current) setError("Could not load jobs.");
    } finally {
      if (sequence === fetchSequence.current) setLoading(false);
    }
  };

  const clearHistory = async (jobId?: string) => {
    if (!jobId && !window.confirm("Clear all finished jobs from history? Saved case files will stay on disk.")) {
      return;
    }
    setClearing(true);
    setError("");
    try {
      await api.clearJobHistory(jobId);
      await fetchData();
    } catch (error) {
      setError(error instanceof Error ? error.message : "Could not clear history.");
    } finally {
      setClearing(false);
    }
  };

  const openFolder = async (jobId: string) => {
    setError("");
    try {
      await api.openCaseFolder(jobId);
    } catch (error) {
      setError(error instanceof Error ? error.message : "Could not open the saved folder.");
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div style={{ maxWidth: 1200, margin: "0 auto" }}>
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">
            Saved jobs
          </h3>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 10 }}>
            <button className="btn btn-secondary" onClick={fetchData} disabled={loading} style={{ padding: "6px 12px", fontSize: "0.8rem" }}>
              <RefreshCw size={14} aria-hidden="true" />
              Refresh
            </button>
            <button
              className="btn btn-secondary"
              onClick={() => clearHistory()}
              disabled={clearing || !jobs.some((job) => job.status !== "queued" && job.status !== "running")}
            >
              Clear all history
            </button>
            <button className="btn btn-primary" onClick={onNewJob} style={{ padding: "6px 14px", fontSize: "0.85rem" }}>
              <Plus size={14} />
              New mesh
            </button>
          </div>
        </div>

        {error && <p role="alert" className="alert alert-danger">{error}</p>}
        {jobs.length === 0 ? (
          <div className="text-muted" style={{ padding: "20px 0" }}>
            {loading ? "Loading jobs..." : "No mesh jobs yet."}
          </div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left", fontSize: "0.875rem" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid var(--border-color)", color: "var(--text-muted)" }}>
                  <th style={{ padding: "12px 16px" }}>Geometry</th>
                  <th style={{ padding: "12px 16px" }}>Workflow</th>
                  <th style={{ padding: "12px 16px" }}>Status</th>
                  <th style={{ padding: "12px 16px" }}>Elapsed</th>
                  <th style={{ padding: "12px 16px", textAlign: "right" }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {jobs.map((job) => {
                  let statusBadgeColor = "var(--text-dim)";
                  if (job.status === "completed") statusBadgeColor = "var(--success)";
                  else if (job.status === "running") statusBadgeColor = "var(--accent-cyan)";
                  else if (job.status === "failed") statusBadgeColor = "var(--danger)";
                  else if (job.status === "cancelled") statusBadgeColor = "var(--warning)";

                  return (
                    <tr
                      key={job.job_id}
                      style={{
                        borderBottom: "1px solid var(--border-color)",
                        transition: "background 0.15s",
                      }}
                      className="table-row-hover"
                    >
                      <td style={{ padding: "14px 16px", fontWeight: 500 }}>
                        {job.filename}
                        {job.case_folder && <div className="text-muted">{job.case_folder}</div>}
                      </td>
                      <td style={{ padding: "14px 16px", textTransform: "capitalize", color: "var(--text-muted)" }}>
                        {job.workflow_type.replace("_", " ")}
                      </td>
                      <td style={{ padding: "14px 16px" }}>
                        <span
                          style={{
                            display: "inline-block",
                            padding: "3px 8px",
                            borderRadius: 4,
                            fontSize: "0.75rem",
                            fontWeight: 600,
                            textTransform: "uppercase",
                            background: `rgba(255, 255, 255, 0.05)`,
                            color: statusBadgeColor,
                            border: `1px solid ${statusBadgeColor}40`,
                          }}
                        >
                          {job.status}
                        </span>
                      </td>
                      <td className="font-mono text-muted" style={{ padding: "14px 16px" }}>
                        {job.elapsed_seconds ? `${job.elapsed_seconds}s` : "-"}
                      </td>
                      <td style={{ padding: "14px 16px", textAlign: "right" }}>
                        <button
                          className="btn btn-secondary"
                          style={{ padding: "4px 10px", fontSize: "0.75rem" }}
                          onClick={() => onSelectJob(job.job_id)}
                        >
                          View
                        </button>
                        {job.case_path && (
                          <button
                            className="btn btn-secondary"
                            style={{ padding: "4px 10px", fontSize: "0.75rem", marginLeft: 6 }}
                            onClick={() => openFolder(job.job_id)}
                          >
                            <FolderOpen size={13} /> Open folder
                          </button>
                        )}
                        {job.status !== "queued" && job.status !== "running" && (
                          <button
                            className="btn btn-secondary"
                            style={{ padding: "4px 10px", fontSize: "0.75rem", marginLeft: 6 }}
                            aria-label={`Clear ${job.case_folder ?? job.filename} from history`}
                            onClick={() => clearHistory(job.job_id)}
                            disabled={clearing}
                          >
                            Clear
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
