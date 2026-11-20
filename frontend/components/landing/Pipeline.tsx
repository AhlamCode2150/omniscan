"use client";
import { useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { Headline, SectionTag } from "@/components/ui";

const STEPS = [
  { n: "01", t: "Image input", d: "PNG · JPEG · WebP · TIFF · PDF", more: "Magic-byte validation, size and pixel limits, EXIF orientation. PDFs with a text layer are read natively." },
  { n: "02", t: "Enhancement", d: "Deskew · perspective · shadows", more: "Contrast, denoise, upscale, sharpen — on a copy. The original is never modified and boxes map back onto it." },
  { n: "03", t: "Detection", d: "Regions · columns · tables", more: "Orientation trial, script detection, reading order across columns, ruled-table grids." },
  { n: "04", t: "Recognition", d: "PP-OCRv5 · Tesseract · VLM", more: "Engines are pluggable. Printed text uses PaddleOCR models; handwriting and math use a vision-language model." },
  { n: "05", t: "Verification", d: "Cross-check · flags", more: "Word alignment between engines. Conflicts, number mismatches, repeats and illegible marks are flagged, never auto-corrected." },
  { n: "06", t: "Structured output", d: "TXT · MD · DOCX · JSON", more: "Raw, cleaned and edited text are kept separate; every cleaning change is logged." },
];

export default function Pipeline() {
  const [a, setA] = useState(3);
  const reduce = useReducedMotion();
  return (
    <section id="pipeline" className="relative overflow-hidden bg-ink px-5 py-24 text-paper lg:px-10 lg:py-32">
      <SectionTag n={5} label="THE TECHNOLOGY" dark />
      <Headline className="mt-8 text-[clamp(44px,8.6vw,150px)] uppercase" lines={["Not just OCR.", { text: "Document intelligence.", mark: true }]} />

      <div className="relative mt-16">
        <div className="absolute left-0 right-0 top-[22px] hidden h-px bg-paper/30 lg:block" />
        {!reduce && <motion.span aria-hidden className="absolute top-[18px] hidden h-2 w-2 bg-lime lg:block" animate={{ left: ["0%", "100%"] }} transition={{ duration: 7, repeat: Infinity, ease: "linear" }} />}
        <ol className="grid gap-px bg-paper/20 lg:grid-cols-6 lg:gap-0 lg:bg-transparent">
          {STEPS.map((s, i) => (
            <li key={s.n} className="bg-ink lg:pr-4">
              <button onClick={() => setA(i)} onMouseEnter={() => setA(i)} onFocus={() => setA(i)} aria-pressed={a === i} className="group block w-full text-left">
                <span className={`mono relative z-10 grid h-11 w-11 place-items-center border transition-colors ${a === i ? "border-lime bg-lime text-ink" : "border-paper/40 bg-ink text-paper"}`}>{s.n}</span>
                <span className="display mt-5 block text-[clamp(26px,2.4vw,40px)] uppercase leading-[.95]">{s.t}</span>
                <span className="mono mt-2 block text-[9.5px] text-paper/55">{s.d}</span>
              </button>
            </li>
          ))}
        </ol>
        <motion.p key={a} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} className="mt-10 max-w-[64ch] border-l-2 border-lime pl-4 text-[17px] text-paper/80">
          <span className="mono mb-1 block text-lime">STAGE {STEPS[a].n} — {STEPS[a].t.toUpperCase()}</span>{STEPS[a].more}
        </motion.p>
      </div>

      <div className="mt-20 grid gap-px border border-paper/25 bg-paper/25 md:grid-cols-3">
        {[["Original preserved", "Enhancement runs on a copy. Click any word and the box lands on your untouched image."],
          ["Raw ≠ cleaned ≠ edited", "Three versions, kept apart. Cleaning is rule-based and logged. No language model rewrites your text."],
          ["Confidence, or nothing", "Scores are shown only when a model provides one. Models that don’t, say so. No score is ever invented."]].map(([h, p]) => (
          <div key={h} className="bg-ink p-6"><h3 className="display text-[30px] uppercase">{h}</h3><p className="mt-3 text-[14.5px] text-paper/65">{p}</p></div>
        ))}
      </div>
    </section>
  );
}
