"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Config } from "@/lib/types";
import { PageHead } from "@/components/PageHead";

const HOWTO: Record<string, string> = {
  rapidocr: "Bundled. Models download on first use into OMNISCAN_MODEL_DIR.",
  tesseract: "Install Tesseract 5, then run  python scripts/fetch_models.py  for language packs. Override the path with TESSERACT_CMD.",
  "ollama-vlm": "Install Ollama, then  ollama pull qwen2.5vl:3b . Change the model with OMNISCAN_VLM_MODEL.",
  "anthropic-vlm": "Set ANTHROPIC_API_KEY in the backend environment. The key never reaches the browser. Images are sent to the Anthropic API.",
};

export default function Settings() {
  const [cfg, setCfg] = useState<Config | null>(null);
  useEffect(() => { api.config().then(setCfg).catch(() => {}); }, []);
  return (
    <main className="mx-auto max-w-[1100px] px-5 pb-16 pt-8 lg:px-10">
      <PageHead n="05" kicker="Settings" title="What is actually running." />
      {!cfg ? <p className="text-ink2">Loading…</p> : (<>
        <p className="mb-6 max-w-[60ch] text-ink2">Engines are pluggable. Omniscan only claims a language for an engine when that engine can really read it on this machine.</p>
        <div className="grid gap-px border border-ink bg-ink md:grid-cols-2">
          {cfg.engines.map((e) => (
            <div key={e.name} className="bg-surface p-5">
              <div className="flex items-start justify-between gap-3">
                <div><p className="font-medium">{e.label}</p><p className="mono text-ink3">{e.name} · {e.kind}</p></div>
                <span className={`chip ${e.available ? "border-good text-good" : "border-warn text-warn"}`}>{e.available ? "Available" : "Unavailable"}</span>
              </div>
              {!e.available && <p className="mt-3 text-[13px] text-warn">{e.reason}</p>}
              <p className="mt-3 text-[13px] text-ink2">{HOWTO[e.name]}</p>
              {e.available && e.languages.length > 0 && <p className="mono mt-3 text-ink3">LANGS: {e.languages.join(" ")}</p>}
            </div>))}
        </div>
        <h2 className="display mt-12 text-[38px] uppercase">Language support</h2>
        <div className="mt-4 overflow-x-auto border border-ink bg-surface">
          <table className="w-full min-w-[520px] text-left text-[13px]">
            <thead className="mono border-b border-ink text-ink3"><tr>{["Language", "Script", "Direction", "PaddleOCR", "Tesseract"].map((h) => <th key={h} className="p-3 font-medium">{h}</th>)}</tr></thead>
            <tbody>{cfg.languages.map((l) => (
              <tr key={l.code} className="border-t border-line"><td className="p-3">{l.name}</td><td className="p-3 text-ink2">{l.script}</td><td className="p-3 text-ink2">{l.rtl ? "RTL" : "LTR"}</td>
                <td className="p-3">{l.rapidocr ? "■" : "—"}</td><td className="p-3">{l.tesseract ? "■" : "—"}</td></tr>))}</tbody>
          </table>
        </div>
        <h2 className="display mt-12 text-[38px] uppercase">Data & limits</h2>
        <dl className="mt-4 grid border border-ink bg-surface md:grid-cols-3">
          {[["Max upload", `${cfg.max_upload_mb} MB`], ["Max PDF pages", String(cfg.max_pdf_pages)], ["Retention", cfg.retention_hours > 0 ? `${cfg.retention_hours} h, then deleted` : "Kept until deleted"]].map(([k, v], i) => (
            <div key={k} className={`p-5 ${i ? "border-t border-ink md:border-l md:border-t-0" : ""}`}><dd className="display text-[34px]">{v}</dd><dt className="mono mt-1 text-ink3">{k}</dt></div>))}
        </dl>
        <ul className="mt-6 list-disc space-y-1 pl-5 text-[13px] text-ink2">{cfg.notes.map((n) => <li key={n}>{n}</li>)}</ul>
      </>)}
    </main>
  );
}
