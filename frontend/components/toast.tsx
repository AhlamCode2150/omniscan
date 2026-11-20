"use client";
import { createContext, useCallback, useContext, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Check, AlertTriangle, Loader2 } from "lucide-react";

type T = { id: number; msg: string; kind: "ok" | "err" | "busy" };
const Ctx = createContext<(msg: string, kind?: T["kind"], ms?: number) => void>(() => {});
export const useToast = () => useContext(Ctx);

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [ts, setTs] = useState<T[]>([]);
  const push = useCallback((msg: string, kind: T["kind"] = "ok", ms = 3200) => {
    const id = Math.random();
    setTs((t) => [...t.slice(-3), { id, msg, kind }]);
    setTimeout(() => setTs((t) => t.filter((x) => x.id !== id)), ms);
  }, []);
  return (
    <Ctx.Provider value={push}>
      {children}
      <div className="pointer-events-none fixed bottom-4 right-4 z-[90] flex flex-col items-end gap-2" role="status" aria-live="polite">
        <AnimatePresence>{ts.map((t) => (
          <motion.div key={t.id} initial={{ opacity: 0, x: 24 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, y: 8 }}
            className={`mono pointer-events-auto flex items-center gap-2 border border-ink px-3 py-2 shadow-[3px_3px_0_var(--ink)] ${t.kind === "err" ? "bg-bad text-white" : "bg-lime text-ink"}`}>
            {t.kind === "ok" ? <Check size={13} /> : t.kind === "err" ? <AlertTriangle size={13} /> : <Loader2 size={13} className="animate-spin" />}{t.msg}
          </motion.div>))}</AnimatePresence>
      </div>
    </Ctx.Provider>
  );
}
