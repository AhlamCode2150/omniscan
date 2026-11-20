"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutGrid, FilePlus2, History, Layers, SlidersHorizontal } from "lucide-react";
import { StatusPill, Wordmark } from "@/components/ui";
import { ToastProvider } from "@/components/toast";

const NAV = [
  { href: "/app", label: "Overview", icon: LayoutGrid, exact: true },
  { href: "/app/new", label: "New extraction", icon: FilePlus2 },
  { href: "/app/history", label: "History", icon: History },
  { href: "/app/batch", label: "Batch", icon: Layers },
  { href: "/app/settings", label: "Settings", icon: SlidersHorizontal },
];

export default function AppShell({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  const is = (n: (typeof NAV)[number]) => (n.exact ? path === n.href : path.startsWith(n.href)) || (n.href === "/app/history" && path.startsWith("/scan"));
  return (
    <ToastProvider>
      <div className="min-h-dvh lg:grid lg:grid-cols-[232px_1fr]">
        <aside className="hidden border-r border-ink bg-surface lg:flex lg:h-dvh lg:flex-col lg:sticky lg:top-0">
          <div className="border-b border-ink px-5 py-4"><Wordmark /></div>
          <nav className="flex-1 py-3" aria-label="Application">
            <p className="eyebrow px-5 pb-2">Workspace</p>
            {NAV.map((n) => (
              <Link key={n.href} href={n.href} aria-current={is(n) ? "page" : undefined}
                className={`mono group flex items-center gap-3 border-l-[3px] px-5 py-2.5 transition-colors ${is(n) ? "border-ink bg-lime" : "border-transparent hover:bg-sunken"}`}>
                <n.icon size={15} strokeWidth={1.8} />{n.label}
              </Link>
            ))}
          </nav>
          <div className="space-y-2 border-t border-ink p-5">
            <StatusPill className="text-[9.5px]" />
            <p className="mono text-[9px] leading-snug text-ink3">LOCAL-FIRST. FILES STAY ON THIS MACHINE.</p>
            <Link href="/" className="mono text-[9.5px] text-ink2 underline underline-offset-4 hover:text-cobalt">← Back to site</Link>
          </div>
        </aside>
        <div className="min-w-0 pb-16 lg:pb-0">
          <header className="sticky top-0 z-30 flex h-12 items-center justify-between border-b border-ink bg-paper px-4 lg:hidden"><Wordmark /><StatusPill className="text-[9px]" /></header>
          {children}
        </div>
        <nav className="fixed inset-x-0 bottom-0 z-40 grid grid-cols-5 border-t border-ink bg-surface lg:hidden" aria-label="Application">
          {NAV.map((n) => (
            <Link key={n.href} href={n.href} aria-current={is(n) ? "page" : undefined} className={`mono flex flex-col items-center gap-0.5 py-2 text-[8.5px] ${is(n) ? "bg-lime" : ""}`}>
              <n.icon size={16} strokeWidth={1.8} />{n.label.split(" ")[0]}</Link>))}
        </nav>
      </div>
    </ToastProvider>
  );
}
