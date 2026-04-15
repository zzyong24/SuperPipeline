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
  listRuns: () => fetchApi<any[]>("/api/runs"),
  getRun: (runId: string) => fetchApi<any>(`/api/runs/${runId}`),
  listContents: (params?: { status?: string; run_id?: string }) => {
    const search = new URLSearchParams();
    if (params?.status) search.set("status", params.status);
    if (params?.run_id) search.set("run_id", params.run_id);
    const qs = search.toString();
    return fetchApi<any[]>(`/api/contents${qs ? `?${qs}` : ""}`);
  },
  getContent: (id: string) => fetchApi<any>(`/api/contents/${id}`),
  approveContent: (id: string, publishUrl?: string) =>
    fetchApi<any>(`/api/contents/${id}/approve`, {
      method: "POST",
      body: JSON.stringify({ publish_url: publishUrl || "" }),
    }),
};
