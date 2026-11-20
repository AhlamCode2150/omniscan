"use client";
import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import type { Box, Page } from "@/lib/types";

export type Selection = { kind: "word"; id: string } | { kind: "box"; box: Box } | null;

interface Props {
  src: string; page: Page; selection: Selection; showRegions: boolean; cropMode: boolean;
  onCrop: (b: Box | null) => void; crop: Box | null; onSelectWord: (id: string) => void;
}

const colorFor = (c: number | null, flags: string[]) => {
  if (flags.includes("conflict") || flags.includes("illegible") || (c !== null && c < 0.6)) return "var(--bad)";
  if (flags.includes("review") || flags.includes("mixed-letters-digits") || (c !== null && c < 0.8)) return "var(--warn)";
  return "var(--ink-3)";
};

export default function Viewer({ src, page, selection, showRegions, cropMode, onCrop, crop, onSelectWord }: Props) {
  const wrap = useRef<HTMLDivElement>(null);
  const [fit, setFit] = useState(1);
  const [zoom, setZoom] = useState(1); // multiplier over fit
  const [rot, setRot] = useState(0); // display-only rotation, degrees clockwise
  const [loaded, setLoaded] = useState(false);
  const [drag, setDrag] = useState<{ x: number; y: number; x2: number; y2: number } | null>(null);
  const W = page.width, H = page.height;
  const swap = rot % 180 !== 0;
  const OW = swap ? H : W, OH = swap ? W : H;
  const scale = fit * zoom;

  const refit = useCallback(() => {
    if (!wrap.current) return;
    const r = wrap.current.getBoundingClientRect();
    setFit(Math.min((r.width - 24) / OW, (r.height - 24) / OH, 1.6));
  }, [OW, OH]);
  useLayoutEffect(() => { refit(); }, [refit]);
  useEffect(() => { const ro = new ResizeObserver(refit); if (wrap.current) ro.observe(wrap.current); return () => ro.disconnect(); }, [refit]);
  useEffect(() => { setLoaded(false); }, [src]);

  // scroll selection into view
  const selBox: Box | null = (() => {
    if (!selection) return null;
    if (selection.kind === "box") return selection.box;
    for (const l of page.lines) for (const w of l.words) if (w.id === selection.id) return w.box;
    return null;
  })();
  useEffect(() => {
    if (!selBox || !wrap.current) return;
    const el = wrap.current, cx = (selBox[0] + selBox[2] / 2) * scale, cy = (selBox[1] + selBox[3] / 2) * scale;
    el.scrollTo({ left: cx - el.clientWidth / 2, top: cy - el.clientHeight / 2, behavior: "smooth" });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selBox?.[0], selBox?.[1]]);

  const toImg = (e: React.PointerEvent) => {
    const r = (e.currentTarget as HTMLElement).getBoundingClientRect();
    return { x: Math.max(0, Math.min(W, (e.clientX - r.left) / scale)), y: Math.max(0, Math.min(H, (e.clientY - r.top) / scale)) };
  };
  const rect = drag ? [Math.min(drag.x, drag.x2), Math.min(drag.y, drag.y2), Math.abs(drag.x2 - drag.x), Math.abs(drag.y2 - drag.y)] : crop;
  const pts = (p: number[][]) => p.map((q) => q.join(",")).join(" ");

  return (
    <div className="relative flex h-full min-h-0 flex-col">
      <div className="absolute right-3 top-3 z-10 flex items-center gap-1  border border-line bg-surface/95 p-1 shadow-sm backdrop-blur">
        <button className="btn btn-ghost btn-icon !h-8 !w-8" aria-label="Rotate view left" title="Rotate view (display only)" onClick={() => { setRot((r) => (r + 270) % 360); onCrop(null); }}>⟲</button>
        <button className="btn btn-ghost btn-icon !h-8 !w-8" aria-label="Rotate view right" title="Rotate view (display only)" onClick={() => { setRot((r) => (r + 90) % 360); onCrop(null); }}>⟳</button>
        <button className="btn btn-ghost btn-icon !h-8 !w-8" aria-label="Zoom out" onClick={() => setZoom((z) => Math.max(0.3, z / 1.25))}>−</button>
        <button className="btn btn-ghost !h-8 px-2 text-[12px] tabular-nums" aria-label="Fit to view" onClick={() => setZoom(1)}>{Math.round(scale * 100)}%</button>
        <button className="btn btn-ghost btn-icon !h-8 !w-8" aria-label="Zoom in" onClick={() => setZoom((z) => Math.min(8, z * 1.25))}>+</button>
      </div>
      <div ref={wrap} className="scroll-thin flex min-h-0 flex-1 overflow-auto border border-ink bg-sunken p-3"
        onWheel={(e) => { if (e.ctrlKey || e.metaKey) { e.preventDefault(); setZoom((z) => Math.min(8, Math.max(0.3, z * (e.deltaY < 0 ? 1.1 : 0.9)))); } }}>
        <div className="relative m-auto shrink-0 select-none" style={{ width: OW * scale, height: OH * scale }}>
        <div className="absolute left-0 top-0 origin-top-left" style={{ width: W * scale, height: H * scale, touchAction: cropMode && rot === 0 ? "none" : "auto", transform: rot === 90 ? `translate(${H * scale}px,0) rotate(90deg)` : rot === 180 ? `translate(${W * scale}px,${H * scale}px) rotate(180deg)` : rot === 270 ? `translate(0,${W * scale}px) rotate(270deg)` : undefined }}
          onPointerDown={(e) => { if (!cropMode || rot !== 0) return; (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId); const p = toImg(e); setDrag({ x: p.x, y: p.y, x2: p.x, y2: p.y }); }}
          onPointerMove={(e) => { if (!drag) return; const p = toImg(e); setDrag({ ...drag, x2: p.x, y2: p.y }); }}
          onPointerUp={() => { if (!drag) return; const b: Box = [Math.min(drag.x, drag.x2), Math.min(drag.y, drag.y2), Math.abs(drag.x2 - drag.x), Math.abs(drag.y2 - drag.y)]; setDrag(null); onCrop(b[2] > 20 && b[3] > 20 ? b : null); }}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img ref={(el) => { if (el && el.complete && el.naturalWidth > 0 && !loaded) setLoaded(true); }} src={src} alt="Uploaded document" width={W * scale} height={H * scale} draggable={false} onLoad={() => setLoaded(true)}
            className={`block shadow-[4px_4px_0_var(--ink)] transition-opacity ${loaded ? "opacity-100" : "opacity-0"}`} />
          <svg className="absolute inset-0" viewBox={`0 0 ${W} ${H}`} width={W * scale} height={H * scale} style={{ pointerEvents: cropMode ? "none" : "auto" }}>
            {showRegions && page.lines.flatMap((l) => l.words).map((w) => w.poly && (
              <polygon key={w.id} points={pts(w.poly)} fill={selection?.kind === "word" && selection.id === w.id ? "var(--accent)" : "transparent"}
                fillOpacity={0.22} stroke={selection?.kind === "word" && selection.id === w.id ? "var(--accent)" : colorFor(w.conf, w.flags)}
                strokeWidth={(selection?.kind === "word" && selection.id === w.id ? 2.5 : 1.2) / Math.max(scale, 0.4)} strokeOpacity={w.status === "uncertain" ? 0.95 : 0.55}
                strokeDasharray={w.est_box ? `${4 / scale} ${3 / scale}` : undefined} style={{ cursor: "pointer" }} onClick={() => onSelectWord(w.id)}>
                <title>{`${w.text}${w.conf !== null ? ` · ${(w.conf * 100).toFixed(0)}%` : ""}`}</title>
              </polygon>
            ))}
            {selection?.kind === "box" && selBox && <rect x={selBox[0]} y={selBox[1]} width={selBox[2]} height={selBox[3]} fill="var(--accent)" fillOpacity={0.14} stroke="var(--accent)" strokeWidth={2.5 / Math.max(scale, 0.4)} />}
            {rect && rect[2] > 0 && <rect x={rect[0]} y={rect[1]} width={rect[2]} height={rect[3]} fill="var(--accent)" fillOpacity={0.1} stroke="var(--accent)" strokeWidth={2 / scale} strokeDasharray={`${6 / scale}`} />}
          </svg>
        </div>
        </div>
      </div>
      {cropMode && rot !== 0 && <p className="mono mt-2 text-center text-warn">Reset rotation to select an area.</p>}
      {cropMode && <p className="mt-2 text-center text-[12px] text-ink2">Drag on the image to select the area to re-scan.</p>}
    </div>
  );
}
