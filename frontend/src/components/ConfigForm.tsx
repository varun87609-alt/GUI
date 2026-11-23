import React, { useState } from "react";
import { Sliders, Play, ShieldAlert, Cpu } from "lucide-react";
import {
  WorkflowType,
  MeshJobCreateRequest,
  GeometryAnalysis,
} from "../types";

interface ConfigFormProps {
  analysis: GeometryAnalysis | null;
  onSubmit: (config: MeshJobCreateRequest) => void;
  isLoading: boolean;
}

export const ConfigForm: React.FC<ConfigFormProps> = ({ analysis, onSubmit, isLoading }) => {
  const [workflowType, setWorkflowType] = useState<WorkflowType>("external_flow");

  // Background Mesh Resolution
  const [cellsX, setCellsX] = useState<number>(15);
  const [cellsY, setCellsY] = useState<number>(15);
  const [cellsZ, setCellsZ] = useState<number>(15);

  // Domain Margins
  const [minXMargin, setMinXMargin] = useState<number>(1.5);
  const [maxXMargin, setMaxXMargin] = useState<number>(3.0);
  const [lateralMargin, setLateralMargin] = useState<number>(1.5);
  const [verticalMargin, setVerticalMargin] = useState<number>(1.5);

  // Surface Refinement
  const [minSurfaceLevel, setMinSurfaceLevel] = useState<number>(1);
  const [maxSurfaceLevel, setMaxSurfaceLevel] = useState<number>(2);

  // Feature Refinement
  const [featureRefinementEnabled, setFeatureRefinementEnabled] = useState<boolean>(true);
  const [includedAngle, setIncludedAngle] = useState<number>(150);
  const [featureLevel, setFeatureLevel] = useState<number>(2);

  // Boundary Layers
  const [layersEnabled, setLayersEnabled] = useState<boolean>(false);
  const [numLayers, setNumLayers] = useState<number>(2);
  const [expansionRatio, setExpansionRatio] = useState<number>(1.2);
  const [finalLayerThickness, setFinalLayerThickness] = useState<number>(0.3);

  // Quality & Limits
  const [timeoutSeconds, setTimeoutSeconds] = useState<number>(600);
  const [maxNonOrtho, setMaxNonOrtho] = useState<number>(65);

  const estimatedBaseCells = cellsX * cellsY * cellsZ;
  const isExceedingLimit = estimatedBaseCells > 3000000;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!analysis) return;

    const request: MeshJobCreateRequest = {
      upload_id: analysis.upload_id,
      workflow_type: workflowType,
      target_cells_x: cellsX,
      target_cells_y: cellsY,
      target_cells_z: cellsZ,
      domain_margin: {
        min_x_multiplier: minXMargin,
        max_x_multiplier: maxXMargin,
        min_y_multiplier: lateralMargin,
        max_y_multiplier: lateralMargin,
        min_z_multiplier: verticalMargin,
        max_z_multiplier: verticalMargin,
      },
      surface_refinement: {
        min_level: minSurfaceLevel,
        max_level: maxSurfaceLevel,
      },
      feature_refinement: {
        enabled: featureRefinementEnabled,
        included_angle: includedAngle,
        level: featureLevel,
      },
      boundary_layers: {
        enabled: layersEnabled,
        n_surface_layers: numLayers,
        expansion_ratio: expansionRatio,
        final_layer_thickness: finalLayerThickness,
        min_thickness: 0.05,
      },
      timeout_seconds: timeoutSeconds,
      max_non_ortho: maxNonOrtho,
    };

    onSubmit(request);
  };

  return (
    <div className="card">
      <div className="card-header">
        <h3 className="card-title">
          <Sliders size={20} className="text-cyan" />
          Mesh settings
        </h3>
        <div className="status-badge font-mono">
          <span>Base Cells:</span>
          <span className={isExceedingLimit ? "text-danger" : "text-cyan"}>
            {estimatedBaseCells.toLocaleString()}
          </span>
        </div>
      </div>

      <form onSubmit={handleSubmit} onInvalidCapture={(event) => {
        const details = (event.target as HTMLElement).closest("details");
        if (details) details.open = true;
      }}>
        {/* Workflow Selection */}
        <div className="form-group">
          <label className="form-label">
            <span>Workflow</span>
          </label>
          <select
            className="form-select"
            value={workflowType}
            onChange={(e) => setWorkflowType(e.target.value as WorkflowType)}
          >
            <option value="external_flow">External flow</option>
            <option value="generic_surface">Surface conforming</option>
            <option value="internal_flow">Internal flow</option>
          </select>
        </div>

        {/* Base Grid Resolution */}
        <div className="form-group">
          <label className="form-label">
            <span>Background grid</span>
          </label>
          <div className="form-row">
            <div>
              <span className="text-dim" style={{ fontSize: "0.75rem" }}>Cells X</span>
              <input
                type="number"
                min={4}
                max={150}
                className="form-input font-mono"
                value={cellsX}
                onChange={(e) => setCellsX(parseInt(e.target.value) || 10)}
              />
            </div>
            <div>
              <span className="text-dim" style={{ fontSize: "0.75rem" }}>Cells Y</span>
              <input
                type="number"
                min={4}
                max={150}
                className="form-input font-mono"
                value={cellsY}
                onChange={(e) => setCellsY(parseInt(e.target.value) || 10)}
              />
            </div>
            <div>
              <span className="text-dim" style={{ fontSize: "0.75rem" }}>Cells Z</span>
              <input
                type="number"
                min={4}
                max={150}
                className="form-input font-mono"
                value={cellsZ}
                onChange={(e) => setCellsZ(parseInt(e.target.value) || 10)}
              />
            </div>
          </div>
        </div>

        {/* Surface & Feature Refinement */}
        <div className="form-group">
          <label className="form-label">
            <span>Surface Refinement Levels</span>
          </label>
          <div className="form-row">
            <div>
              <span className="text-dim" style={{ fontSize: "0.75rem" }}>Min Level</span>
              <input
                type="number"
                min={0}
                max={5}
                className="form-input font-mono"
                value={minSurfaceLevel}
                onChange={(e) => setMinSurfaceLevel(parseInt(e.target.value) || 0)}
              />
            </div>
            <div>
              <span className="text-dim" style={{ fontSize: "0.75rem" }}>Max Level</span>
              <input
                type="number"
                min={minSurfaceLevel}
                max={6}
                className="form-input font-mono"
                value={maxSurfaceLevel}
                onChange={(e) => setMaxSurfaceLevel(parseInt(e.target.value) || minSurfaceLevel)}
              />
            </div>
          </div>
        </div>

        <details className="disclosure">
          <summary>Advanced settings</summary>
          {/* Domain Margins (if External Flow) */}
          {workflowType === "external_flow" && (
            <div className="form-group">
              <label className="form-label">
                <span>Domain Margins (Multipliers relative to Model Dims)</span>
              </label>
              <div className="form-row">
                <div>
                  <span className="text-dim" style={{ fontSize: "0.75rem" }}>Upstream (-X)</span>
                  <input
                    type="number"
                    step="0.5"
                    min={0.5}
                    max={10}
                    className="form-input font-mono"
                    value={minXMargin}
                    onChange={(e) => setMinXMargin(parseFloat(e.target.value) || 1)}
                  />
                </div>
                <div>
                  <span className="text-dim" style={{ fontSize: "0.75rem" }}>Wake (+X)</span>
                  <input
                    type="number"
                    step="0.5"
                    min={1.0}
                    max={15}
                    className="form-input font-mono"
                    value={maxXMargin}
                    onChange={(e) => setMaxXMargin(parseFloat(e.target.value) || 2)}
                  />
                </div>
                <div>
                  <span className="text-dim" style={{ fontSize: "0.75rem" }}>Lateral (Y)</span>
                  <input
                    type="number"
                    step="0.5"
                    min={0.5}
                    max={10}
                    className="form-input font-mono"
                    value={lateralMargin}
                    onChange={(e) => setLateralMargin(parseFloat(e.target.value) || 1)}
                  />
                </div>
                <div>
                  <span className="text-dim" style={{ fontSize: "0.75rem" }}>Vertical (Z)</span>
                  <input
                    type="number"
                    step="0.5"
                    min={0.5}
                    max={10}
                    className="form-input font-mono"
                    value={verticalMargin}
                    onChange={(e) => setVerticalMargin(parseFloat(e.target.value) || 1)}
                  />
                </div>
              </div>
            </div>
          )}

          {/* Feature Extraction */}
          <div className="form-group">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
              <span style={{ fontSize: "0.85rem", fontWeight: 500 }}>Feature Edge Extraction</span>
              <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: "0.8rem", cursor: "pointer" }}>
                <input
                  type="checkbox"
                  checked={featureRefinementEnabled}
                  onChange={(e) => setFeatureRefinementEnabled(e.target.checked)}
                />
                Enable
              </label>
            </div>
            {featureRefinementEnabled && (
              <div className="form-row">
                <div>
                  <span className="text-dim" style={{ fontSize: "0.75rem" }}>Included Angle (°)</span>
                  <input
                    type="number"
                    min={30}
                    max={179}
                    className="form-input font-mono"
                    value={includedAngle}
                    onChange={(e) => setIncludedAngle(parseFloat(e.target.value) || 150)}
                  />
                </div>
                <div>
                  <span className="text-dim" style={{ fontSize: "0.75rem" }}>Edge Refinement Level</span>
                  <input
                    type="number"
                    min={1}
                    max={5}
                    className="form-input font-mono"
                    value={featureLevel}
                    onChange={(e) => setFeatureLevel(parseInt(e.target.value) || 2)}
                  />
                </div>
              </div>
            )}
          </div>

          {/* Boundary Layers */}
          <div className="form-group">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
              <span style={{ fontSize: "0.85rem", fontWeight: 500 }}>Prism Boundary Layers</span>
              <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: "0.8rem", cursor: "pointer" }}>
                <input
                  type="checkbox"
                  checked={layersEnabled}
                  onChange={(e) => setLayersEnabled(e.target.checked)}
                />
                Enable
              </label>
            </div>
            {layersEnabled && (
              <div className="form-row">
                <div>
                  <span className="text-dim" style={{ fontSize: "0.75rem" }}>Number of Layers</span>
                  <input
                    type="number"
                    min={1}
                    max={6}
                    className="form-input font-mono"
                    value={numLayers}
                    onChange={(e) => setNumLayers(parseInt(e.target.value) || 2)}
                  />
                </div>
                <div>
                  <span className="text-dim" style={{ fontSize: "0.75rem" }}>Expansion Ratio</span>
                  <input
                    type="number"
                    step="0.05"
                    min={1.05}
                    max={2.0}
                    className="form-input font-mono"
                    value={expansionRatio}
                    onChange={(e) => setExpansionRatio(parseFloat(e.target.value) || 1.2)}
                  />
                </div>
                <div>
                  <span className="text-dim" style={{ fontSize: "0.75rem" }}>Final Thickness</span>
                  <input
                    type="number"
                    step="0.05"
                    min={0.1}
                    max={0.8}
                    className="form-input font-mono"
                    value={finalLayerThickness}
                    onChange={(e) => setFinalLayerThickness(parseFloat(e.target.value) || 0.3)}
                  />
                </div>
              </div>
            )}
          </div>

          {/* Job Execution Limits */}
          <div className="form-group">
            <label className="form-label">
              <span>Execution Controls</span>
            </label>
            <div className="form-row">
              <div>
                <span className="text-dim" style={{ fontSize: "0.75rem" }}>Timeout (seconds)</span>
                <select
                  className="form-select font-mono"
                  value={timeoutSeconds}
                  onChange={(e) => setTimeoutSeconds(parseInt(e.target.value))}
                >
                  <option value={180}>3 minutes (Fast)</option>
                  <option value={600}>10 minutes (Standard)</option>
                  <option value={1200}>20 minutes (Detailed)</option>
                </select>
              </div>
              <div>
                <span className="text-dim" style={{ fontSize: "0.75rem" }}>Max Non-Ortho (°)</span>
                <input
                  type="number"
                  min={45}
                  max={85}
                  className="form-input font-mono"
                  value={maxNonOrtho}
                  onChange={(e) => setMaxNonOrtho(parseFloat(e.target.value) || 65)}
                />
              </div>
            </div>
          </div>

        </details>

        {isExceedingLimit && (
          <div className="alert alert-danger">
            <ShieldAlert size={18} />
            <div>
              Estimated cell count ({estimatedBaseCells.toLocaleString()}) exceeds safety limit of 3,000,000.
              Please reduce grid resolution before submitting.
            </div>
          </div>
        )}

        <button
          type="submit"
          className="btn btn-primary"
          style={{ width: "100%", marginTop: 8 }}
          disabled={!analysis || isLoading || isExceedingLimit}
        >
          <Play size={16} />
          {isLoading ? "Starting…" : "Generate mesh"}
        </button>
      </form>
    </div>
  );
};
