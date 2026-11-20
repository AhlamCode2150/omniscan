export function PageHead({ n, kicker, title }: { n: string; kicker: string; title: string }) {
  return (
    <div className="mb-8 border-b border-ink pb-6">
      <p className="mono flex items-center gap-3 text-ink2"><span className="bg-ink px-1.5 py-0.5 text-paper">{n}</span>{kicker}</p>
      <h1 className="display mt-4 text-[clamp(44px,6vw,92px)] uppercase">{title}</h1>
    </div>
  );
}
