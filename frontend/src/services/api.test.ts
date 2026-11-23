import { describe, it, expect, vi, afterEach } from "vitest";
import { api } from "./api";

describe("API Client", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("fetches health status successfully", async () => {
    const mockHealth = {
      status: "healthy",
      docker_ready: true,
      openfoam_image_ready: true,
      openfoam_version: "v2506",
      workspace_disk_free_gb: 120.5,
      active_jobs: 0,
      max_concurrent_jobs: 2,
    };

    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockHealth,
    } as Response));

    const result = await api.getHealth();
    expect(result.status).toBe("healthy");
    expect(result.docker_ready).toBe(true);
    expect(result.openfoam_version).toBe("v2506");
  });

  it("fetches capabilities successfully", async () => {
    const mockCap = {
      supported_workflows: ["external_flow", "generic_surface", "internal_flow"],
      supported_formats: ["stl_ascii", "stl_binary"],
      max_upload_size_bytes: 104857600,
      max_triangle_count: 1000000,
      max_estimated_cells: 3000000,
      default_timeout_seconds: 600,
      openfoam_image: "openeuler/openfoam:2506-oe2403sp4",
    };

    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockCap,
    } as Response));

    const result = await api.getCapabilities();
    expect(result.supported_workflows).toContain("external_flow");
    expect(result.max_triangle_count).toBe(1000000);
  });

  it("constructs correct download url", () => {
    const url = api.getDownloadUrl("job-12345");
    expect(url).toContain("/jobs/job-12345/download");
  });
});
