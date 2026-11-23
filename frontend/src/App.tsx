import React, { useCallback, useState } from "react";
import { Navbar } from "./components/Navbar";
import { UploadZone } from "./components/UploadZone";
import { STLViewer } from "./components/STLViewer";
import { ConfigForm } from "./components/ConfigForm";
import { JobProgress } from "./components/JobProgress";
import { ResultsView } from "./components/ResultsView";
import { Dashboard } from "./components/Dashboard";
import { DocumentationView } from "./components/DocumentationView";
import { api } from "./services/api";
import { GeometryAnalysis, MeshJobCreateRequest } from "./types";

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<"studio" | "jobs" | "docs">("studio");

  // Studio Workflow State
  const [analysis, setAnalysis] = useState<GeometryAnalysis | null>(null);
  const [stlFile, setStlFile] = useState<File | null>(null);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [viewingResults, setViewingResults] = useState<boolean>(false);
  const [runVersion, setRunVersion] = useState(0);
  const [isSubmittingJob, setIsSubmittingJob] = useState<boolean>(false);
  const [appError, setAppError] = useState<string | null>(null);

  const handleUploadSuccess = (newAnalysis: GeometryAnalysis, file: File) => {
    setAnalysis(newAnalysis);
    setStlFile(file);
    setActiveJobId(null);
    setViewingResults(false);
    setAppError(null);
  };

  const handleCreateJob = async (config: MeshJobCreateRequest) => {
    try {
      setIsSubmittingJob(true);
      setAppError(null);
      const res = await api.createJob(config);
      setActiveJobId(res.job_id);
      setViewingResults(false);
    } catch (err: any) {
      setAppError(err.message || "Failed to submit meshing job.");
    } finally {
      setIsSubmittingJob(false);
    }
  };

  const handleJobCompleted = useCallback(() => {
    setViewingResults(true);
  }, []);

  const handleRemesh = () => {
    setViewingResults(false);
    setRunVersion((version) => version + 1);
  };

  const handleSelectJobFromDashboard = async (jobId: string) => {
    try {
      const job = await api.getJob(jobId);
      setActiveJobId(jobId);
      setActiveTab("studio");
      if (job.status === "completed") {
        setViewingResults(true);
      } else {
        setViewingResults(false);
      }
    } catch (err: any) {
      setAppError(err.message || "Failed to load job details.");
    }
  };

  const handleResetNewJob = () => {
    setActiveJobId(null);
    setViewingResults(false);
  };

  return (
    <div className="app-container">
      <Navbar activeTab={activeTab} setActiveTab={setActiveTab} />

      <main className="main-content">
        {appError && (
          <div className="alert alert-danger" style={{ marginBottom: 20 }}>
            <div style={{ flex: 1 }}>{appError}</div>
            <button
              className="btn btn-secondary"
              style={{ padding: "4px 8px", fontSize: "0.75rem" }}
              onClick={() => setAppError(null)}
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Studio Tab */}
        {activeTab === "studio" && (
          <>
            {viewingResults && activeJobId ? (
              <ResultsView key={activeJobId} jobId={activeJobId} onNewJob={handleResetNewJob} onRemesh={handleRemesh} />
            ) : activeJobId ? (
              <JobProgress key={`${activeJobId}:${runVersion}`} jobId={activeJobId} onJobComplete={handleJobCompleted} onRemesh={handleRemesh} />
            ) : (
              <div className={stlFile ? "studio-grid" : "studio-empty"}>
                <div className="studio-controls">
                  <UploadZone onUploadSuccess={handleUploadSuccess} isLoading={isSubmittingJob} />

                  {analysis && (
                    <ConfigForm
                      analysis={analysis}
                      onSubmit={handleCreateJob}
                      isLoading={isSubmittingJob}
                    />
                  )}
                </div>
                {stlFile && <STLViewer stlFile={stlFile} analysis={analysis} />}
              </div>
            )}
          </>
        )}

        {/* Job Monitor / Dashboard Tab */}
        {activeTab === "jobs" && (
          <Dashboard
            onSelectJob={handleSelectJobFromDashboard}
            onNewJob={() => {
              setActiveJobId(null);
              setViewingResults(false);
              setActiveTab("studio");
            }}
          />
        )}

        {/* Documentation Tab */}
        {activeTab === "docs" && <DocumentationView />}
      </main>
    </div>
  );
};

export default App;
