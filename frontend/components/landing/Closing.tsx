"use client";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { Headline, SectionTag, Wordmark } from "@/components/ui";

export default function Closing() {
  return (
    <>
      <section id="start" className="relative overflow-hidden bg-lime px-5 pb-0 pt-24 lg:px-10 lg:pt-32">
        <SectionTag n={7} label="BEGIN" />
        <Headline className="mt-8 text-[clamp(48px,10.4vw,190px)] uppercase" lines={["Your images have", { text: "something to say.", italic: true }]} />
        <div className="mt-12 flex flex-wrap items-center gap-5">
          <Link href="/app/new" className="btn btn-dark !h-14 px-7 text-[13px]">Start extracting <ArrowRight size={16} /></Link>
          <span className="mono max-w-[38ch] text-[10px] text-ink/70">RUNS ON YOUR MACHINE. FILES STAY LOCAL AND ARE DELETED AUTOMATICALLY.</span>
        </div>
        <div aria-hidden className="display mt-16 select-none whitespace-nowrap text-center text-[clamp(90px,24vw,430px)] uppercase leading-[.72] text-transparent [-webkit-text-stroke:2px_var(--ink)]">OMNISCAN</div>
      </section>
      <footer className="bg-ink px-5 py-10 text-paper lg:px-10">
        <div className="grid gap-8 md:grid-cols-4">
          <div className="text-paper"><Wordmark /><p className="mono mt-4 text-[9.5px] text-paper/50">DOCUMENT INTELLIGENCE.<br />NO OCR IS 100% ACCURATE — OMNISCAN SHOWS ITS DOUBT.</p></div>
          {[["Product", [["Workspace", "/app"], ["New extraction", "/app/new"], ["Batch", "/app/batch"], ["History", "/app/history"]]],
            ["Engine", [["Capabilities", "#engine"], ["Pipeline", "#pipeline"], ["Settings", "/app/settings"]]],
            ["Principles", [["Original preserved", "#pipeline"], ["Raw ≠ cleaned", "#pipeline"], ["Confidence or nothing", "#pipeline"]]]].map(([h, ls]) => (
            <div key={h as string}><p className="mono mb-3 text-lime">{h as string}</p><ul className="space-y-1.5 text-[14px] text-paper/75">{(ls as string[][]).map(([l, href]) => <li key={l}><Link className="hover:text-lime" href={href}>{l}</Link></li>)}</ul></div>
          ))}
        </div>
      </footer>
    </>
  );
}
