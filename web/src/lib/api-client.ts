import type { Run, Content, Pipeline, PipelineDetail, StageSnapshot } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...options?.headers },
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export const api = {
  listRuns: () => fetchApi<Run[]>("/api/runs"),
  getRun: (runId: string) => fetchApi<Run>(`/api/runs/${runId}`),
  listContents: (params?: { status?: string; run_id?: string }) => {
    const search = new URLSearchParams();
    if (params?.status) search.set("status", params.status);
    if (params?.run_id) search.set("run_id", params.run_id);
    const qs = search.toString();
    return fetchApi<Content[]>(`/api/contents${qs ? `?${qs}` : ""}`);
  },
  getContent: (id: string) => fetchApi<Content>(`/api/contents/${id}`),
  approveContent: (id: string, publishUrl?: string) =>
    fetchApi<Content>(`/api/contents/${id}/approve`, {
      method: "POST",
      body: JSON.stringify({ publish_url: publishUrl || "" }),
    }),
  createRun: (data: { pipeline: string; brief: string; keywords?: string[]; stage_overrides?: Record<string, Record<string, any>> }) =>
    fetchApi<{ run_id: string; status: string }>("/api/runs", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  listPipelines: () => fetchApi<Pipeline[]>("/api/pipelines"),
  getPipeline: (name: string) => fetchApi<PipelineDetail>(`/api/pipelines/${name}`),
  listStages: (runId: string) => fetchApi<StageSnapshot[]>(`/api/runs/${runId}/stages`),
  getStage: (runId: string, agent: string, version?: number) => {
    const params = version ? `?version=${version}` : "";
    return fetchApi<StageSnapshot>(`/api/runs/${runId}/stages/${agent}${params}`);
  },
  editStageOutputs: (runId: string, agent: string, outputs: Record<string, any>) =>
    fetchApi<StageSnapshot>(`/api/runs/${runId}/stages/${agent}`, {
      method: "PUT",
      body: JSON.stringify({ outputs }),
    }),
  rerunStage: (
    runId: string,
    agent: string,
    data: { config?: Record<string, any>; model?: string; prompt?: string; only?: boolean }
  ) =>
    fetchApi<{ status: string; run_id: string }>(`/api/runs/${runId}/stages/${agent}/rerun`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  getStageHistory: (runId: string, agent: string) =>
    fetchApi<StageSnapshot[]>(`/api/runs/${runId}/stages/${agent}/history`),
};
