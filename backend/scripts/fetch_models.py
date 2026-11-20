"""Download optional model data: Tesseract language packs (tessdata_fast).

RapidOCR models auto-download on first use into OMNISCAN_MODEL_DIR/rapidocr.
Usage:  python scripts/fetch_models.py [lang_code ...]
"""
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import config  # noqa: E402
from app.languages import TESS  # noqa: E402

BASE = "https://github.com/tesseract-ocr/tessdata_fast/raw/main/{}.traineddata"


def main(codes):
    out = config.MODEL_DIR / "tessdata"
    out.mkdir(parents=True, exist_ok=True)
    names = sorted({TESS[c] for c in codes if c in TESS} | {"osd"})
    for n in names:
        dest = out / f"{n}.traineddata"
        if dest.exists() and dest.stat().st_size > 10_000:
            print(f"have {n}")
            continue
        print(f"fetching {n} ...", flush=True)
        with httpx.stream("GET", BASE.format(n), follow_redirects=True, timeout=120) as r:
            r.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in r.iter_bytes():
                    f.write(chunk)
        print(f"  {dest.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main(sys.argv[1:] or list(TESS))
