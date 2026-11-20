"""Benchmark suite: runs the real pipeline over fixtures/*.{png,jpg,pdf} and compares with the sibling .txt ground truth.

Metrics: CER and WER (jiwer) on whitespace-normalised, Unicode-NFC text. Nothing here is hard-coded: numbers are whatever
the engines produce on this machine. Results are written to benchmarks/results/<timestamp>.{json,md}.

    python benchmarks/run_benchmark.py [--mode printed|handwriting|academic|auto] [--only substr] [--lang xx]
"""
import argparse
import json
import re
import sys
import time
import unicodedata
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import cv2  # noqa: E402
import jiwer  # noqa: E402

from app.pipeline.run import process_page  # noqa: E402
from app.ingest import load_pages  # noqa: E402

FIX = Path(__file__).parent / "fixtures"
RES = Path(__file__).parent / "results"
LANG_BY_PREFIX = {"de": "de", "fr": "fr", "es": "es", "zh": "zh", "ko": "ko", "ja": "zh", "ru": "ru", "ar": "ar", "en": "en", "hw": "en",
                  "table": "en", "math": "en", "pdf": "en"}
CJK = re.compile(r"[⺀-鿿가-힯぀-ヿ]")


def norm(t, cjk=False):
    t = unicodedata.normalize("NFC", t)
    t = re.sub(r"\s+", "" if cjk else " ", t).strip()
    return t


def score(ref, hyp):
    cjk = bool(CJK.search(ref))
    r, h = norm(ref, cjk), norm(hyp, cjk)
    cer = jiwer.cer(r, h) if r else None
    wer = None if cjk else (jiwer.wer(r, h) if r else None)
    return cer, wer


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default="printed")
    ap.add_argument("--only", default="")
    ap.add_argument("--lang", default="")
    ap.add_argument("--auto-lang", action="store_true")
    a = ap.parse_args()
    rows = []
    files = sorted(p for p in FIX.iterdir() if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".pdf"} and p.with_suffix(".txt").exists())
    for p in files:
        if a.only and a.only not in p.name:
            continue
        ref = p.with_suffix(".txt").read_text(encoding="utf-8")
        lang = "auto" if a.auto_lang else (a.lang or LANG_BY_PREFIX.get(p.name.split("_")[0], "en"))
        mode = "handwriting" if p.name.startswith("hw") and a.mode == "printed" else a.mode
        t = time.time()
        try:
            pages = load_pages(p.read_bytes(), p.name)
            texts, notes, flagged, lang_found = [], [], 0, None
            for i, pg in enumerate(pages):
                r = process_page(pg.bgr, i + 1, {"mode": mode, "lang": lang})
                texts.append(r["cleaned_text"] if False else r["raw_text"])
                flagged += r["stats"]["flagged_words"]
                lang_found = r["language"]["code"]
                notes += r["warnings"][:1]
            hyp = "\n\n".join(texts)
            cer, wer = score(ref, hyp)
            rows.append({"file": p.name, "lang": lang, "detected": lang_found, "mode": mode, "cer": cer, "wer": wer,
                         "seconds": round(time.time() - t, 1), "flagged_words": flagged, "hyp": hyp, "notes": notes})
            print(f"{p.name:28s} lang={lang:5s}->{lang_found}  CER={cer:.3f}  WER={'-' if wer is None else format(wer, '.3f')}  {rows[-1]['seconds']}s", flush=True)
        except Exception as e:
            rows.append({"file": p.name, "error": repr(e)})
            print(f"{p.name:28s} ERROR {e!r}", flush=True)
    RES.mkdir(exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    (RES / f"{stamp}-{a.mode}.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    ok = [r for r in rows if r.get("cer") is not None]
    md = [f"# Benchmark {stamp} (mode={a.mode})", "", "| file | lang | CER | WER | s |", "|---|---|---|---|---|"]
    for r in ok:
        md.append(f"| {r['file']} | {r['lang']}→{r['detected']} | {r['cer']:.3f} | {'–' if r['wer'] is None else format(r['wer'], '.3f')} | {r['seconds']} |")
    if ok:
        md += ["", f"Mean CER over {len(ok)} files: {sum(r['cer'] for r in ok) / len(ok):.3f}"]
    (RES / f"{stamp}-{a.mode}.md").write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md[-3:]))


if __name__ == "__main__":
    main()
