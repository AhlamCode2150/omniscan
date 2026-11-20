"use client";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { PageHead } from "@/components/PageHead";
import { JobList } from "@/components/JobList";
import { useJobs } from "@/components/Upload";
import { useEngineStatus } from "@/components/ui";

export default function Overview() {
  const { jobs, refresh } = useJobs();
  const { cfg } = useEngineStatus();
  const done = jobs.filter((j) => j.status === "done");
  const words = done.reduce((a, j) => a + (j.summary?.words || 0), 0);
  const unc = done.reduce((a, j) => a + (j.summary?.uncertain || 0), 0);
  const confs = done.map((j) => j.summary?.mean_conf).filter((x): x is number => typeof x === "number");
  const stats = [["Documents", String(done.length)], ["Words read", words.toLocaleString()], ["Flagged uncertain", String(unc)], ["Mean engine score", confs.length ? `${Math.round((confs.reduce((a, b) => a + b, 0) / confs.length) * 100)}%` : "—"]];
  return (
    <main className="mx-auto max-w-[1100px] px-5 pb-16 pt-8 lg:px-10">
      <PageHead n="01" kicker="Overview" title="Good to see you." />
      <dl className="grid grid-cols-2 border border-ink bg-surface md:grid-cols-4">
        {stats.map(([k, v], i) => <div key={k} className={`p-5 ${i ? "md:border-l md:border-ink" : ""} ${i % 2 ? "border-l border-ink md:border-l" : ""} ${i > 1 ? "border-t border-ink md:border-t-0" : ""}`}><dd className="display text-[56px]">{v}</dd><dt className="mono mt-1 text-ink3">{k}</dt></div>)}
      </dl>
      <div className="mt-6 grid gap-6 md:grid-cols-[1.4fr_1fr]">
        <Link href="/app/new" className="reg group relative flex min-h-[200px] flex-col justify-between border border-ink bg-lime p-6 transition-shadow hover:shadow-[6px_6px_0_var(--ink)]">
          <span className="mono">NEW EXTRACTION</span>
          <span className="display text-[clamp(36px,4.4vw,64px)] uppercase">Scan a page <ArrowRight className="inline transition-transform group-hover:translate-x-2" size={34} /></span>
        </Link>
        <div className="border border-ink bg-surface p-5"><p className="eyebrow mb-3">Engines on this machine</p>
          <ul className="space-y-2">{cfg?.engines.map((e) => <li key={e.name} className="flex items-center gap-2 text-[13px]"><span className={`h-2 w-2 ${e.available ? "bg-good" : "bg-ink3"}`} />{e.label}</li>) ?? <li className="text-ink3">Connecting…</li>}</ul>
          <Link href="/app/settings" className="mono mt-4 inline-block underline underline-offset-4">Manage →</Link></div>
      </div>
      <div className="mb-3 mt-10 flex items-end justify-between"><h2 className="display text-[34px] uppercase">Recent</h2><Link href="/app/history" className="mono underline underline-offset-4">All history →</Link></div>
      <JobList jobs={jobs.filter((j) => j.status !== "queued" && j.status !== "running").slice(0, 5)} onChange={refresh} />
    </main>
  );
}
