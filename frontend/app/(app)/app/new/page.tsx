import Upload from "@/components/Upload";
import { PageHead } from "@/components/PageHead";

export default function New() {
  return (
    <main className="mx-auto max-w-[1100px] px-5 pb-16 pt-8 lg:px-10">
      <PageHead n="02" kicker="New extraction" title="Feed the instrument." />
      <Upload />
    </main>
  );
}
