import React, { useState, useRef } from "react";
import { Upload, FileBox, AlertCircle, RefreshCw } from "lucide-react";
import { api } from "../services/api";
import { GeometryAnalysis } from "../types";

interface UploadZoneProps {
  onUploadSuccess: (analysis: GeometryAnalysis, file: File) => void;
  isLoading: boolean;
}

export const UploadZone: React.FC<UploadZoneProps> = ({ onUploadSuccess, isLoading }) => {
  const [isDragOver, setIsDragOver] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFile = async (file: File) => {
    setError(null);
    if (!file.name.toLowerCase().endsWith(".stl")) {
      setError("Only .stl geometry files are accepted.");
      return;
    }

    if (file.size > 100 * 1024 * 1024) {
      setError("File exceeds 100 MB limit.");
      return;
    }

    setUploadProgress(0);
    try {
      const analysis = await api.uploadSTL(file, (percent) => {
        setUploadProgress(percent);
      });
      setUploadProgress(null);
      onUploadSuccess(analysis, file);
    } catch (err: any) {
      setUploadProgress(null);
      setError(err.message || "Failed to upload and validate STL.");
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  const handleLoadSampleCube = async () => {
    setError(null);
    setUploadProgress(10);
    const sampleCubeSTL = `solid cube
  facet normal 0 0 1
    outer loop
      vertex -0.2 -0.2 0.2
      vertex  0.2 -0.2 0.2
      vertex  0.2  0.2 0.2
    endloop
  endfacet
  facet normal 0 0 1
    outer loop
      vertex -0.2 -0.2 0.2
      vertex  0.2  0.2 0.2
      vertex -0.2  0.2 0.2
    endloop
  endfacet
  facet normal 0 0 -1
    outer loop
      vertex -0.2 -0.2 -0.2
      vertex  0.2  0.2 -0.2
      vertex  0.2 -0.2 -0.2
    endloop
  endfacet
  facet normal 0 0 -1
    outer loop
      vertex -0.2 -0.2 -0.2
      vertex -0.2  0.2 -0.2
      vertex  0.2  0.2 -0.2
    endloop
  endfacet
  facet normal 0 1 0
    outer loop
      vertex -0.2 0.2 -0.2
      vertex -0.2 0.2  0.2
      vertex  0.2 0.2  0.2
    endloop
  endfacet
  facet normal 0 1 0
    outer loop
      vertex -0.2 0.2 -0.2
      vertex  0.2 0.2  0.2
      vertex  0.2 0.2 -0.2
    endloop
  endfacet
  facet normal 0 -1 0
    outer loop
      vertex -0.2 -0.2 -0.2
      vertex  0.2 -0.2  0.2
      vertex -0.2 -0.2  0.2
    endloop
  endfacet
  facet normal 0 -1 0
    outer loop
      vertex -0.2 -0.2 -0.2
      vertex  0.2 -0.2 -0.2
      vertex  0.2 -0.2  0.2
    endloop
  endfacet
  facet normal 1 0 0
    outer loop
      vertex 0.2 -0.2 -0.2
      vertex 0.2  0.2 -0.2
      vertex 0.2  0.2  0.2
    endloop
  endfacet
  facet normal 1 0 0
    outer loop
      vertex 0.2 -0.2 -0.2
      vertex 0.2  0.2  0.2
      vertex 0.2 -0.2  0.2
    endloop
  endfacet
  facet normal -1 0 0
    outer loop
      vertex -0.2 -0.2 -0.2
      vertex -0.2 -0.2  0.2
      vertex -0.2  0.2  0.2
    endloop
  endfacet
  facet normal -1 0 0
    outer loop
      vertex -0.2 -0.2 -0.2
      vertex -0.2  0.2  0.2
      vertex -0.2  0.2 -0.2
    endloop
  endfacet
endsolid cube
`;
    const blob = new Blob([sampleCubeSTL], { type: "application/sla" });
    const file = new File([blob], "cube.stl", { type: "application/sla" });
    await handleFile(file);
  };

  return (
    <div className="card">
      <div className="card-header">
        <h3 className="card-title">
          <Upload size={20} className="text-cyan" />
          Upload STL
        </h3>
        <button
          className="btn btn-secondary"
          onClick={handleLoadSampleCube}
          disabled={isLoading || uploadProgress !== null}
          style={{ padding: "6px 12px", fontSize: "0.8rem" }}
        >
          <FileBox size={14} />
          Use sample cube
        </button>
      </div>

      <div
        className={`upload-dropzone ${isDragOver ? "dragover" : ""}`}
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragOver(true);
        }}
        onDragLeave={() => setIsDragOver(false)}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <input
          type="file"
          ref={fileInputRef}
          style={{ display: "none" }}
          accept=".stl"
          onChange={(e) => {
            if (e.target.files && e.target.files[0]) {
              handleFile(e.target.files[0]);
            }
          }}
        />

        <div className="dropzone-icon">
          <Upload size={28} />
        </div>

        <h4 style={{ marginBottom: 6 }}>Drag and drop your STL here</h4>
        <p className="text-muted" style={{ fontSize: "0.85rem", marginBottom: 16 }}>
          Supports binary & ASCII STL formats up to 100 MB
        </p>

        <button
          type="button"
          className="btn btn-primary"
          disabled={isLoading || uploadProgress !== null}
          onClick={(e) => {
            e.stopPropagation();
            fileInputRef.current?.click();
          }}
        >
          Choose STL
        </button>

        {uploadProgress !== null && (
          <div style={{ marginTop: 20 }}>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                fontSize: "0.8rem",
                marginBottom: 6,
              }}
            >
              <span>Uploading & Validating...</span>
              <span className="font-mono">{uploadProgress}%</span>
            </div>
            <div
              style={{
                width: "100%",
                height: 6,
                background: "var(--bg-input)",
                borderRadius: 4,
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  width: `${uploadProgress}%`,
                  height: "100%",
                  background: "var(--accent-cyan)",
                  transition: "width 0.2s ease",
                }}
              />
            </div>
          </div>
        )}
      </div>

      {error && (
        <div className="alert alert-danger" style={{ marginTop: 16 }}>
          <AlertCircle size={18} />
          <div style={{ flex: 1 }}>
            <div style={{ fontWeight: 600 }}>Upload Error</div>
            <div>{error}</div>
          </div>
          <button
            className="btn btn-secondary"
            onClick={() => setError(null)}
            style={{ padding: "4px 8px", fontSize: "0.75rem" }}
          >
            Dismiss
          </button>
        </div>
      )}
    </div>
  );
};
