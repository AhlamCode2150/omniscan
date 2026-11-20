"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import type { Block, Box, Page, Word } from "@/lib/types";
import type { Selection } from "./Viewer";

const pct = (c: number | null) => (c === null ? "n/a" : `${Math.round(c * 100)}%`);
const FLAG_TEXT: Record<string, string> = {
  "low-confidence": "Engine reported low confidence", review: "Moderate confidence – worth a look", conflict: "Engines disagree",
  "number-mismatch": "Engines read this number differently", illegible: "Marked illegible by the model", "crossed-out": "Crossed out in the source",
  "mixed-letters-digits": "Mixes letters and digits – check for misread characters", "suspicious-char": "Contains an unusual symbol", "repeated-word": "Repeated word",
  "invalid-char": "Invalid character", agreed: "Both engines agree", "no-engine-confidence": "This engine gives no per-word confidence", "pdf-text-layer": "From the PDF text layer",
  "only-in-primary": "Second engine did not read this word",
};
const hit = (t: string, q: string) => !!q && t.toLowerCase().includes(q.toLowerCase());

export function Highlight({ text, q }: { text: string; q: string }) {
  if (!q) return <>{text}</>;
  const parts = text.split(new RegExp(`(${q.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")})`, "gi"));
  return <>{parts.map((p, i) => (p.toLowerCase() === q.toLowerCase() ? <mark key={i} className="rounded bg-warn/40 text-inherit">{p}</mark> : p))}</>;
}

export function Banners({ page }: { page: Page }) {
  const v = page.verification;
  return (
    <div className="space-y-2">
      {page.warnings.map((w, i) => <p key={i} role="status" className="border border-warn bg-warn/10 px-3.5 py-2.5 text-[13px]">{w}</p>)}
      <p className="flex items-start gap-2 text-[12px] text-ink2">
        <span className={`mt-[3px] inline-block h-2 w-2 shrink-0 ${v.level === "cross-checked" ? "bg-good" : "bg-ink3"}`} />
        <span><b className="font-medium text-ink">{v.level === "cross-checked" ? "Cross-checked" : v.level === "native-text" ? "Native PDF text" : "Single engine"}.</b> {v.statement}
          {v.agreement?.agreement != null && <> Word agreement with Tesseract: {Math.round(v.agreement.agreement * 100)}% ({v.agreement.conflict} conflicts).</>}</span>
      </p>
    </div>
  );
}

export function ExtractedPane({ page, selection, onSelect, q, editing, text, onText, rtl, onApplyAlt, size = 16 }: {
  page: Page; selection: Selection; onSelect: (id: string) => void; q: string; editing: boolean; text: string; onText: (t: string) => void; rtl: boolean;
  onApplyAlt: (w: Word, alt: string) => void; size?: number;
}) {
  const sel = useMemo(() => {
    if (selection?.kind !== "word") return null;
    for (const l of page.lines) for (const w of l.words) if (w.id === selection.id) return w;
    return null;
  }, [selection, page]);
  const selRef = useRef<HTMLSpanElement>(null);
  useEffect(() => { selRef.current?.scrollIntoView({ block: "nearest", behavior: "smooth" }); }, [sel?.id]);
  if (editing) {
    return <textarea value={text} onChange={(e) => onText(e.target.value)} dir={rtl ? "rtl" : "ltr"} spellCheck={false} aria-label="Editable extracted text"
      className="scroll-thin h-full min-h-[300px] w-full resize-none border border-ink bg-surface p-4 font-mono text-[13.5px] leading-7 outline-none focus:border-accent" />;
  }
  return (
    <div className="flex h-full min-h-0 flex-col">
      <div dir={rtl ? "rtl" : "ltr"} className="scroll-thin min-h-0 flex-1 overflow-auto border border-ink bg-surface p-4 leading-[2]" style={{ fontSize: size }}>
        {page.edited_text !== null && <p dir="ltr" className="mb-3 rounded-lg bg-sunken px-3 py-2 text-[12px] text-ink2">You have edited this page. Showing the original recognition here; the Edit view shows your version.</p>}
        {page.lines.length === 0 && <p className="text-ink3">No text was recognised on this page.</p>}
        {page.lines.map((l) => (
          <p key={l.id} className="[&:not(:last-child)]:mb-0.5">
            {l.words.map((w, i) => {
              const cls = ["w", w.status === "uncertain" ? (w.flags.includes("conflict") || w.flags.includes("illegible") || (w.conf !== null && w.conf < 0.6) ? "bad" : "warn") : w.flags.includes("review") ? "warn" : "",
                sel?.id === w.id ? "sel" : "", hit(w.text, q) ? "hit" : ""].join(" ");
              return <span key={w.id} ref={sel?.id === w.id ? selRef : undefined}><span className={cls} role="button" tabIndex={0} onClick={() => onSelect(w.id)} onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && onSelect(w.id)}
                title={`${pct(w.conf)}${w.flags.length ? " · " + w.flags.map((f) => FLAG_TEXT[f] || f).join("; ") : ""}`}>{w.text}</span>{i < l.words.length - 1 ? " " : ""}</span>;
            })}
          </p>
        ))}
      </div>
      {sel && (
        <div className="rise mt-3 border border-ink bg-surface p-3.5 text-[13px]" dir="ltr">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-display text-2xl leading-none">{sel.text}</span>
            <span className="chip">{pct(sel.conf)} {sel.conf !== null && "engine score"}</span>
            <span className="chip">{sel.engine}</span>
            {sel.est_box && <span className="chip" title="The word box is estimated by splitting the line box.">approximate position</span>}
            <span className={`chip ${sel.status === "uncertain" ? "border-warn/50 text-warn" : ""}`}>{sel.status}</span>
          </div>
          {sel.flags.length > 0 && <ul className="mt-2 list-disc pl-5 text-ink2">{sel.flags.map((f) => <li key={f}>{FLAG_TEXT[f] || f}</li>)}</ul>}
          {sel.alts.length > 0 && (
            <div className="mt-2.5"><p className="eyebrow mb-1.5">Other readings</p>
              <div className="flex flex-wrap gap-2">{sel.alts.map((a, i) => (
                <button key={i} className="btn !h-8" onClick={() => onApplyAlt(sel, a.text)} title={`Replace in your edited text`}>
                  {a.text}<span className="text-[11px] text-ink3">{a.engine}{a.conf != null ? ` · ${pct(a.conf)}` : ""}</span></button>))}</div></div>
          )}
        </div>
      )}
      <p className="mt-2 text-[11.5px] text-ink3">Underlines: <span className="underline decoration-warn decoration-wavy underline-offset-4">review</span> · <span className="underline decoration-bad decoration-wavy underline-offset-4">uncertain</span>. Scores are reported by the engine; they are not calibrated probabilities.</p>
    </div>
  );
}

export function CleanedPane({ page, q, rtl, size = 16 }: { page: Page; q: string; rtl: boolean; size?: number }) {
  return (
    <div className="scroll-thin h-full min-h-0 space-y-4 overflow-auto">
      <div dir={rtl ? "rtl" : "ltr"} className="whitespace-pre-wrap border border-ink bg-surface p-4 leading-8" style={{ fontSize: size }}><Highlight text={page.cleaned_text || "—"} q={q} /></div>
      <div className="border border-ink bg-surface p-4">
        <p className="eyebrow">What changed from the raw recognition</p>
        {page.cleaning_log.length === 0 ? <p className="mt-2 text-ink2">Nothing – paragraphs were only re-joined from lines. Cleaning is rule-based (spacing, ligatures, hyphenated line breaks); no language model rewrites your text.</p> :
          <ul className="mt-2 space-y-1.5 text-[13px]">{page.cleaning_log.slice(0, 60).map((c, i) => <li key={i}><b className="font-medium">{c.change}</b><span className="ml-2 font-mono text-[12px] text-ink3">{c.before.slice(0, 70)} → {c.after.slice(0, 70)}</span></li>)}</ul>}
      </div>
      {page.math && (
        <div className="border border-ink bg-surface p-4">
          <p className="eyebrow">Math &amp; formulas</p>
          <p className="mt-1 text-[12px] text-ink2">{page.math.note}</p>
          {page.math.latex_from_vlm && <pre className="mt-3 overflow-auto rounded-lg bg-sunken p-3 font-mono text-[12.5px] whitespace-pre-wrap">{page.math.latex_from_vlm}</pre>}
          <p className="mt-3 text-[12px] text-ink3">Normalized (conservative Unicode→LaTeX of recognised symbols)</p>
          <pre className="mt-1 overflow-auto rounded-lg bg-sunken p-3 font-mono text-[12.5px] whitespace-pre-wrap">{page.math.normalized_latex}</pre>
          {page.math.chemical_formulas.length > 0 && <p className="mt-3 text-[13px]">Chemical formulas: {page.math.chemical_formulas.map((f) => `${f.recognized} → ${f.normalized}`).join(", ")}</p>}
        </div>
      )}
    </div>
  );
}

const TYPE_LABEL: Record<string, string> = { heading: "Heading", paragraph: "Paragraph", list: "List", table: "Table", checkbox: "Checkbox", "form-field": "Form field", header: "Header", footer: "Footer", "page-number": "Page number", footnote: "Footnote" };

export function StructurePane({ page, onBox }: { page: Page; onBox: (b: Box | null) => void }) {
  return (
    <div className="scroll-thin h-full min-h-0 space-y-2 overflow-auto">
      <p className="text-[12px] text-ink3">Detected with layout heuristics ({page.stats.columns} column{page.stats.columns > 1 ? "s" : ""}, {page.stats.tables} ruled table{page.stats.tables === 1 ? "" : "s"}). {page.layout_notes.join(" ")} Click a block to find it in the image.</p>
      {page.blocks.length === 0 && <p className="text-ink3">No structure detected.</p>}
      {page.blocks.map((b: Block, i) => (
        <button key={i} onClick={() => onBox(b.box)} className="block w-full border border-ink bg-surface p-3 text-left transition hover:border-ink3">
          <span className="eyebrow">{TYPE_LABEL[b.type]}{b.type === "heading" ? ` · H${b.level}` : ""}{b.type === "list" ? (b.ordered ? " · numbered" : " · bulleted") : ""}</span>
          <div className="mt-1">
            {b.type === "heading" && <p className={b.level === 1 ? "font-display text-3xl" : "font-display text-2xl"}>{b.text}</p>}
            {b.type === "paragraph" && <p>{b.lines?.join(" ")}</p>}
            {b.type === "list" && <ul className={`pl-5 ${b.ordered ? "list-decimal" : "list-disc"}`}>{b.items?.map((it, k) => <li key={k}>{it}</li>)}</ul>}
            {b.type === "checkbox" && <p>{b.checked ? "☑" : "☐"} {b.text}</p>}
            {b.type === "table" && (
              <div className="overflow-x-auto"><table className="mt-1 w-full border-collapse text-[13px]"><tbody>{b.rows?.map((r, ri) => (
                <tr key={ri}>{r.map((c, ci) => <td key={ci} className={`border border-line px-2 py-1 ${ri === 0 ? "bg-sunken font-medium" : ""}`}>{c.text}</td>)}</tr>))}</tbody></table></div>)}
            {!["heading", "paragraph", "list", "checkbox", "table"].includes(b.type) && <p className="text-ink2">{b.text}</p>}
          </div>
        </button>
      ))}
    </div>
  );
}

function Row({ k, v }: { k: string; v: React.ReactNode }) {
  return <div className="flex justify-between gap-4 border-b border-line py-1.5 last:border-0"><dt className="text-ink2">{k}</dt><dd className="text-right font-medium tabular-nums">{v}</dd></div>;
}

export function DetailsPane({ page, jobId, onBox }: { page: Page; jobId: string; onBox: (b: Box | null) => void }) {
  const a = page.analysis, hw = page.handwriting;
  return (
    <div className="scroll-thin h-full min-h-0 space-y-4 overflow-auto text-[13px]">
      <Sec title="Result"><dl>
        <Row k="Words / lines" v={`${page.stats.words} / ${page.stats.lines}`} />
        <Row k="Mean engine score" v={pct(page.stats.mean_conf)} />
        <Row k="Uncertain words" v={page.stats.uncertain_words} />
        <Row k="Source" v={page.source === "ocr" ? "Recognised from pixels" : "PDF text layer"} />
        <Row k="Processing time" v={`${page.stats.seconds}s`} />
      </dl></Sec>
      <Sec title="Language"><dl>
        <Row k="Detected / chosen" v={`${page.language.name}${page.language.code ? ` (${page.language.code})` : ""}`} />
        <Row k="How" v={`${page.language.source} – ${page.language.basis}`} />
        <Row k="Direction" v={page.language.rtl ? "Right-to-left" : "Left-to-right"} />
      </dl>{page.language.note && <p className="mt-2 text-ink3">{page.language.note}</p>}
        {page.language.trials.length > 0 && <p className="mt-2 text-ink3">Script trials (higher is better): {page.language.trials.map(([s, v]) => `${s} ${v}`).join(" · ")}</p>}</Sec>
      <Sec title="Engines">
        <ul className="space-y-2">{page.engines.map((e, i) => (
          <li key={i} className="rounded-lg bg-sunken px-3 py-2">
            <b className="font-medium">{e.name}</b> <span className="text-ink3">{e.role || ""}</span>
            {e.skipped ? <p className="text-ink3">Skipped: {e.skipped}</p> : e.error ? <p className="text-bad">Error: {e.error}</p> :
              <p className="text-ink2">{e.lines} lines · {e.seconds}s{e.mean_conf != null ? ` · mean score ${pct(e.mean_conf)}` : " · no confidence provided"}{e.model ? ` · ${e.model}` : ""}</p>}
          </li>))}</ul>
      </Sec>
      {hw && <Sec title="Handwriting analysis"><dl>
        <Row k="Handwriting likelihood (heuristic)" v={`${Math.round(hw.score * 100)}%`} />
        <Row k="Vision-language transcription used" v={hw.used_vlm ? "Yes" : "No"} />
        <Row k="Stroke-width variation" v={hw.stroke_width_cv} /><Row k="Component-height variation" v={hw.component_height_cv} /><Row k="Baseline jitter" v={`${hw.baseline_jitter_deg}°`} />
      </dl><p className="mt-2 text-ink3">{hw.note}</p></Sec>}
      {a && <Sec title="Image analysis"><dl>
        <Row k="Size" v={`${a.width}×${a.height} (${a.megapixels} MP)`} /><Row k="Sharpness (Laplacian var.)" v={a.sharpness} /><Row k="Contrast" v={a.contrast} />
        <Row k="Skew" v={`${a.skew_deg}°`} /><Row k="Lighting unevenness" v={a.lighting_unevenness} /><Row k="Noise" v={a.noise} />
      </dl><p className="mt-2 text-ink2">{a.issues.length ? `Detected: ${a.issues.join(", ")}.` : "No major image problems detected."}</p></Sec>}
      <Sec title="Enhancement">
        <p className="text-ink2">{page.enhancement.steps.length ? page.enhancement.steps.join(" → ") : "None applied."} The original file is never modified.</p>
        {page.source === "ocr" && <div className="mt-3 grid grid-cols-2 gap-2">
          {/* eslint-disable @next/next/no-img-element */}
          <figure><img className="w-full rounded-lg border border-line" src={`/api/jobs/${jobId}/image/${page.page}?variant=original`} alt="Original" /><figcaption className="mt-1 text-center text-[11px] text-ink3">Original</figcaption></figure>
          <figure><img className="w-full rounded-lg border border-line" src={`/api/jobs/${jobId}/image/${page.page}?variant=enhanced`} alt="Enhanced copy sent to the recogniser" /><figcaption className="mt-1 text-center text-[11px] text-ink3">Enhanced copy used for recognition</figcaption></figure>
        </div>}
      </Sec>
      <Sec title={`Verification flags (${page.issues.length})`}>
        {page.issues.length === 0 ? <p className="text-ink2">{page.verification.level === "cross-checked" ? "No disagreements, missing text, or suspicious output detected by the checks." : "No suspicious output detected by the single-engine checks (this is not independent verification)."}</p> :
          <ul className="space-y-1.5">{page.issues.slice(0, 80).map((is, i) => (
            <li key={i} className="rounded-lg bg-sunken px-3 py-2"><b className="font-medium">{is.type}</b> – {is.detail}{is.text ? <span className="ml-1 font-mono text-[12px] text-ink3">“{is.text}”</span> : null}</li>))}</ul>}
      </Sec>
    </div>
  );
}

function Sec({ title, children }: { title: string; children: React.ReactNode }) {
  return <section className="border border-ink bg-surface p-4"><h3 className="eyebrow mb-2">{title}</h3>{children}</section>;
}
