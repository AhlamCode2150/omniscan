"use client";
import { useState } from "react";
import { Search } from "lucide-react";
import { PageHead } from "@/components/PageHead";
import { JobList } from "@/components/JobList";
import { useJobs } from "@/components/Upload";

export default function HistoryPage() {
  const { jobs, refresh } = useJobs();
  const [q, setQ] = useState("");
  const [f, setF] = useState("all");
  const list = jobs.filter((j) => (f === "all" || j.status === f) && (!q || (j.filename + (j.summary?.preview || "")).toLowerCase().includes(q.toLowerCase())));
  return (
    <main className="mx-auto max-w-[1100px] px-5 pb-16 pt-8 lg:px-10">
      <PageHead n="03" kicker="History" title="Everything you've read." />
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <label className="relative"><Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-ink3" /><input className="field w-64 !pl-8" placeholder="Search names and text" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search history" /></label>
        <div className="seg">{["all", "done", "failed"].map((s) => <button key={s} aria-pressed={f === s} onClick={() => setF(s)}>{s}</button>)}</div>
        <span className="mono ml-auto text-ink3">{list.length} OF {jobs.length}</span>
      </div>
      <JobList jobs={list} onChange={refresh} />
    </main>
  );
}
