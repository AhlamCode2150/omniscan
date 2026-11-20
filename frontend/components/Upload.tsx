"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { UploadCloud, ClipboardPaste } from "lucide-react";
import { api } from "@/lib/api";
import type { Config, Job } from "@/lib/types";
import { ProcessingCard } from "./ProcessingCard";
import { JobList } from "./JobList";
import { useToast } from "./toast";

const MODES: [string, string][] = [["auto", "Auto"], ["printed", "Printed"], ["handwriting", "Handwriting"], ["academic", "Math"]];

export function useJobs() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const refresh = useCallback(() => api.jobs().then((r) => setJobs(r.jobs)).catch(() => {}), []);
  useEffect(() => { refresh(); }, [refresh]);
  useEffect(() => {
    const active = jobs.some((j) => j.status === "queued" || j.status === "running");
    const t = setInterval(refresh, active ? 900 : 6000);
    return () => clearInterval(t);
  }, [jobs, refresh]);
  return { jobs, refresh };
}

export default function Upload({ batch = false }: { batch?: boolean }) {
  const router = useRouter();
  const toast = useToast();
  const [cfg, setCfg] = useState<Config | null>(null);
  const { jobs, refresh } = useJobs();
  const [mode, setMode] = useState("auto");
  const [lang, setLang] = useState("auto");
  const [enhance, setEnhance] = useState("auto");
  const [drag, setDrag] = useState(false);
  const [errors, setErrors] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const input = useRef<HTMLInputElement>(null);
  useEffect(() => { api.config().then(setCfg).catch(() => setErrors(["Cannot reach the OMNISCAN API. Is the backend running on port 8000?"])); }, []);

  const send = useCallback(async (files: File[]) => {
    if (!files.length) return;
    setBusy(true); setErrors([]);
    try {
      const r = await api.upload(files, { mode, lang, enhance });
      const errs = r.jobs.filter((x) => !x.ok).map((x: any) => `${x.filename}: ${x.error}`);
      setErrors(errs);
      const ok = r.jobs.filter((x) => x.ok) as { ok: true; job: Job }[];
      if (ok.length) toast(`${ok.length} file${ok.length > 1 ? "s" : ""} queued`);
      await refresh();
      if (ok.length === 1 && !errs.length && !batch) router.push(`/scan/${ok[0].job.id}`);
    } catch (e: any) { setErrors([e.message]); toast("Upload failed", "err"); } finally { setBusy(false); }
  }, [mode, lang, enhance, refresh, router, batch, toast]);

  useEffect(() => {
    const onPaste = (e: ClipboardEvent) => {
      const fs = Array.from(e.clipboardData?.files || []);
      if (fs.length) { e.preventDefault(); send(fs.map((f, i) => (f.name === "image.png" ? new File([f], `pasted-${Date.now()}-${i}.png`, { type: f.type }) : f))); }
    };
    window.addEventListener("paste", onPaste);
    return () => window.removeEventListener("paste", onPaste);
  }, [send]);

  const active = jobs.filter((j) => j.status === "queued" || j.status === "running");
  const finished = jobs.filter((j) => j.status !== "queued" && j.status !== "running");
  const vlm = cfg?.engines.find((e) => e.kind === "vlm" && e.available);

  return (
    <div className="space-y-8">
      <div
        onDragOver={(e) => { e.preventDefault(); setDrag(true); }} onDragLeave={() => setDrag(false)}
        onDrop={(e) => { e.preventDefault(); setDrag(false); send(Array.from(e.dataTransfer.files)); }}
        className={`reg relative flex min-h-[320px] flex-col justify-between overflow-hidden border border-ink p-6 transition-colors lg:min-h-[380px] ${drag ? "bg-lime" : "bg-surface"}`}
      >
        <div className="mono flex justify-between text-ink2"><span>{batch ? "BATCH INTAKE" : "INTAKE"}</span><span>{busy ? "UPLOADING…" : drag ? "RELEASE TO SCAN" : "READY"}</span></div>
        <div>
          <motion.div animate={drag ? { y: -4 } : { y: 0 }}><UploadCloud size={34} strokeWidth={1.4} /></motion.div>
          <p className="display mt-4 text-[clamp(40px,5.4vw,82px)] uppercase">{drag ? "Drop it." : batch ? "Drop a stack." : "Drop a page."}</p>
          <p className="mt-3 max-w-[46ch] text-[15px] text-ink2">Images or PDFs{batch ? ", as many as you like" : ""}. Or paste a screenshot with <kbd className="mono border border-ink px-1">Ctrl</kbd> <kbd className="mono border border-ink px-1">V</kbd>.</p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <button className="btn btn-primary !h-11" disabled={busy} onClick={() => input.current?.click()}>Browse files</button>
          <span className="mono flex items-center gap-1.5 text-ink3"><ClipboardPaste size={12} />{cfg ? `${cfg.formats.join(" · ")} · ≤ ${cfg.max_upload_mb} MB · ≤ ${cfg.max_pdf_pages} PAGES` : "…"}</span>
        </div>
        <input ref={input} type="file" hidden multiple accept="image/png,image/jpeg,image/webp,image/bmp,image/tiff,application/pdf" onChange={(e) => { send(Array.from(e.target.files || [])); e.target.value = ""; }} />
        {busy && <div className="sweep absolute inset-x-0 bottom-0 h-1 overflow-hidden bg-ink" />}
      </div>

      <div className="grid gap-5 border border-ink bg-surface p-5 md:grid-cols-3">
        <div><p className="eyebrow mb-2">Mode</p><div className="seg flex-wrap" role="group" aria-label="Mode">{MODES.map(([k, l]) => <button key={k} aria-pressed={mode === k} onClick={() => setMode(k)}>{l}</button>)}</div></div>
        <div><p className="eyebrow mb-2">Language</p>
          <select className="field w-full" value={lang} onChange={(e) => setLang(e.target.value)} aria-label="Language"><option value="auto">Detect automatically</option>
            {cfg?.languages.map((l) => <option key={l.code} value={l.code}>{l.name}{l.rtl ? " (RTL)" : ""}</option>)}</select></div>
        <div><p className="eyebrow mb-2">Enhancement</p><div className="seg" role="group" aria-label="Enhancement">{[["auto", "Auto"], ["off", "Off"], ["aggressive", "Strong"]].map(([k, l]) => <button key={k} aria-pressed={enhance === k} onClick={() => setEnhance(k)}>{l}</button>)}</div></div>
      </div>

      <AnimatePresence>
        {(mode === "handwriting" || mode === "academic") && cfg && !vlm && (
          <motion.p initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0, height: 0 }} role="status" className="border border-warn bg-warn/10 px-4 py-3 text-[13px]">
            <b>No vision-language engine is available</b>, so {mode === "handwriting" ? "handwriting" : "equations"} fall back to the printed-text recogniser and will be unreliable. See <Link className="underline" href="/app/settings">Settings</Link>.</motion.p>)}
      </AnimatePresence>
      {errors.map((e, i) => <p key={i} role="alert" className="border border-bad px-4 py-3 text-[13px] text-bad">{e}</p>)}

      {active.length > 0 && (
        <section aria-live="polite"><h2 className="eyebrow mb-3">Processing · {active.length}</h2>
          <div className="grid gap-3 md:grid-cols-2">{active.map((j) => <ProcessingCard key={j.id} j={j} stages={cfg?.stages || []} />)}</div></section>)}

      {batch && finished.length > 0 && <section><h2 className="eyebrow mb-3">Results</h2><JobList jobs={finished.slice(0, 30)} onChange={refresh} /></section>}
    </div>
  );
}
