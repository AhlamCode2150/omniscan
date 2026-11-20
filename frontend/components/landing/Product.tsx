"use client";
import { useState } from "react";
import Link from "next/link";
import { ArrowRight, Copy, Download, Pencil, Check } from "lucide-react";
import Viewer, { type Selection } from "@/components/Viewer";
import { Banners, ExtractedPane } from "@/components/Panes";
import { Headline, SectionTag, FadeIn } from "@/components/ui";
import sample from "@/lib/sample.json";
import type { Page } from "@/lib/types";

const page = sample as unknown as Page;

export default function Product() {
  const [sel, setSel] = useState<Selection>({ kind: "word", id: page.lines[1]?.words[1]?.id ?? "" });
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState(page.raw_text);
  const [copied, setCopied] = useState(false);
  const [regions, setRegions] = useState(true);
  const download = () => {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([text], { type: "text/plain" }));
    a.download = "sample.txt"; a.click(); URL.revokeObjectURL(a.href);
  };
  return (
    <section id="product" className="border-t border-ink px-5 py-24 lg:px-10 lg:py-32">
      <SectionTag n={6} label="THE PRODUCT" />
      <div className="mt-8 grid items-end gap-6 lg:grid-cols-12">
        <Headline className="text-[clamp(44px,8vw,140px)] uppercase lg:col-span-8" lines={["Meet the", { text: "instrument.", mark: true }]} />
        <FadeIn className="lg:col-span-4"><p className="text-[15px] text-ink2">This is the real workspace, running on a sample result from an actual run. Click any word to find it on the page. Edit it. Download it.</p></FadeIn>
      </div>
      <FadeIn className="mt-12">
        <div className="border border-ink bg-surface shadow-[10px_10px_0_var(--ink)]">
          <div className="mono flex flex-wrap items-center gap-3 border-b border-ink bg-ink px-4 py-2 text-paper">
            <span>OMNISCAN / WORKSPACE</span><span className="text-paper/50">en_perspective_photo.png</span>
            <span className="ml-auto text-lime">{page.stats.words} WORDS · {Math.round((page.stats.mean_conf ?? 0) * 100)}% MEAN SCORE · CROSS-CHECKED</span>
          </div>
          <div className="grid lg:grid-cols-2">
            <div className="h-[420px] border-b border-ink p-3 lg:h-[520px] lg:border-b-0 lg:border-r">
              <Viewer src="/sample/page.jpg" page={page} selection={sel} showRegions={regions} cropMode={false} crop={null} onCrop={() => {}} onSelectWord={(id) => setSel({ kind: "word", id })} />
            </div>
            <div className="flex h-[560px] flex-col gap-3 p-4 lg:h-[520px]">
              <div className="flex flex-wrap items-center gap-2">
                <button className="btn !h-8" onClick={() => { setEditing(!editing); }}><Pencil size={13} />{editing ? "Done" : "Edit text"}</button>
                <button className="btn !h-8" onClick={async () => { try { await navigator.clipboard.writeText(text); setCopied(true); setTimeout(() => setCopied(false), 1400); } catch {} }}>
                  {copied ? <Check size={13} /> : <Copy size={13} />}{copied ? "Copied" : "Copy all"}</button>
                <button className="btn !h-8" onClick={download}><Download size={13} />.txt</button>
                <label className="mono ml-auto flex items-center gap-1.5 text-ink2"><input type="checkbox" checked={regions} onChange={(e) => setRegions(e.target.checked)} />Regions</label>
              </div>
              <Banners page={page} />
              <div className="min-h-0 flex-1">
                <ExtractedPane page={page} selection={sel} onSelect={(id) => setSel({ kind: "word", id })} q="" editing={editing} text={text} onText={setText} rtl={false} onApplyAlt={() => {}} />
              </div>
            </div>
          </div>
        </div>
        <div className="mt-8 flex flex-wrap items-center gap-4"><Link href="/app/new" className="btn btn-primary !h-12 px-5">Open the real workspace <ArrowRight size={15} /></Link>
          <span className="mono text-[9.5px] text-ink3">SAMPLE FROM THE BUNDLED PERSPECTIVE-PHOTO FIXTURE. HANDWRITING, MATH AND BATCH ARE AVAILABLE IN THE APP.</span></div>
      </FadeIn>
    </section>
  );
}
