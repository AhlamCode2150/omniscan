"use client";
import { useRef } from "react";
import { motion, useScroll, useTransform, useReducedMotion } from "framer-motion";
import { Lock } from "lucide-react";
import { Headline, SectionTag } from "@/components/ui";

function Tag({ children }: { children: React.ReactNode }) {
  return <span className="mono absolute -bottom-3 left-3 z-10 flex items-center gap-1 bg-lime px-1.5 py-0.5 text-[8.5px] text-ink"><Lock size={9} />{children}</span>;
}

function Artifact({ className, speed, rot, children }: { className: string; speed: number; rot: number; children: React.ReactNode }) {
  const ref = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start end", "end start"] });
  const reduce = useReducedMotion();
  const y = useTransform(scrollYProgress, [0, 1], reduce ? [0, 0] : [60 * speed, -60 * speed]);
  return <motion.div ref={ref} style={{ y, rotate: rot }} className={`absolute ${className}`}>{children}</motion.div>;
}

export default function Problem() {
  return (
    <section id="problem" className="relative overflow-hidden bg-ink px-5 py-24 text-paper lg:px-10 lg:py-32">
      <SectionTag n={2} label="THE PROBLEM" dark />
      <Headline className="mt-8 text-[clamp(44px,8.6vw,150px)] uppercase" lines={["The world is full of text.", { text: "Most of it is trapped.", mark: true }]} />
      <p className="mt-8 max-w-[46ch] text-[17px] text-paper/70">Receipts in drawers. Notebooks in bags. Screenshots nobody can search. Scans that are just pictures. Omniscan frees the words, and tells you how sure it is about each one.</p>

      <div className="relative mt-16 hidden h-[560px] lg:block">
        <Artifact className="left-[2%] top-[40px] w-[250px]" speed={1} rot={-4}>
          <div className="relative bg-[#f7f4ea] p-4 font-mono text-[11px] leading-[1.7] text-ink [clip-path:polygon(0_0,100%_0,100%_calc(100%-8px),95%_100%,90%_calc(100%-8px),85%_100%,80%_calc(100%-8px),75%_100%,70%_calc(100%-8px),65%_100%,60%_calc(100%-8px),55%_100%,50%_calc(100%-8px),45%_100%,40%_calc(100%-8px),35%_100%,30%_calc(100%-8px),25%_100%,20%_calc(100%-8px),15%_100%,10%_calc(100%-8px),5%_100%,0_calc(100%-8px))]">
            <p className="text-center font-bold">CAFÉ LUMEN</p><p className="text-center text-[9px]">14 MAR · 08:12 · #00418</p><hr className="my-2 border-dashed border-ink/40" />
            <p>2 × ESPRESSO <span className="float-right">6.40</span></p><p>1 × ALMOND CROIS. <span className="float-right">4.10</span></p><p>1 × OAT FLAT WHITE <span className="float-right">4.40</span></p>
            <hr className="my-2 border-dashed border-ink/40" /><p className="font-bold">TOTAL <span className="float-right">14.90</span></p><p className="pb-3 text-[9px]">THANK YOU · KEEP RECEIPT</p>
          </div>
          <Tag>PHOTO · NOT SEARCHABLE</Tag>
        </Artifact>
        <Artifact className="left-[26%] top-[170px] w-[330px]" speed={0.5} rot={2.5}>
          <div className="relative aspect-[4/3] border border-paper/30 bg-[#f4f1e4] p-5 text-ink" style={{ backgroundImage: "repeating-linear-gradient(transparent 0 27px, #9fb1c9 27px 28px)" }}>
            <p className="font-[family-name:var(--font-hand)] text-[26px] leading-[28px] text-[#1e3a9a]">buy oat milk &amp; pens<br />call Sam — Tuesday notes!!<br />meet 4:30, old library<br /><span className="line-through">bring red folder</span> two pens</p>
          </div>
          <Tag>HANDWRITING · PAGE 14</Tag>
        </Artifact>
        <Artifact className="right-[4%] top-[10px] w-[360px]" speed={1.3} rot={1.5}>
          <div className="relative border border-paper/30 bg-[#e9e6da] text-ink">
            <div className="mono flex items-center gap-2 border-b border-ink/30 px-3 py-1.5 text-[9px]"><span>▢</span>dashboard.png<span className="ml-auto">1920×1080</span></div>
            <div className="p-4"><p className="text-[11px] text-ink2">Q3 REVENUE</p><p className="display text-[56px] leading-none">€4.21M <span className="font-sans text-[14px] text-good">+12.4%</span></p>
              <div className="mt-3 flex h-14 items-end gap-1">{[30, 44, 38, 60, 52, 78, 70].map((h, i) => <span key={i} className="flex-1 bg-ink" style={{ height: `${h}%` }} />)}</div></div>
          </div>
          <Tag>SCREENSHOT · PIXELS ONLY</Tag>
        </Artifact>
        <Artifact className="right-[10%] top-[330px] w-[290px]" speed={0.8} rot={-2}>
          <div className="relative border border-paper/20 bg-[#d8d3c2] p-5 font-serif text-[11.5px] leading-[1.55] text-ink [filter:contrast(1.1)_grayscale(.6)]" style={{ transform: "skewX(-1.5deg)" }}>
            <p className="font-bold">DEPARTMENT OF RECORDS</p><p>Ref. 77/B — 02 February 1987</p><p className="mt-2">Dear Madam, we acknowledge receipt of your correspondence of the 19th ult. and regret the delay in our reply.</p>
            <p className="mt-2 inline-block border-2 border-[#8a2020] px-2 py-0.5 text-[10px] font-bold tracking-widest text-[#8a2020] rotate-[-6deg]">RECEIVED</p>
          </div>
          <Tag>SCAN · 1987 CARBON COPY</Tag>
        </Artifact>
        <Artifact className="left-[3%] top-[420px] w-[200px]" speed={1.1} rot={5}>
          <div className="relative bg-lime p-4 text-ink"><p className="font-[family-name:var(--font-hand)] text-[24px] leading-6">invoice 20418<br />due Friday!!</p></div>
          <Tag>STICKY · 3 WORDS</Tag>
        </Artifact>
      </div>

      <ul className="mt-14 grid gap-3 text-ink lg:hidden sm:grid-cols-2">
        {["Receipt · photo", "Notebook · handwriting", "Dashboard · screenshot", "Letter · 1987 scan"].map((t) => <li key={t} className="mono flex items-center gap-2 border border-paper/30 p-4 text-paper"><Lock size={12} />{t}</li>)}
      </ul>
    </section>
  );
}
