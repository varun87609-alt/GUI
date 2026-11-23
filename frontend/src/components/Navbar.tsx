import React, { useEffect, useState } from "react";
import { api } from "../services/api";
import { HealthResponse } from "../types";

interface NavbarProps {
  activeTab: "studio" | "jobs" | "docs";
  setActiveTab: (tab: "studio" | "jobs" | "docs") => void;
}

export const Navbar: React.FC<NavbarProps> = ({ activeTab, setActiveTab }) => {
  const [health, setHealth] = useState<HealthResponse | null>(null);

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const data = await api.getHealth();
        setHealth(data);
      } catch {
        setHealth(null);
      }
    };
    fetchHealth();
    const interval = setInterval(fetchHealth, 15000);
    return () => clearInterval(interval);
  }, []);

  const isHealthy = health?.status === "healthy" && health?.docker_ready && health?.openfoam_image_ready;

  return (
    <header className="navbar">
      <div className="nav-brand">
        OpenFOAM AutoMesh
      </div>

      <nav className="nav-tabs" aria-label="Main navigation">
        <button
          className={`nav-tab-btn ${activeTab === "studio" ? "active" : ""}`}
          onClick={() => setActiveTab("studio")}
        >
          Mesh
        </button>
        <button
          className={`nav-tab-btn ${activeTab === "jobs" ? "active" : ""}`}
          onClick={() => setActiveTab("jobs")}
        >
          Jobs
        </button>
        <button
          className={`nav-tab-btn ${activeTab === "docs" ? "active" : ""}`}
          onClick={() => setActiveTab("docs")}
        >
          Help
        </button>
      </nav>

      <div className="nav-status">
        <div className="nav-readiness" role="status">
          <span className={`status-dot ${isHealthy ? "online" : "offline"}`} />
          <span>
            {isHealthy
              ? "Ready"
              : health?.docker_ready
              ? "Image Missing"
              : health ? "Docker offline" : "Backend unavailable"}
          </span>
        </div>
      </div>
    </header>
  );
};
