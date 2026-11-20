"use client";
import Link from "next/link";
import { Trash2, FileText } from "lucide-react";
import { api, fmtAgo, fmtBytes } from "@/lib/api";
import type { Job } from "@/lib/types";
import { useToast } from "./toast";

export function JobList({ jobs, onChange }: { jobs: Job[]; onChange: () => void }) {
  const toast = useToast();
  if (!jobs.length) return <div className="border border-ink bg-surface px-6 py-14 text-center text-ink2">Nothing here yet. Extractions are stored only on this machine.</div>;
  return (
    <ul className="divide-y divide-ink border border-ink bg-surface">
      {jobs.map((j) => (
        <li key={j.id} className="group flex items-center gap-4 px-4 py-3 transition-colors hover:bg-lime/40">
          <Link href={`/scan/${j.id}`} className="flex min-w-0 flex-1 items-center gap-4">
            {j.kind !== "pdf" ? /* eslint-disable-next-line @next/next/no-img-element */ <img src={api.image(j.id, 1)} alt="" loading="lazy" className="h-12 w-12 shrink-0 border border-ink object-cover" /> :
              <div className="grid h-12 w-12 shrink-0 place-items-center border border-ink"><FileText size={18} /></div>}
            <div className="min-w-0 flex-1">
              <p className="truncate font-medium">{j.filename}</p>
              <p className="truncate text-[12px] text-ink3">{j.status === "done" ? (j.summary?.empty ? "No text recognised" : j.summary?.preview?.replace(/\s+/g, " ")) : j.error}</p>
            </div>
          </Link>
          <div className="hidden shrink-0 items-center gap-2 sm:flex">
            {j.status === "failed" && <span className="chip border-bad text-bad">Failed</span>}
            {j.status === "done" && j.summary && (<>
              <span className="chip">{j.summary.language_name || "—"}</span><span className="chip">{j.summary.words} words</span>
              {j.summary.uncertain > 0 && <span className="chip border-warn text-warn">{j.summary.uncertain} uncertain</span>}</>)}
            <span className="mono w-28 text-right text-[10px] text-ink3">{fmtAgo(j.created)} · {fmtBytes(j.size)}</span>
          </div>
          <button className="btn btn-ghost btn-icon opacity-0 transition group-hover:opacity-100 focus-visible:opacity-100" aria-label={`Delete ${j.filename}`}
            onClick={async () => { await api.del(j.id); toast("Deleted"); onChange(); }}><Trash2 size={15} /></button>
        </li>))}
    </ul>
  );
}
