"use client";
import { use, useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import type { Box, Config, Job, Page, Word } from "@/lib/types";
import Viewer, { type Selection } from "@/components/Viewer";
import { Banners, CleanedPane, DetailsPane, ExtractedPane, StructurePane } from "@/components/Panes";
import { ProcessingCard } from "@/components/ProcessingCard";

const TABS = [["extracted", "Extracted text"], ["cleaned", "Cleaned text"], ["structure", "Document structure"], ["details", "Recognition details"]] as const;
type Tab = (typeof TABS)[number][0];

export default function Workspace({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [job, setJob] = useState<Job | null>(null);
  const [pages, setPages] = useState<Page[] | null>(null);
  const [cfg, setCfg] = useState<Config | null>(null);
  const [pi, setPi] = useState(0);
  const [tab, setTab] = useState<Tab>("extracted");
  const [sel, setSel] = useState<Selection>(null);
  const [q, setQ] = useState("");
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");
  const [saved, setSaved] = useState<"" | "saving" | "saved">("");
  const [view, setView] = useState<"original" | "enhanced">("original");
  const [regions, setRegions] = useState(true);
  const [cropMode, setCropMode] = useState(false);
  const [crop, setCrop] = useState<Box | null>(null);
  const [err, setErr] = useState("");
  const [mobilePane, setMobilePane] = useState<"image" | "text">("text");
  const [copied, setCopied] = useState(false);
  const [size, setSize] = useState(16);
  const saveTimer = useRef<ReturnType<typeof setTimeout>>(undefined);

  const load = useCallback(async () => {
    try {
      const r = await api.job(id);
      setJob(r.job);
      if (r.result) setPages(r.result.pages);
    } catch (e: any) { setErr(e.message); }
  }, [id]);
  useEffect(() => { load(); api.config().then(setCfg).catch(() => {}); }, [load]);
  useEffect(() => {
    if (!job || (job.status !== "queued" && job.status !== "running")) return;
    const t = setInterval(async () => {
      try { const s = await api.status(id); setJob(s); if (s.status === "done") { setPages(null); load(); } else if (s.status !== "running" && s.status !== "queued") load(); } catch {}
    }, 800);
    return () => clearInterval(t);
  }, [job, id, load]);

  const page = pages?.[pi] ?? null;
  useEffect(() => { setSel(null); setEditing(false); setCrop(null); setCropMode(false); }, [pi]);
  const rtl = !!page?.language.rtl;

  const startEdit = () => { if (!page) return; setDraft(page.edited_text ?? page.raw_text); setEditing(true); };
  const onText = (t: string) => {
    setDraft(t); setSaved("saving");
    clearTimeout(saveTimer.current);
    saveTimer.current = setTimeout(async () => {
      await api.saveText(id, pi + 1, t);
      setPages((ps) => ps && ps.map((p, i) => (i === pi ? { ...p, edited_text: t } : p)));
      setSaved("saved");
    }, 600);
  };
  const resetEdit = async () => {
    await api.saveText(id, pi + 1, null);
    setPages((ps) => ps && ps.map((p, i) => (i === pi ? { ...p, edited_text: null } : p)));
    setEditing(false);
  };
  const applyAlt = async (w: Word, alt: string) => {
    if (!page) return;
    const lines = (page.edited_text ?? page.raw_text).split("\n");
    const ln = page.lines.find((l) => l.words.some((x) => x.id === w.id));
    const idx = ln ? lines.findIndex((l) => l.includes(w.text)) : -1;
    if (idx < 0) { setDraft(page.edited_text ?? page.raw_text); setEditing(true); return; }
    lines[idx] = lines[idx].replace(w.text, alt);
    const t = lines.join("\n");
    await api.saveText(id, pi + 1, t);
    setPages((ps) => ps && ps.map((p, i) => (i === pi ? { ...p, edited_text: t } : p)));
  };

  const textForCopy = useMemo(() => {
    if (!page) return "";
    if (page.edited_text !== null && (tab === "extracted" || tab === "cleaned")) return page.edited_text;
    return tab === "cleaned" ? page.cleaned_text : page.raw_text;
  }, [page, tab]);
  const allText = () => (pages ?? []).map((p) => p.edited_text ?? (tab === "cleaned" ? p.cleaned_text : p.raw_text)).join("\n\n");
  const copy = async () => { try { await navigator.clipboard.writeText(allText()); setCopied(true); setTimeout(() => setCopied(false), 1400); } catch { setErr("Clipboard access was blocked by the browser."); } };

  const rescan = async (body: Record<string, unknown>) => {
    try { await api.retry(id, body); setPages(null); setCrop(null); setCropMode(false); setJob((j) => j && { ...j, status: "queued" }); } catch (e: any) { setErr(e.message); }
  };

  if (err && !job) return <main className="mx-auto max-w-xl px-5 py-24 text-center"><p className="display text-5xl uppercase">Not found</p><p className="mt-2 text-ink2">{err}</p><Link className="btn btn-primary mt-6" href="/app/history">Back to history</Link></main>;
  if (!job) return <main className="px-5 py-24 text-center text-ink2">Loading…</main>;

  if (job.status === "queued" || job.status === "running")
    return <main className="mx-auto max-w-xl px-5 py-24"><h1 className="mb-6 display text-5xl uppercase">Reading {job.filename}</h1><ProcessingCard j={job} stages={cfg?.stages || []} />
      <button className="btn mt-4" onClick={() => api.cancel(id)}>Cancel</button></main>;

  if (job.status === "failed" || job.status === "cancelled" || !page)
    return (
      <main className="mx-auto max-w-xl px-5 py-24">
        <h1 className="display text-5xl uppercase">{job.status === "cancelled" ? "Cancelled" : "That didn’t work"}</h1>
        <p role="alert" className="mt-3 rounded-xl border border-bad/40 px-4 py-3 text-bad">{job.error || "Processing stopped."}</p>
        <div className="mt-5 flex gap-2"><button className="btn btn-primary" onClick={() => rescan({})}>Retry</button>
          <button className="btn" onClick={() => rescan({ enhance: "aggressive" })}>Retry with aggressive enhancement</button><Link className="btn btn-ghost" href="/app/history">Back</Link></div>
      </main>
    );

  const multi = pages!.length > 1;
  const imgSrc = api.image(id, page.page, page.source === "ocr" ? view : "original");
  const pane = (
    <div className="flex h-full min-h-0 flex-col gap-3">
      <div className="flex flex-wrap items-center gap-2">
        <div role="tablist" className="seg flex-wrap">
          {TABS.map(([k, label]) => <button key={k} role="tab" aria-selected={tab === k} onClick={() => setTab(k)}
            className="!h-9 !px-3">{label}</button>)}
        </div>
        <div className="ml-auto flex items-center gap-1.5">
          <div className="seg" aria-label="Text size">{[[14, "A-"], [16, "A"], [20, "A+"]].map(([n, l]) => <button key={n} aria-pressed={size === n} onClick={() => setSize(n as number)} style={{ height: "2.2rem" }}>{l}</button>)}</div>
          <input className="field w-36" placeholder="Search text" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search within extracted text" />
          {q && <span className="text-[11px] text-ink3">{page.lines.reduce((a, l) => a + l.words.filter((w) => w.text.toLowerCase().includes(q.toLowerCase())).length, 0)} hits</span>}
        </div>
      </div>
      <Banners page={page} />
      <div className="flex flex-wrap items-center gap-2">
        {tab === "extracted" && (editing ?
          <><button className="btn" onClick={() => setEditing(false)}>Done</button>{page.edited_text !== null && <button className="btn btn-ghost" onClick={resetEdit}>Discard edits</button>}<span className="text-[12px] text-ink3">{saved === "saving" ? "Saving…" : saved === "saved" ? "Saved" : "Edits are saved automatically and used in exports."}</span></> :
          <button className="btn" onClick={startEdit}>Edit text</button>)}
        <button className="btn" onClick={copy}>{copied ? "Copied ✓" : multi ? "Copy all pages" : "Copy all"}</button>
        <details className="relative">
          <summary className="btn cursor-pointer list-none !h-9">Download ▾</summary>
          <div className="absolute left-0 z-20 mt-1 w-48 rounded-xl border border-line bg-surface p-1 shadow-lg">
            {[["txt", "Plain text (.txt)"], ["md", "Markdown (.md)"], ["docx", "Word (.docx)"], ["json", "Structured JSON"]].map(([f, label]) => (
              <a key={f} className="block rounded-lg px-3 py-2 hover:bg-sunken" href={api.exportUrl(id, f, tab === "extracted" ? "raw" : "cleaned")}>{label}</a>))}
            <p className="px-3 pb-1.5 pt-1 text-[11px] text-ink3">{tab === "extracted" ? "Exports the raw recognition" : "Exports cleaned text"} (your edits take precedence).</p>
          </div>
        </details>
        <details className="relative ml-auto">
          <summary className="btn cursor-pointer list-none !h-9">Re-scan ▾</summary>
          <RescanMenu cfg={cfg} job={job} crop={crop} onGo={rescan} onCrop={() => { setCropMode(true); setMobilePane("image"); }} />
        </details>
      </div>
      <div className="min-h-[320px] flex-1 lg:min-h-0">
        {tab === "extracted" && <ExtractedPane page={page} selection={sel} onSelect={(i) => setSel({ kind: "word", id: i })} q={q} editing={editing} text={draft} onText={onText} rtl={rtl} onApplyAlt={applyAlt} size={size} />}
        {tab === "cleaned" && <CleanedPane page={page} q={q} rtl={rtl} size={size} />}
        {tab === "structure" && <StructurePane page={page} onBox={(b) => { setSel(b ? { kind: "box", box: b } : null); setMobilePane("image"); }} />}
        {tab === "details" && <DetailsPane page={page} jobId={id} onBox={() => {}} />}
      </div>
    </div>
  );

  return (
    <main className="flex flex-col px-4 pb-6 pt-4 lg:px-6 lg:h-dvh">
      <div className="mb-3 flex flex-wrap items-center gap-3">
        <Link href="/app/history" className="btn btn-ghost btn-icon" aria-label="Back to history">←</Link>
        <div className="min-w-0"><h1 className="truncate display text-[34px] leading-none">{job.filename}</h1>
          <p className="mt-1 text-[12px] text-ink3">{page.language.name}{page.language.rtl ? " · RTL" : ""} · {page.stats.words} words · mean score {page.stats.mean_conf !== null ? `${Math.round(page.stats.mean_conf * 100)}%` : "n/a"} · {page.stats.uncertain_words} uncertain · {job.summary?.seconds}s</p></div>
        {multi && <div className="ml-auto flex items-center gap-1"><button className="btn btn-icon" disabled={pi === 0} onClick={() => setPi(pi - 1)} aria-label="Previous page">‹</button>
          <span className="px-2 text-[13px] tabular-nums">Page {pi + 1} / {pages!.length}</span><button className="btn btn-icon" disabled={pi === pages!.length - 1} onClick={() => setPi(pi + 1)} aria-label="Next page">›</button></div>}
      </div>
      <div className="seg mb-3 flex lg:hidden" role="tablist">{(["image", "text"] as const).map((k) => <button key={k} role="tab" aria-selected={mobilePane === k} onClick={() => setMobilePane(k)} className="flex-1 capitalize">{k}</button>)}</div>
      <div className="grid min-h-0 flex-1 gap-4 lg:grid-cols-2">
        <section className={`flex min-h-[420px] min-w-0 flex-col gap-2 lg:min-h-0 ${mobilePane === "image" ? "" : "hidden lg:flex"}`} aria-label="Original image">
          <div className="flex flex-wrap items-center gap-2">
            {page.source === "ocr" && <div className="seg">{(["original", "enhanced"] as const).map((v) => <button key={v} onClick={() => setView(v)} aria-pressed={view === v}
              className="capitalize">{v}</button>)}</div>}
            <label className="flex items-center gap-1.5 text-[12px] text-ink2"><input type="checkbox" checked={regions} onChange={(e) => setRegions(e.target.checked)} />Word regions</label>
            <button className={`btn !h-8 ${cropMode ? "btn-primary" : ""}`} onClick={() => { setCropMode(!cropMode); if (cropMode) setCrop(null); }}>Select area</button>
            {crop && <button className="btn btn-primary !h-8" onClick={() => rescan({ crop: crop.map(Math.round) })}>Re-scan selection</button>}
            {!page.has_word_boxes && page.lines.length > 0 && <span className="text-[12px] text-ink3">Word-level alignment unavailable for this result.</span>}
          </div>
          <div className="min-h-0 flex-1">
            <Viewer src={imgSrc} page={page} selection={sel} showRegions={regions} cropMode={cropMode} crop={crop} onCrop={setCrop} onSelectWord={(i) => { setSel({ kind: "word", id: i }); setTab("extracted"); setMobilePane("text"); }} />
          </div>
        </section>
        <section className={`min-h-0 min-w-0 ${mobilePane === "text" ? "" : "hidden lg:block"}`} aria-label="Extracted text">{pane}</section>
      </div>
    </main>
  );
}

function RescanMenu({ cfg, job, crop, onGo, onCrop }: { cfg: Config | null; job: Job; crop: Box | null; onGo: (b: Record<string, unknown>) => void; onCrop: () => void }) {
  const [mode, setMode] = useState(job.options.mode || "auto");
  const [lang, setLang] = useState(job.options.lang || "auto");
  const [enh, setEnh] = useState(job.options.enhance || "auto");
  return (
    <div className="absolute right-0 z-20 mt-1 w-72 space-y-3 rounded-2xl border border-line bg-surface p-4 shadow-lg">
      <label className="block text-[12px] text-ink3">Mode<select className="field mt-1 w-full" value={mode} onChange={(e) => setMode(e.target.value)}>{(cfg?.modes || []).map((m) => <option key={m}>{m}</option>)}</select></label>
      <label className="block text-[12px] text-ink3">Language<select className="field mt-1 w-full" value={lang} onChange={(e) => setLang(e.target.value)}><option value="auto">Detect automatically</option>{cfg?.languages.map((l) => <option key={l.code} value={l.code}>{l.name}</option>)}</select></label>
      <label className="block text-[12px] text-ink3">Enhancement<select className="field mt-1 w-full" value={enh} onChange={(e) => setEnh(e.target.value)}><option value="auto">Auto</option><option value="off">Off</option><option value="aggressive">Aggressive</option></select></label>
      <div className="flex flex-wrap gap-2">
        <button className="btn btn-primary" onClick={() => onGo({ mode, lang, enhance: enh })}>Re-scan page</button>
        <button className="btn" onClick={() => onGo({ mode, lang, enhance: enh, rotate90: ((job.options.rotate90 || 0) + 1) % 4 })}>Rotate 90° &amp; scan</button>
        <button className="btn" onClick={onCrop}>Select area…</button>
        {job.options.crop && <button className="btn btn-ghost" onClick={() => onGo({ clear_crop: true })}>Clear area</button>}
      </div>
    </div>
  );
}
