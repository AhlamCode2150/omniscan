import Upload from "@/components/Upload";
import { PageHead } from "@/components/PageHead";

export default function Batch() {
  return (
    <main className="mx-auto max-w-[1100px] px-5 pb-16 pt-8 lg:px-10">
      <PageHead n="04" kicker="Batch processing" title="A whole stack, one pass." />
      <Upload batch />
    </main>
  );
}
