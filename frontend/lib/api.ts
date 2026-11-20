import type { Config, Job, Page } from "./types";

async function j<T>(r: Response): Promise<T> {
  if (!r.ok) {
    let msg = `Request failed (${r.status})`;
    try { const b = await r.json(); msg = b.detail || b.jobs?.map((x: any) => x.error).filter(Boolean).join("; ") || msg; } catch {}
    throw new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
  }
  return r.json();
}

export const api = {
  config: () => fetch("/api/config").then(j<Config>),
  jobs: () => fetch("/api/jobs").then(j<{ jobs: Job[] }>),
  job: (id: string) => fetch(`/api/jobs/${id}`).then(j<{ job: Job; result: { pages: Page[] } | null }>),
  status: (id: string) => fetch(`/api/jobs/${id}/status`).then(j<Job>),
  upload: async (files: File[], opts: Record<string, string | boolean>) => {
    const fd = new FormData();
    files.forEach((f) => fd.append("files", f));
    Object.entries(opts).forEach(([k, v]) => fd.append(k, String(v)));
    const r = await fetch("/api/jobs", { method: "POST", body: fd });
    return j<{ jobs: ({ ok: true; job: Job } | { ok: false; filename: string; error: string })[] }>(r);
  },
  retry: (id: string, body: Record<string, unknown>) =>
    fetch(`/api/jobs/${id}/retry`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }).then(j<Job>),
  cancel: (id: string) => fetch(`/api/jobs/${id}/cancel`, { method: "POST" }),
  del: (id: string) => fetch(`/api/jobs/${id}`, { method: "DELETE" }),
  saveText: (id: string, page: number, text: string | null) =>
    fetch(`/api/jobs/${id}/pages/${page}/text`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text }) }),
  image: (id: string, page: number, variant: "original" | "enhanced" = "original") => `/api/jobs/${id}/image/${page}?variant=${variant}`,
  exportUrl: (id: string, format: string, variant = "cleaned") => `/api/jobs/${id}/export?format=${format}&variant=${variant}`,
};

export const fmtBytes = (n: number) => (n > 1e6 ? `${(n / 1e6).toFixed(1)} MB` : `${Math.max(1, Math.round(n / 1e3))} KB`);
export const fmtAgo = (t: number) => {
  const s = Math.max(0, Date.now() / 1000 - t);
  if (s < 60) return "just now";
  if (s < 3600) return `${Math.floor(s / 60)} min ago`;
  if (s < 86400) return `${Math.floor(s / 3600)} h ago`;
  return `${Math.floor(s / 86400)} d ago`;
};
