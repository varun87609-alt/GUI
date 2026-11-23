import { useState } from "react";
import { Copy, FolderOpen, RotateCcw } from "lucide-react";
import { api } from "../services/api";
import { JobStatusResponse } from "../types";

export function CaseControls({ job, onRemesh }: {
  job: JobStatusResponse;
  onRemesh: () => void;
}) {
  const [copyStatus, setCopyStatus] = useState("");
  const [remeshing, setRemeshing] = useState(false);
  const [opening, setOpening] = useState(false);
  const [error, setError] = useState("");
  const path = job.case_path;
  if (!path) return null;

  async function copyPath(casePath: string) {
    try {
      await navigator.clipboard.writeText(casePath);
      setCopyStatus("Copied");
    } catch {
      setCopyStatus("Select the path and copy it manually.");
    }
  }

  async function openFolder() {
    setOpening(true);
    setError("");
    try {
      await api.openCaseFolder(job.job_id);
    } catch (error) {
      setError(error instanceof Error ? error.message : "Could not open the saved folder.");
    } finally {
      setOpening(false);
    }
  }

  async function remesh() {
    setRemeshing(true);
    setError("");
    try {
      await api.remeshJob(job.job_id);
      onRemesh();
    } catch (error) {
      setError(error instanceof Error ? error.message : "Could not remesh this case.");
      setRemeshing(false);
    }
  }

  return (
    <section className="case-folder">
      <div className="text-muted">Case folder</div>
      <div className="font-mono" style={{ overflowWrap: "anywhere", userSelect: "text", margin: "4px 0 10px" }}>
        {path}
      </div>
      <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 8 }}>
        <button className="btn btn-secondary" onClick={openFolder} disabled={opening}>
          <FolderOpen size={16} /> Open folder
        </button>
        <button className="btn btn-secondary" onClick={() => copyPath(path)}>
          <Copy size={16} /> Copy path
        </button>
        <span role="status">{copyStatus}</span>
        {job.can_remesh && (
          <button className="btn btn-primary" onClick={remesh} disabled={remeshing}>
            <RotateCcw size={16} /> {remeshing ? "Queuing…" : "Remesh this case"}
          </button>
        )}
      </div>
      {job.can_remesh && (
        <p className="text-muted" style={{ marginTop: 8 }}>
          Save dictionary edits before remeshing.
        </p>
      )}
      {error && <p role="alert" className="alert alert-danger">{error}</p>}
    </section>
  );
}
