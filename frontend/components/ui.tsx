"use client";
import { useEffect, useRef, useState } from "react";
import { motion, useInView, useReducedMotion, useMotionValue, useSpring } from "framer-motion";
import Link from "next/link";
import { api } from "@/lib/api";
import type { Config } from "@/lib/types";

export function Glyph({ size = 22 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M2 8V2h6M16 2h6v6M22 16v6h-6M8 22H2v-6" stroke="currentColor" strokeWidth="2" />
      <rect x="8" y="8" width="8" height="8" fill="var(--lime)" stroke="currentColor" strokeWidth="1.4" />
    </svg>
  );
}

export function Wordmark({ href = "/", className = "" }: { href?: string; className?: string }) {
  return (
    <Link href={href} aria-label="Omniscan home" className={`inline-flex items-center gap-2.5 ${className}`}>
      <Glyph />
      <span className="flex items-baseline leading-none">
        <span className="text-[17px] font-semibold tracking-[-0.03em]">OMNI</span>
        <span className="font-display text-[22px] italic tracking-[-0.02em]">scan</span>
      </span>
    </Link>
  );
}

/** Masked line-by-line headline reveal. Each string in `lines` is one line; use <mark> via {mark:true} objects. */
export type Line = string | { text: string; mark?: boolean; italic?: boolean };
export function Headline({ lines, className = "", delay = 0, as: Tag = "h2" }: { lines: Line[]; className?: string; delay?: number; as?: "h1" | "h2" | "h3" }) {
  const ref = useRef<HTMLElement>(null);
  const inView = useInView(ref, { once: true, margin: "-12% 0px" });
  const reduce = useReducedMotion();
  const M: any = motion[Tag];
  return (
    <M ref={ref} className={`display ${className}`}>
      {lines.map((l, i) => {
        const o = typeof l === "string" ? { text: l } : l;
        return (
          <span key={i} className="block overflow-hidden pb-[0.08em] -mb-[0.08em]">
            <motion.span className="block" initial={reduce ? false : { y: "105%" }} animate={inView || reduce ? { y: 0 } : undefined}
              transition={{ duration: 0.9, delay: delay + i * 0.09, ease: [0.16, 1, 0.3, 1] }}>
              <span className={`${o.mark ? "mark" : ""} ${o.italic ? "italic" : ""}`}>{o.text}</span>
            </motion.span>
          </span>
        );
      })}
    </M>
  );
}

export function FadeIn({ children, delay = 0, y = 18, className = "" }: { children: React.ReactNode; delay?: number; y?: number; className?: string }) {
  const reduce = useReducedMotion();
  return (
    <motion.div className={className} initial={reduce ? false : { opacity: 0, y }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, margin: "-8% 0px" }}
      transition={{ duration: 0.7, delay, ease: [0.16, 1, 0.3, 1] }}>{children}</motion.div>
  );
}

export function SectionTag({ n, total = 7, label, dark = false }: { n: number; total?: number; label: string; dark?: boolean }) {
  return (
    <div className={`mono flex items-center gap-3 ${dark ? "text-paper/70" : "text-ink2"}`}>
      <span className={`px-1.5 py-0.5 ${dark ? "bg-lime text-ink" : "bg-ink text-paper"}`}>{String(n).padStart(2, "0")}</span>
      <span>/ {String(total).padStart(2, "0")}</span>
      <span className="h-px w-10 bg-current" />
      <span>{label}</span>
    </div>
  );
}

/** Crosshair cursor with live page coordinates (fine pointers only, never on touch). */
export function Cursor() {
  const x = useMotionValue(-100), y = useMotionValue(-100);
  const sx = useSpring(x, { stiffness: 700, damping: 40 }), sy = useSpring(y, { stiffness: 700, damping: 40 });
  const [on, setOn] = useState(false);
  const [hot, setHot] = useState(false);
  const [pos, setPos] = useState<[number, number]>([0, 0]);
  const reduce = useReducedMotion();
  useEffect(() => {
    if (reduce || !window.matchMedia("(pointer: fine)").matches) return;
    document.documentElement.classList.add("has-cursor");
    setOn(true);
    const mv = (e: PointerEvent) => {
      x.set(e.clientX); y.set(e.clientY); setPos([Math.round(e.pageX), Math.round(e.pageY)]);
      setHot(!!(e.target as HTMLElement)?.closest("a,button,[role=button],input,select,textarea,summary"));
    };
    window.addEventListener("pointermove", mv);
    return () => { window.removeEventListener("pointermove", mv); document.documentElement.classList.remove("has-cursor"); };
  }, [reduce, x, y]);
  if (!on) return null;
  return (
    <motion.div aria-hidden className="pointer-events-none fixed left-0 top-0 z-[100] mix-blend-difference" style={{ x: sx, y: sy }}>
      <div className={`absolute -left-3 -top-3 h-6 w-6 transition-transform duration-150 ${hot ? "scale-150" : ""}`}>
        <span className="absolute left-1/2 top-0 h-full w-px -translate-x-1/2 bg-white" /><span className="absolute left-0 top-1/2 h-px w-full -translate-y-1/2 bg-white" />
        {hot && <span className="absolute inset-1 border border-white" />}
      </div>
      <span className="mono absolute left-4 top-3 whitespace-nowrap text-[9px] text-white">x{pos[0]} y{pos[1]}</span>
    </motion.div>
  );
}

export function useEngineStatus() {
  const [cfg, setCfg] = useState<Config | null>(null);
  const [down, setDown] = useState(false);
  useEffect(() => { api.config().then(setCfg).catch(() => setDown(true)); }, []);
  return { cfg, down };
}

/** Honest live indicator: reflects the real /api/config result. */
export function StatusPill({ className = "" }: { className?: string }) {
  const { cfg, down } = useEngineStatus();
  const up = cfg?.engines.filter((e) => e.available).length ?? 0;
  const label = down ? "ENGINE OFFLINE" : cfg ? `ENGINE ONLINE · ${up}/${cfg.engines.length} MODELS` : "CONNECTING…";
  return (
    <span className={`mono inline-flex items-center gap-2 ${className}`} role="status">
      <span className={`h-2 w-2 ${down ? "bg-bad" : cfg ? "bg-lime live outline outline-1 outline-ink" : "bg-ink3"}`} />{label}
    </span>
  );
}
