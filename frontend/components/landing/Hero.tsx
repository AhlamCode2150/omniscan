"use client";
import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { motion, useReducedMotion } from "framer-motion";
import { ArrowRight } from "lucide-react";
import { Headline, StatusPill } from "@/components/ui";

const DOC = [
  { t: "INVOICE 20418", k: "h", y: 0.1 },
  { t: "Issued 14 March 2024", k: "p", y: 0.19 },
  { t: "Bill to: Lumen Printworks", k: "p", y: 0.27 },
  { t: "Paper stock, 120 gsm ........ 640.00", k: "r", y: 0.4 },
  { t: "Setup & registration ........ 210.75", k: "r", y: 0.48 },
  { t: "Courier, two drops .......... 400.00", k: "r", y: 0.56 },
  { t: "TOTAL DUE 1,250.75", k: "t", y: 0.7 },
  { t: "Please remit before Friday.", k: "p", y: 0.82 },
];

function ScanPlate() {
  const reduce = useReducedMotion();
  const [p, setP] = useState(reduce ? 1 : 0);
  const [manual, setManual] = useState(false);
  const box = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (reduce || manual) return;
    let raf = 0, t0 = performance.now();
    const tick = (t: number) => {
      const c = ((t - t0) / 7000) % 1.35;       // sweep, then rest with everything detected
      setP(Math.min(c, 1.0));
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [reduce, manual]);
  const seen = DOC.filter((d) => d.y + 0.045 < p);
  return (
    <div className="relative">
      <div className="mono mb-2 flex items-center justify-between text-ink2"><span>PLATE 01 — THE SCAN</span><span>{String(Math.round(Math.min(p, 1) * 100)).padStart(3, "0")}%</span></div>
      <div className="grid gap-0 border border-ink bg-surface shadow-[8px_8px_0_var(--ink)] sm:grid-cols-[1.15fr_1fr]">
        <div ref={box} className="reg relative aspect-[4/5] cursor-crosshair touch-none overflow-hidden border-b border-ink bg-[#fbfaf4] sm:border-b-0 sm:border-r"
          onPointerMove={(e) => { const r = box.current!.getBoundingClientRect(); setManual(true); setP(Math.max(0, Math.min(1, (e.clientY - r.top) / r.height))); }}
          onPointerLeave={() => setManual(false)} aria-label="Illustrative document being scanned. Move the pointer to scan manually.">
          <div className="absolute inset-0 px-6 pt-4 font-mono text-[11px] leading-none text-ink">
            {DOC.map((d) => {
              const on = d.y + 0.045 < p;
              return (
                <div key={d.t} className="absolute left-6 right-6" style={{ top: `${d.y * 100}%` }}>
                  <div className={`relative inline-block ${d.k === "h" ? "text-[17px] font-bold tracking-tight" : d.k === "t" ? "text-[13px] font-bold" : ""}`}>
                    {d.t}
                    <motion.span aria-hidden className="absolute -inset-x-1 -inset-y-1 border border-ink bg-lime/30" initial={false} animate={{ opacity: on ? 1 : 0, scaleX: on ? 1 : 0.6 }}
                      style={{ originX: 0 }} transition={{ duration: 0.25 }} />
                    <span aria-hidden className="mono absolute -top-3 right-0 translate-x-full whitespace-nowrap pl-1.5 text-[8px] text-ink3" style={{ opacity: on ? 1 : 0 }}>L{String(DOC.indexOf(d) + 1).padStart(2, "0")}</span>
                  </div>
                </div>
              );
            })}
          </div>
          <div aria-hidden className="pointer-events-none absolute inset-x-0 h-px bg-ink" style={{ top: `${Math.min(p, 1) * 100}%`, opacity: p >= 1 ? 0 : 1 }}>
            <div className="absolute inset-x-0 -top-10 h-10 bg-gradient-to-t from-lime/70 to-transparent" />
            <span className="mono absolute -top-4 left-1 bg-ink px-1 text-[8px] text-lime">y {Math.round(Math.min(p, 1) * 1240)}</span>
          </div>
        </div>
        <div className="flex min-h-[200px] flex-col p-4">
          <div className="mono mb-3 flex justify-between text-ink3"><span>OUTPUT</span><span>{seen.length}/{DOC.length} LINES</span></div>
          <div className="flex-1 space-y-1.5 font-mono text-[12px]" aria-live="off">
            {seen.map((d) => (
              <motion.p key={d.t} initial={{ opacity: 0, x: -6 }} animate={{ opacity: 1, x: 0 }} className={d.k === "h" ? "font-bold" : ""}>{d.t.replace(/\.{3,}/g, " ")}</motion.p>
            ))}
            {seen.length === 0 && <p className="text-ink3">waiting for scan…</p>}
          </div>
          <p className="mono mt-3 border-t border-ink pt-2 text-[9px] leading-snug text-ink3">ILLUSTRATIVE ANIMATION. THE PRODUCT BELOW RUNS REAL ENGINES — NOT THIS DEMO.</p>
        </div>
      </div>
    </div>
  );
}

export default function Hero() {
  return (
    <section id="top" className="relative px-5 pb-16 pt-6 lg:px-10">
      <div className="mono flex flex-wrap items-center justify-between gap-3 border-b border-ink pb-3 text-ink2">
        <span>OMNISCAN® — DOCUMENT INTELLIGENCE</span>
        <StatusPill />
        <span className="hidden md:inline">N 52°31′ · E 13°24′ · ARCHIVE 001</span>
      </div>
      <div className="relative mt-8 grid items-end gap-10 lg:grid-cols-12">
        <div className="lg:col-span-8">
          <Headline as="h1" className="text-[clamp(56px,10.6vw,190px)] uppercase"
            lines={["Every mark.", "Every word.", { text: "Captured.", mark: true }]} />
        </div>
        <div className="lg:absolute lg:-bottom-2 lg:right-0 lg:col-span-5 lg:w-[42%] xl:w-[38%] lg:translate-y-8 lg:rotate-[1.2deg]">
          <ScanPlate />
        </div>
      </div>
      <div className="mt-10 grid gap-8 lg:grid-cols-12">
        <motion.div className="lg:col-span-5" initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.7, duration: 0.7 }}>
          <p className="max-w-[42ch] text-[19px] leading-snug">From handwritten chaos to perfectly structured text. One engine that shows its work: every word keeps its position, its score, and any disagreement.</p>
          <div className="mt-7 flex flex-wrap gap-3">
            <Link href="/app/new" className="btn btn-primary !h-12 px-5 text-[12.5px]">Start extracting <ArrowRight size={15} /></Link>
            <a href="#engine" className="btn !h-12 px-5 text-[12.5px]">Explore the engine</a>
          </div>
        </motion.div>
      </div>
      <dl className="mono mt-14 grid grid-cols-2 border-y border-ink text-ink md:grid-cols-4">
        {[["15", "LANGUAGES ADDRESSED"], ["6", "PIPELINE STAGES"], ["0.018", "MEAN CER · 18 SYNTHETIC FIXTURES*"], ["0", "WORDS SILENTLY INVENTED"]].map(([n, l], i) => (
          <div key={l} className={`px-4 py-4 ${i ? "md:border-l md:border-ink" : ""} ${i % 2 ? "border-l border-ink md:border-l" : ""} ${i > 1 ? "border-t border-ink md:border-t-0" : ""}`}>
            <dt className="display text-[44px] normal-case">{n}</dt><dd className="mt-1 text-[9.5px] text-ink2">{l}</dd>
          </div>
        ))}
      </dl>
      <p className="mono mt-2 text-[9.5px] text-ink3">* MEASURED ON THE BUNDLED BENCHMARK (FONT-RENDERED TEXT, NOT REAL-WORLD SCANS). REAL DOCUMENTS WILL SCORE LOWER. NO OCR IS 100% ACCURATE.</p>
    </section>
  );
}
