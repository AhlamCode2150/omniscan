import Nav from "@/components/landing/Nav";
import Hero from "@/components/landing/Hero";
import Problem from "@/components/landing/Problem";
import Transform from "@/components/landing/Transform";
import Marquee from "@/components/landing/Marquee";
import Capabilities from "@/components/landing/Capabilities";
import Pipeline from "@/components/landing/Pipeline";
import Product from "@/components/landing/Product";
import Closing from "@/components/landing/Closing";
import { Cursor } from "@/components/ui";

export default function Landing() {
  return (
    <>
      <a href="#problem" className="sr-only focus:not-sr-only focus:absolute focus:z-[200] focus:bg-lime focus:p-2">Skip to content</a>
      <Cursor />
      <Nav />
      <main>
        <Hero />
        <Problem />
        <Transform />
        <Marquee />
        <Capabilities />
        <Pipeline />
        <Product />
      </main>
      <Closing />
    </>
  );
}
