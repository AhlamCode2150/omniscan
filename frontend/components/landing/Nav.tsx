"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowRight, Plus, X } from "lucide-react";
import { Wordmark } from "@/components/ui";

const LINKS = [["Engine", "engine", "04"], ["Pipeline", "pipeline", "05"], ["Product", "product", "06"], ["Begin", "start", "07"]] as const;

export default function Nav() {
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState("");
  const [stuck, setStuck] = useState(false);
  useEffect(() => {
    const ids = ["top", "problem", "transform", "engine", "pipeline", "product", "start"];
    const io = new IntersectionObserver((es) => es.forEach((e) => e.isIntersecting && setActive(e.target.id)), { rootMargin: "-45% 0px -50% 0px" });
    ids.forEach((i) => { const el = document.getElementById(i); if (el) io.observe(el); });
    const sc = () => setStuck(window.scrollY > 40);
    window.addEventListener("scroll", sc, { passive: true }); sc();
    return () => { io.disconnect(); window.removeEventListener("scroll", sc); };
  }, []);
  return (
    <>
      <header className={`sticky top-0 z-50 border-b border-ink transition-colors ${stuck ? "bg-paper/95 backdrop-blur" : "bg-paper"}`}>
        <div className="flex h-14 items-center gap-6 px-5 lg:px-10">
          <Wordmark />
          <nav className="mono ml-8 hidden items-center gap-6 md:flex" aria-label="Sections">
            {LINKS.map(([l, id]) => <a key={id} href={`#${id}`} className={`transition-colors hover:text-cobalt ${active === id ? "text-cobalt" : ""}`}>[{l}]</a>)}
          </nav>
          <div className="ml-auto flex items-center gap-2">
            <Link href="/app/new" className="btn btn-primary !h-9 hidden sm:inline-flex">Start extracting <ArrowRight size={13} /></Link>
            <button className="btn !h-9 md:hidden" onClick={() => setOpen(true)} aria-label="Open menu">Menu <Plus size={13} /></button>
          </div>
        </div>
      </header>
      <AnimatePresence>
        {open && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 z-[60] flex flex-col bg-ink p-5 text-paper">
            <div className="flex justify-between"><span className="mono">MENU</span><button onClick={() => setOpen(false)} aria-label="Close menu"><X /></button></div>
            <ul className="mt-10 space-y-2">{[["Engine", "engine"], ["Pipeline", "pipeline"], ["Product", "product"], ["Begin", "start"]].map(([l, id], i) => (
              <li key={id}><a href={`#${id}`} onClick={() => setOpen(false)} className="display flex items-baseline gap-3 text-[56px] uppercase"><span className="mono text-[11px] text-lime">0{i + 4}</span>{l}</a></li>))}</ul>
            <Link href="/app/new" className="btn btn-primary mt-auto !h-12 !text-ink">Start extracting <ArrowRight size={14} /></Link>
          </motion.div>
        )}
      </AnimatePresence>
      <aside aria-hidden className="fixed right-3 top-1/2 z-40 hidden -translate-y-1/2 flex-col items-center gap-2.5 min-[1700px]:flex">
        {["top", "problem", "transform", "engine", "pipeline", "product", "start"].map((id, i) => (
          <a key={id} href={`#${id}`} tabIndex={-1} className={`mono flex items-center gap-1.5 text-[9px] ${active === id ? "text-ink" : "text-ink3"}`}>
            <span className={`h-px transition-all ${active === id ? "w-6 bg-ink" : "w-2 bg-ink3"}`} />{String(i + 1).padStart(2, "0")}</a>))}
      </aside>
    </>
  );
}
