import type { Metadata, Viewport } from "next";
import { Instrument_Serif, Geist, Geist_Mono, Caveat, Noto_Naskh_Arabic, Noto_Sans_Devanagari, Noto_Sans_JP, Noto_Nastaliq_Urdu } from "next/font/google";
import "./globals.css";

const display = Instrument_Serif({ subsets: ["latin"], weight: "400", style: ["normal", "italic"], variable: "--font-display" });
const sans = Geist({ subsets: ["latin"], variable: "--font-sans" });
const mono = Geist_Mono({ subsets: ["latin"], variable: "--font-mono" });
const hand = Caveat({ subsets: ["latin"], variable: "--font-hand" });
const naskh = Noto_Naskh_Arabic({ subsets: ["arabic"], variable: "--font-ar", preload: false });
const urdu = Noto_Nastaliq_Urdu({ subsets: ["arabic"], variable: "--font-ur", preload: false });
const deva = Noto_Sans_Devanagari({ subsets: ["devanagari"], variable: "--font-hi", preload: false });
const jp = Noto_Sans_JP({ subsets: ["latin"], weight: ["400", "700"], variable: "--font-ja", preload: false });

export const metadata: Metadata = {
  title: "Omniscan — every mark, every word",
  description: "Document intelligence: printed and handwritten text from images and PDFs, with confidence, alignment and cross-engine verification.",
};
export const viewport: Viewport = { width: "device-width", initialScale: 1, themeColor: "#f0ece0" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const v = [display, sans, mono, hand, naskh, urdu, deva, jp].map((f) => f.variable).join(" ");
  return (
    <html lang="en" className={v}>
      <body>{children}</body>
    </html>
  );
}
