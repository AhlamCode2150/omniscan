const W = [
  ["Every word", "en", "ltr"], ["كل كلمة", "ar", "rtl"], ["ہر لفظ", "ur", "rtl"], ["हर शब्द", "hi", "ltr"], ["すべての言葉", "ja", "ltr"],
  ["每一个字", "zh", "ltr"], ["모든 단어", "ko", "ltr"], ["Каждое слово", "ru", "ltr"], ["Jedes Wort", "de", "ltr"], ["Chaque mot", "fr", "ltr"],
] as const;
const font: Record<string, string> = { ar: "var(--font-ar)", ur: "var(--font-ur)", hi: "var(--font-hi)", ja: "var(--font-ja)", zh: "var(--font-ja)", ko: "var(--font-ja)" };

export default function Marquee() {
  const row = W.map(([t, l, d]) => (
    <span key={t} className="mx-8 inline-flex items-baseline gap-3 whitespace-nowrap">
      <span dir={d} lang={l} className="text-[clamp(34px,5vw,72px)] leading-[1.3]" style={{ fontFamily: font[l] || "var(--font-display)" }}>{t}</span>
      <span className="mono text-[9px] text-ink3">{l}</span><span className="text-lime">■</span>
    </span>
  ));
  return (
    <div className="overflow-hidden border-y border-ink bg-surface py-3" aria-label="The phrase 'every word' in ten languages">
      <div className="marquee flex w-max" aria-hidden>{row}{row}</div>
    </div>
  );
}
