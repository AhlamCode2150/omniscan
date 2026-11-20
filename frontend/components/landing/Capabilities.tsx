"use client";
import { useEffect, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { Headline, SectionTag } from "@/components/ui";

/* ---------- 01 RECOGNIZE: two engines read the same line; disagreement is surfaced, not merged ---------- */
function Recognize() {
  const words = [["Total", "agree"], ["due", "agree"], ["1,250.75", "conflict"], ["before", "agree"], ["Friday.", "agree"]];
  return (
    <div className="space-y-5 p-6">
      <p className="mono text-ink3">SOURCE LINE</p>
      <div className="relative inline-block border border-ink bg-[#fbfaf4] px-4 py-3 font-mono text-[15px]">Total due 1,250.75 before Friday.<span className="absolute -inset-1 border border-dashed border-ink/50" /></div>
      {[["PP-OCRv5", "Total due 1,250.75 before Friday."], ["TESSERACT", "Total due 1,260.75 before Friday."]].map(([e, t], r) => (
        <div key={e} className="flex items-center gap-3"><span className="mono w-24 shrink-0 text-ink2">{e}</span>
          <p className="flex flex-wrap gap-x-2 font-mono text-[14px]">{t.split(" ").map((w, i) => <motion.span key={i} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 * i + r * 0.3 }}
            className={words[i][1] === "conflict" ? "bg-lime px-1 outline outline-1 outline-ink" : ""}>{w}</motion.span>)}</p></div>
      ))}
      <div className="border-l-4 border-ink bg-sunken p-3 text-[13px]"><span className="mono block text-ink2">FLAG · number-mismatch</span>Engines read this number differently. Omniscan keeps the primary reading, shows <b>1,260.75</b> as an alternative, and marks the word uncertain. It never silently picks one.</div>
      <p className="mono text-[9.5px] text-ink3">EXAMPLE OF REAL VERIFICATION BEHAVIOUR (COVERED BY UNIT TESTS).</p>
    </div>
  );
}

/* ---------- 02 UNDERSTAND: handwriting → regions → transcript ---------- */
function Understand() {
  const [s, setS] = useState(0);
  const reduce = useReducedMotion();
  useEffect(() => { if (reduce) { setS(2); return; } const t = setInterval(() => setS((v) => (v + 1) % 3), 2600); return () => clearInterval(t); }, [reduce]);
  const lines = ["Dear Sam, thanks for the notes", "from Tuesday. Meet me at 4:30", "near the old libra[?]"];
  return (
    <div className="grid h-full gap-0 sm:grid-cols-2">
      <div className="relative border-b border-ink p-6 sm:border-b-0 sm:border-r" style={{ backgroundImage: "repeating-linear-gradient(transparent 0 33px, #9fb1c9 33px 34px)" }}>
        <p className="font-[family-name:var(--font-hand)] text-[30px] leading-[34px] text-[#1e3a9a]">{lines.map((l, i) => <span key={i} className="relative block">{l.replace("[?]", "ry")}
          <motion.span className="absolute -inset-x-1 inset-y-1 border border-ink bg-lime/30" animate={{ opacity: s >= 1 ? 1 : 0 }} /></span>)}</p>
        <span className="mono absolute bottom-2 left-3 text-ink3">{["A · ORIGINAL", "B · WRITING REGIONS", "C · RECOGNISED"][s]}</span>
      </div>
      <div className="flex flex-col justify-center gap-3 p-6">
        <p className="mono text-ink3">TRANSCRIPT</p>
        <AnimatePresence mode="wait">{s === 2 ? (
          <motion.div key="t" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="font-mono text-[14px] leading-7">
            {lines.map((l, i) => <p key={i}>{l.split("[?]")[0]}{l.includes("[?]") && <span className="bg-warn/25 underline decoration-warn decoration-wavy underline-offset-4" title="Model declared this illegible">[?]</span>}</p>)}
          </motion.div>) : <motion.p key="w" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="font-mono text-[13px] text-ink3">{s === 0 ? "ink on paper — no text yet" : "locating writing…"}</motion.p>}</AnimatePresence>
        <p className="text-[12.5px] text-ink2">Unreadable parts are marked <code className="bg-sunken px-1">[?]</code> and flagged. The model is told not to guess. Handwriting runs on a local vision model; it gives no per-word score, and the app says so.</p>
      </div>
    </div>
  );
}

/* ---------- 03 TRANSLATE: type wall ---------- */
const SCRIPTS: [string, string, string, "ltr" | "rtl", string][] = [
  ["Hello", "English", "en", "ltr", "var(--font-display)"], ["مرحبا بالعالم", "العربية", "ar", "rtl", "var(--font-ar)"], ["ہیلو دنیا", "اردو", "ur", "rtl", "var(--font-ur)"],
  ["नमस्ते दुनिया", "हिन्दी", "hi", "ltr", "var(--font-hi)"], ["こんにちは", "日本語", "ja", "ltr", "var(--font-ja)"], ["你好世界", "中文", "zh", "ltr", "var(--font-ja)"],
  ["안녕하세요", "한국어", "ko", "ltr", "var(--font-ja)"], ["Привет, мир", "Русский", "ru", "ltr", "var(--font-display)"], ["Guten Tag", "Deutsch", "de", "ltr", "var(--font-display)"],
];
function Translate() {
  const [a, setA] = useState(1);
  return (
    <div className="grid grid-cols-3 border-collapse">
      {SCRIPTS.map(([t, n, c, d, f], i) => (
        <button key={c} onMouseEnter={() => setA(i)} onFocus={() => setA(i)} className={`group relative flex min-h-[110px] flex-col justify-between border-b border-r border-ink p-3 text-left transition-colors ${a === i ? "bg-lime" : ""} ${i % 3 === 2 ? "border-r-0" : ""} ${i > 5 ? "border-b-0" : ""}`}>
          <span className="mono flex w-full justify-between text-[9px] text-ink2"><span>{c}</span><span>{d.toUpperCase()}</span></span>
          <span dir={d} lang={c} className="text-[clamp(22px,2.6vw,38px)] leading-[1.25]" style={{ fontFamily: f }}>{t}</span>
          <span className="mono text-[9px] text-ink2">{n}</span>
        </button>
      ))}
    </div>
  );
}

/* ---------- 04 STRUCTURE: flat OCR vs reconstructed ---------- */
function Structure() {
  return (
    <div className="grid gap-0 sm:grid-cols-2">
      <div className="border-b border-ink p-6 sm:border-b-0 sm:border-r"><p className="mono text-ink3">PRINTED-TEXT ENGINE SEES</p>
        <p className="mt-3 font-mono text-[14px] leading-7">Item<br />Pencil<br />Notebook<br />Qty<br />12<br />5<br />x2 + y2 = z2</p></div>
      <div className="p-6"><p className="mono text-ink3">STRUCTURE STAGE REBUILDS</p>
        <table className="mt-3 w-full border-collapse font-mono text-[13px]"><tbody>{[["Item", "Qty"], ["Pencil", "12"], ["Notebook", "5"]].map((r, i) => <tr key={i}>{r.map((c, j) => <td key={j} className={`border border-ink px-2 py-1 ${i === 0 ? "bg-lime font-bold" : ""}`}>{c}</td>)}</tr>)}</tbody></table>
        <p className="mt-4 font-serif text-[26px] italic">x<sup>2</sup> + y<sup>2</sup> = z<sup>2</sup></p>
        <code className="mono mt-1 block text-[10px] normal-case text-ink2">$$x^2 + y^2 = z^2$$</code>
        <p className="mt-3 text-[12px] text-ink2">Gridded tables are rebuilt from the image. Equations come from the vision model in Academic mode and are marked unverified.</p></div>
    </div>
  );
}

/* ---------- 05 EXPORT ---------- */
const EX: Record<string, string> = {
  TXT: "Quarterly Supply Report\n\nDeliveries rose in the third\nquarter, though two shipments…",
  MD: "# Quarterly Supply Report\n\nDeliveries rose in the third quarter…\n\n| Item | Qty |\n|---|---|\n| Paper | 12 |\n\n- [x] Reorder paper",
  DOCX: "▤ Word document\n  Heading 1 · Paragraph · Table\n  Right-to-left paragraphs for\n  Arabic / Urdu pages",
  JSON: '{ "pages": [{\n  "lines": [{ "text": "…",\n    "words": [{ "text": "Total",\n      "conf": 0.998,\n      "box": [59, 94, 70, 73],\n      "flags": ["agreed"] }]}]\n}]}',
};
function Export() {
  const [t, setT] = useState("MD");
  return (
    <div className="p-6">
      <div className="seg" role="tablist">{Object.keys(EX).map((k) => <button key={k} role="tab" aria-selected={t === k} onClick={() => setT(k)}>{k}</button>)}</div>
      <pre className="mt-4 min-h-[210px] overflow-auto border border-ink bg-[#fbfaf4] p-4 font-mono text-[12.5px] leading-6">{EX[t]}</pre>
      <p className="mt-3 text-[12.5px] text-ink2">Your edits take precedence in every export. Raw recognition and cleaned text stay separate, so nothing is rewritten behind your back.</p>
    </div>
  );
}

const ITEMS = [
  { n: "01", name: "Recognize", line: "Printed text, two engines, one honest answer.", V: Recognize },
  { n: "02", name: "Understand", line: "Handwriting, with doubt shown as doubt.", V: Understand },
  { n: "03", name: "Translate", line: "Fifteen languages. Right-to-left done right.", V: Translate },
  { n: "04", name: "Structure", line: "Tables, headings, lists and equations.", V: Structure },
  { n: "05", name: "Export", line: "Editable, searchable, portable.", V: Export },
];

export default function Capabilities() {
  const [a, setA] = useState(0);
  const V = ITEMS[a].V;
  return (
    <section id="engine" className="border-t border-ink px-5 py-24 lg:px-10 lg:py-32">
      <SectionTag n={4} label="THE FIVE CAPABILITIES" />
      <div className="mt-8 grid gap-10 lg:grid-cols-12">
        <div className="lg:col-span-5">
          <Headline className="text-[clamp(40px,6vw,104px)] uppercase" lines={["Five verbs.", { text: "One engine.", italic: true }]} />
          <ul className="mt-10 border-t border-ink" role="tablist" aria-label="Capabilities">
            {ITEMS.map((it, i) => (
              <li key={it.n}><button role="tab" aria-selected={a === i} onClick={() => setA(i)} onMouseEnter={() => setA(i)} onFocus={() => setA(i)}
                className={`group flex w-full items-baseline gap-4 border-b border-ink py-4 text-left transition-colors ${a === i ? "bg-lime px-4" : "px-0 hover:px-4"} `} style={{ transition: "padding .2s, background .15s" }}>
                <span className="mono w-6 text-ink2">{it.n}</span>
                <span className="display text-[clamp(34px,4.2vw,64px)] uppercase">{it.name}</span>
                <span className="mono ml-auto hidden max-w-[16ch] text-right text-[9.5px] text-ink2 xl:block">{it.line}</span>
              </button></li>
            ))}
          </ul>
        </div>
        <div className="lg:col-span-7">
          <div className="mono mb-2 flex justify-between text-ink2"><span>STAGE {ITEMS[a].n} — {ITEMS[a].name.toUpperCase()}</span><span>{ITEMS[a].line}</span></div>
          <div className="reg min-h-[430px] border border-ink bg-surface shadow-[8px_8px_0_var(--ink)]">
            <AnimatePresence mode="wait"><motion.div key={a} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }} transition={{ duration: 0.25 }}><V /></motion.div></AnimatePresence>
          </div>
        </div>
      </div>
    </section>
  );
}
