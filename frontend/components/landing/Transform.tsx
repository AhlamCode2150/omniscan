"use client";
import { useRef, useState } from "react";
import { Headline, SectionTag, FadeIn } from "@/components/ui";

const Box = ({ children, k }: { children: React.ReactNode; k?: string }) => (
  <span className="relative mx-[1px] inline-block outline outline-1 outline-ink/70 bg-lime/35">
    {children}{k && <span className="mono absolute -top-2.5 left-0 bg-ink px-1 text-[7px] leading-3 text-lime">{k}</span>}
  </span>
);

function Original() {
  return (
    <div className="absolute inset-0 overflow-hidden bg-[#cfc8b4]">
      <div className="absolute inset-[6%] origin-center rotate-[-2.6deg] bg-[#ded8c4] px-[7%] py-[6%] font-serif text-[clamp(9px,1.35vw,15px)] leading-[1.6] text-ink/85 shadow-[0_0_60px_rgba(60,40,10,.35)] [filter:contrast(.95)_blur(.25px)]"
        style={{ backgroundImage: "radial-gradient(circle at 82% 78%, rgba(120,80,30,.22) 0 9%, transparent 10%), radial-gradient(circle at 12% 12%, rgba(0,0,0,.12), transparent 40%)" }}>
        <p className="text-[1.5em] font-bold tracking-wide"><Box k="H1">QUARTERLY SUPPLY REPORT</Box></p>
        <p className="mt-2"><Box k="P">Deliveries rose in the third quarter, though two shipments from the northern depot arrived late and were logged separately.</Box></p>
        <div className="mt-3 grid grid-cols-3 gap-x-4 border border-ink/50 p-2 font-mono"><b>Item</b><b>Qty</b><b>Price</b><span>Paper</span><span>12</span><span>3.40</span><span>Ink</span><span>5</span><span>12.00</span><span>Tape</span><span>8</span><span>1.60</span></div>
        <p className="mt-3"><Box k="LIST">• Reorder paper by 30 June</Box></p><p><Box k="LIST">• Audit the northern depot</Box></p>
        <p className="mt-3 text-center text-[1.2em]"><Box k="MATH">E = mc²</Box></p>
      </div>
      <span className="mono absolute left-3 top-3 bg-ink px-1.5 py-0.5 text-[9px] text-paper">IMG_2041.JPG · 3024×4032</span>
    </div>
  );
}

function Structured() {
  return (
    <div className="absolute inset-0 overflow-hidden bg-surface px-[6%] py-[5%] text-[clamp(10px,1.3vw,15px)] text-ink">
      <span className="mono absolute right-3 top-3 bg-lime px-1.5 py-0.5 text-[9px]">STRUCTURED · EDITABLE</span>
      <p className="mono text-[9px] text-ink3">HEADING · LEVEL 1</p><h3 className="display text-[2.6em] uppercase">Quarterly Supply Report</h3>
      <p className="mono mt-3 text-[9px] text-ink3">PARAGRAPH</p><p className="max-w-[60ch] leading-snug">Deliveries rose in the third quarter, though two shipments from the northern depot arrived late and were logged separately.</p>
      <p className="mono mt-3 text-[9px] text-ink3">TABLE · 3 × 4</p>
      <table className="w-full max-w-[420px] border-collapse font-mono text-[0.9em]"><tbody>{[["Item", "Qty", "Price"], ["Paper", "12", "3.40"], ["Ink", "5", "12.00"], ["Tape", "8", "1.60"]].map((r, i) => <tr key={i}>{r.map((c, j) => <td key={j} className={`border border-ink px-2 py-0.5 ${i === 0 ? "bg-lime font-bold" : ""}`}>{c}</td>)}</tr>)}</tbody></table>
      <p className="mono mt-3 text-[9px] text-ink3">LIST · BULLETED</p><ul className="list-disc pl-5"><li>Reorder paper by 30 June</li><li>Audit the northern depot</li></ul>
      <p className="mono mt-3 text-[9px] text-ink3">MATH · LATEX (VISION MODEL)</p><p className="font-mono text-[0.95em]">$$E = mc^2$$</p>
    </div>
  );
}

export default function Transform() {
  const [x, setX] = useState(52);
  const ref = useRef<HTMLDivElement>(null);
  const set = (clientX: number) => { const r = ref.current!.getBoundingClientRect(); setX(Math.max(4, Math.min(96, ((clientX - r.left) / r.width) * 100))); };
  return (
    <section id="transform" className="px-5 py-24 lg:px-10 lg:py-32">
      <SectionTag n={3} label="THE TRANSFORMATION" />
      <div className="mt-8 grid items-end gap-6 lg:grid-cols-12">
        <Headline className="text-[clamp(44px,8.6vw,150px)] uppercase lg:col-span-9" lines={["From image", { text: "to intelligence.", italic: true }]} />
        <FadeIn className="lg:col-span-3"><p className="text-[15px] text-ink2">Drag the line. Left: a skewed, stained, shadowed photograph. Right: the same page as structure you can edit. <span className="mono text-[9.5px]">(Illustration of the output format.)</span></p></FadeIn>
      </div>
      <FadeIn className="mt-12">
        <div ref={ref} className="reg relative aspect-[4/3] w-full touch-none select-none overflow-hidden border border-ink md:aspect-[16/8.5]"
          onPointerDown={(e) => { (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId); set(e.clientX); }} onPointerMove={(e) => e.buttons && set(e.clientX)}>
          <Structured />
          <div className="absolute inset-0" style={{ clipPath: `inset(0 ${100 - x}% 0 0)` }}><Original /></div>
          <div className="pointer-events-none absolute inset-y-0 w-px bg-ink" style={{ left: `${x}%` }}>
            <span className="mono absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 whitespace-nowrap border border-ink bg-lime px-2 py-1 text-[10px] shadow-[3px_3px_0_var(--ink)]">◀ DRAG ▶</span>
          </div>
          <input type="range" min={4} max={96} value={x} onChange={(e) => setX(+e.target.value)} aria-label="Compare original image and structured text"
            className="absolute inset-0 h-full w-full cursor-ew-resize opacity-0" />
        </div>
        <div className="mono mt-2 flex justify-between text-ink3"><span>A — ORIGINAL IMAGE</span><span>B — STRUCTURED OUTPUT</span></div>
      </FadeIn>
    </section>
  );
}
