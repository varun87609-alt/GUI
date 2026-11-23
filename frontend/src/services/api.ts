import {
  HealthResponse,
  CapabilitiesResponse,
  GeometryAnalysis,
  MeshJobCreateRequest,
  JobStatusResponse,
  JobLogsResponse,
  MeshStatsResponse,
} from "../types";

const API_BASE = import.meta.env.VITE_API_BASE || "/api/v1";

class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  const response = await fetch(url, {
    ...options,
    headers: {
      ...(options.headers || {}),
    },
  });

  if (!response.ok) {
    let errorMessage = `HTTP ${response.status} ${response.statusText}`;
    try {
      const errorJson = await response.json();
      if (errorJson.detail) {
        if (typeof errorJson.detail === "string") {
          errorMessage = errorJson.detail;
        } else if (Array.isArray(errorJson.detail)) {
          errorMessage = errorJson.detail.map((d: any) => d.msg || JSON.stringify(d)).join(", ");
        }
      }
    } catch {
      // Non-JSON error body
    }
    throw new ApiError(errorMessage, response.status);
  }

  return response.status === 204 ? (undefined as T) : response.json();
}

export const api = {
  getHealth: (): Promise<HealthResponse> => {
    return request<HealthResponse>("/health");
  },

  getCapabilities: (): Promise<CapabilitiesResponse> => {
    return request<CapabilitiesResponse>("/capabilities");
  },

  uploadSTL: async (
    file: File,
    onProgress?: (percent: number) => void
  ): Promise<GeometryAnalysis> => {
    const formData = new FormData();
    formData.append("file", file, file.name);

    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open("POST", `${API_BASE}/uploads`);

      if (onProgress && xhr.upload) {
        xhr.upload.onprogress = (e) => {
          if (e.lengthComputable) {
            const percent = Math.round((e.loaded / e.total) * 100);
            onProgress(percent);
          }
        };
      }

      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            const data = JSON.parse(xhr.responseText);
            resolve(data);
          } catch {
            reject(new ApiError("Invalid JSON in upload response", xhr.status));
          }
        } else {
          let msg = `Upload failed with status ${xhr.status}`;
          try {
            const err = JSON.parse(xhr.responseText);
            if (err.detail) msg = typeof err.detail === "string" ? err.detail : JSON.stringify(err.detail);
          } catch {
            // ignore
          }
          reject(new ApiError(msg, xhr.status));
        }
      };

      xhr.onerror = () => {
        reject(new ApiError("Network error during file upload", 0));
      };

      xhr.send(formData);
    });
  },

  getUploadAnalysis: (uploadId: string): Promise<GeometryAnalysis> => {
    return request<GeometryAnalysis>(`/uploads/${uploadId}`);
  },

  createJob: (req: MeshJobCreateRequest): Promise<JobStatusResponse> => {
    return request<JobStatusResponse>("/jobs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req),
    });
  },

  getJobs: (limit = 50, offset = 0): Promise<JobStatusResponse[]> => {
    return request<JobStatusResponse[]>(`/jobs?limit=${limit}&offset=${offset}`);
  },

  clearJobHistory: (jobId?: string): Promise<{ cleared: number }> => {
    const endpoint = jobId ? `/jobs/${jobId}/history` : "/jobs/history";
    return request<{ cleared: number }>(endpoint, { method: "DELETE" });
  },

  getJob: (jobId: string): Promise<JobStatusResponse> => {
    return request<JobStatusResponse>(`/jobs/${jobId}`);
  },

  remeshJob: (jobId: string): Promise<JobStatusResponse> => {
    return request<JobStatusResponse>(`/jobs/${jobId}/remesh`, { method: "POST" });
  },

  openCaseFolder: (jobId: string): Promise<void> => {
    return request<void>(`/jobs/${jobId}/open-folder`, {
      method: "POST",
      headers: { "X-Open-Case-Folder": "1" },
    });
  },

  getJobLogs: (jobId: string, offset = 0): Promise<JobLogsResponse> => {
    return request<JobLogsResponse>(`/jobs/${jobId}/logs?offset=${offset}`);
  },

  cancelJob: (jobId: string): Promise<{ message: string }> => {
    return request<{ message: string }>(`/jobs/${jobId}/cancel`, {
      method: "POST",
    });
  },

  getMeshResults: (jobId: string): Promise<MeshStatsResponse> => {
    return request<MeshStatsResponse>(`/jobs/${jobId}/results`);
  },

  getDownloadUrl: (jobId: string): string => {
    return `${API_BASE}/jobs/${jobId}/download`;
  },
};
