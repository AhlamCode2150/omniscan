import type { Job } from "@/lib/types";

export function ProcessingCard({ j, stages }: { j: Job; stages: string[] }) {
  const p = j.progress;
  return (
    <div className="border border-ink bg-surface p-4">
      <div className="flex items-center justify-between gap-3"><p className="truncate font-medium">{j.filename}</p><span className="mono tabular-nums">{String(Math.round(p.pct)).padStart(3, "0")}%</span></div>
      <div className="relative mt-3 h-2 overflow-hidden border border-ink bg-sunken" role="progressbar" aria-valuenow={Math.round(p.pct)} aria-valuemin={0} aria-valuemax={100}>
        <div className="sweep absolute inset-y-0 left-0 overflow-hidden bg-ink transition-all duration-500" style={{ width: `${Math.max(3, p.pct)}%` }} /></div>
      <ol className="mono mt-3 grid grid-cols-2 gap-x-3 gap-y-1 text-[10px] sm:grid-cols-3">
        {stages.map((s, i) => <li key={s} className={i < p.stage ? "text-ink2" : i === p.stage && j.status === "running" ? "bg-lime font-bold text-ink" : "text-ink3"}>{i < p.stage ? "■ " : i === p.stage && j.status === "running" ? "▶ " : "□ "}{s}</li>)}
      </ol>
      <p className="mono mt-2 min-h-4 truncate text-[10px] normal-case text-ink3">{j.status === "queued" ? "Waiting for a worker…" : p.message}{p.pages > 1 ? ` · page ${p.page}/${p.pages}` : ""}</p>
    </div>
  );
}
