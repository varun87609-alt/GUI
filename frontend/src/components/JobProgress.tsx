import React, { useEffect, useState, useRef } from "react";
import {
  Clock,
  Terminal,
  AlertCircle,
  StopCircle,
  ArrowRight,
  Copy,
  Check,
} from "lucide-react";
import { api } from "../services/api";
import { JobStatusResponse, PipelineStage } from "../types";
import { CaseControls } from "./CaseControls";

interface JobProgressProps {
  jobId: string;
  onJobComplete: () => void;
  onRemesh: () => void;
}

const STAGES: { key: PipelineStage; label: string }[] = [
  { key: "upload", label: "Staging" },
  { key: "dict_generation", label: "Dict Gen" },
  { key: "surface_check", label: "Surface Check" },
  { key: "feature_extract", label: "Features" },
  { key: "block_mesh", label: "BlockMesh" },
  { key: "snappy_hex_mesh", label: "SnappyHexMesh" },
  { key: "check_mesh", label: "CheckMesh" },
  { key: "packaging", label: "Package" },
  { key: "completed", label: "Complete" },
];

export const JobProgress: React.FC<JobProgressProps> = ({ jobId, onJobComplete, onRemesh }) => {
  const [job, setJob] = useState<JobStatusResponse | null>(null);
  const [logs, setLogs] = useState<string[]>([]);
  const [autoScroll, setAutoScroll] = useState<boolean>(true);
  const [isCopied, setIsCopied] = useState<boolean>(false);
  const [isCancelling, setIsCancelling] = useState<boolean>(false);

  const terminalRef = useRef<HTMLDivElement>(null);
  const logOffsetRef = useRef<number>(0);

  // Poll job status
  useEffect(() => {
    let intervalId: any;
    let active = true;

    const checkStatus = async () => {
      try {
        const data = await api.getJob(jobId);
        if (!active) return;
        setJob(data);

        if (data.status === "completed") {
          clearInterval(intervalId);
          onJobComplete();
        } else if (data.status === "failed" || data.status === "cancelled") {
          clearInterval(intervalId);
        }
      } catch (err) {
        console.error("Failed to fetch job status", err);
      }
    };

    checkStatus();
    intervalId = setInterval(checkStatus, 1500);

    return () => {
      active = false;
      clearInterval(intervalId);
    };
  }, [jobId, onJobComplete]);

  // Poll logs
  useEffect(() => {
    let logInterval: any;

    const fetchLogs = async () => {
      try {
        const logData = await api.getJobLogs(jobId, logOffsetRef.current);
        if (logData.lines.length > 0) {
          setLogs((prev) => [...prev, ...logData.lines]);
          logOffsetRef.current = logData.total_lines;
        }
      } catch (err) {
        console.error("Failed to fetch logs", err);
      }
    };

    fetchLogs();
    logInterval = setInterval(fetchLogs, 1000);

    return () => clearInterval(logInterval);
  }, [jobId]);

  // Autoscroll terminal
  useEffect(() => {
    if (autoScroll && terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [logs, autoScroll]);

  const handleCancel = async () => {
    if (confirm("Are you sure you want to cancel this meshing job?")) {
      setIsCancelling(true);
      try {
        await api.cancelJob(jobId);
      } catch (err) {
        console.error("Cancel failed", err);
      } finally {
        setIsCancelling(false);
      }
    }
  };

  const handleCopyLogs = () => {
    navigator.clipboard.writeText(logs.join("\n"));
    setIsCopied(true);
    setTimeout(() => setIsCopied(false), 2000);
  };

  const getStageIndex = (stage: PipelineStage): number => {
    const idx = STAGES.findIndex((s) => s.key === stage);
    return idx >= 0 ? idx : 0;
  };

  const currentStageIdx = job ? getStageIndex(job.stage) : 0;

  return (
    <div className="card" style={{ maxWidth: 1000, margin: "0 auto" }}>
      <div className="card-header">
        <div>
          <h3 className="card-title">
            <Terminal size={20} className="text-cyan" />
            Mesh run
          </h3>
          <div className="text-muted font-mono" style={{ fontSize: "0.8rem", marginTop: 4 }}>
            Job ID: {jobId}
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          {job?.elapsed_seconds !== undefined && (
            <div className="status-badge font-mono">
              <Clock size={14} className="text-cyan" />
              <span>{job.elapsed_seconds}s</span>
            </div>
          )}

          {(job?.status === "running" || job?.status === "queued") && (
            <button
              className="btn btn-danger"
              style={{ padding: "6px 12px", fontSize: "0.8rem" }}
              onClick={handleCancel}
              disabled={isCancelling}
            >
              <StopCircle size={14} />
              {isCancelling ? "Cancelling..." : "Cancel Job"}
            </button>
          )}

          {job?.status === "completed" && (
            <button
              className="btn btn-primary"
              style={{ padding: "6px 14px", fontSize: "0.85rem" }}
              onClick={onJobComplete}
            >
              View Mesh Results
              <ArrowRight size={14} />
            </button>
          )}
        </div>
      </div>

      {job && <CaseControls job={job} onRemesh={onRemesh} />}
      {(job?.status === "failed" || job?.status === "cancelled") && job.has_archive && (
        <a href={api.getDownloadUrl(jobId)} className="btn btn-secondary" download>
          Download last completed mesh
        </a>
      )}

      {job && (job.status === "queued" || job.status === "running") && (
        <p role="status" className="run-stage">
          {job.status === "queued" ? "Queued" : STAGES[currentStageIdx].label}
          {job.status === "running" && <span> · Step {currentStageIdx + 1} of {STAGES.length}</span>}
        </p>
      )}

      {/* Status Banner */}
      {job?.status === "failed" && (
        <div className="alert alert-danger">
          <AlertCircle size={20} />
          <div>
            <div style={{ fontWeight: 600 }}>Meshing Pipeline Failed</div>
            <div style={{ fontSize: "0.85rem", marginTop: 2 }}>{job.error_message}</div>
          </div>
        </div>
      )}

      {job?.status === "cancelled" && (
        <div className="alert alert-warning">
          <AlertCircle size={20} />
          <div>
            <div style={{ fontWeight: 600 }}>Job Cancelled</div>
            <div style={{ fontSize: "0.85rem", marginTop: 2 }}>Execution was halted by the user.</div>
          </div>
        </div>
      )}

      {/* Terminal Log Console */}
      <details className="disclosure">
        <summary>OpenFOAM log</summary>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: 8,
            fontSize: "0.8rem",
          }}
        >
          <span className="text-muted">{logs.length} lines</span>
          <div style={{ display: "flex", gap: 12 }}>
            <label style={{ display: "flex", alignItems: "center", gap: 6, cursor: "pointer" }}>
              <input
                type="checkbox"
                checked={autoScroll}
                onChange={(e) => setAutoScroll(e.target.checked)}
              />
              Auto-scroll
            </label>
            <button
              onClick={handleCopyLogs}
              style={{
                background: "transparent",
                border: "none",
                color: "var(--accent-cyan)",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: 4,
                fontSize: "0.8rem",
              }}
            >
              {isCopied ? <Check size={14} /> : <Copy size={14} />}
              {isCopied ? "Copied" : "Copy Log"}
            </button>
          </div>
        </div>

        <div className="terminal-console" ref={terminalRef}>
          {logs.length === 0 ? (
            <div className="text-dim" style={{ textAlign: "center", paddingTop: 40 }}>
              Connecting to container execution stream...
            </div>
          ) : (
            logs.map((line, idx) => {
              let lineType = "default";
              if (line.includes("=== STAGE:")) lineType = "stage";
              else if (line.includes("Mesh OK.") || line.includes("=== ALL COMPLETE ===")) lineType = "ok";
              else if (line.includes("Warning") || line.includes("warn")) lineType = "warn";
              else if (line.includes("FATAL") || line.includes("Error") || line.includes("failed"))
                lineType = "error";

              return (
                <div key={idx} className={`terminal-line ${lineType}`}>
                  <span className="text-dim" style={{ userSelect: "none", marginRight: 12 }}>
                    {idx + 1}
                  </span>
                  {line}
                </div>
              );
            })
          )}
        </div>
      </details>
    </div>
  );
};
