"""Tesseract engine (optional). Gives word-level boxes and confidences; used as an independent second opinion."""
import os
import shutil
import subprocess
import time
from pathlib import Path

import cv2

from .base import Engine, EngineResult, ELine, EWord
from .. import config
from ..languages import TESS

_CANDIDATES = [r"D:\Tesseract-OCR\tesseract.exe", r"C:\Program Files\Tesseract-OCR\tesseract.exe",
               r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"]


def find_cmd():
    if config.TESSERACT_CMD and Path(config.TESSERACT_CMD).exists():
        return config.TESSERACT_CMD
    w = shutil.which("tesseract")
    if w:
        return w
    for c in _CANDIDATES:
        if Path(c).exists():
            return c
    return None


def _tessdata(cmd):
    if config.TESSDATA_DIR:
        return Path(config.TESSDATA_DIR)
    for p in (config.MODEL_DIR / "tessdata", Path(cmd).parent / "tessdata"):
        if p.exists():
            return p
    return Path(cmd).parent / "tessdata"


class TesseractEngine(Engine):
    name = "tesseract"
    kind = "printed"
    label = "Tesseract 5 (LSTM)"

    def available(self):
        cmd = find_cmd()
        if not cmd:
            return False, "Tesseract not installed (set TESSERACT_CMD or install UB-Mannheim build)"
        return True, ""

    def installed_langs(self):
        cmd = find_cmd()
        if not cmd:
            return []
        d = _tessdata(cmd)
        have = {p.stem for p in d.glob("*.traineddata")} if d.exists() else set()
        return have

    def languages(self):
        have = self.installed_langs()
        return sorted(k for k, v in TESS.items() if v in have)

    def recognize(self, bgr, langs, opts=None):
        cmd = find_cmd()
        have = self.installed_langs()
        codes = [TESS[l] for l in (langs or ["en"]) if l in TESS and TESS[l] in have]
        if not codes:
            return EngineResult(self.name, [], "", langs, 0.0, [f"tesseract language data missing for {langs}"])
        t0 = time.time()
        tmp = config.DATA_DIR / "_tmp"
        tmp.mkdir(exist_ok=True)
        f = tmp / f"t_{os.getpid()}_{int(time.time() * 1000)}.png"
        cv2.imwrite(str(f), bgr)
        env = dict(os.environ, TESSDATA_PREFIX=str(_tessdata(cmd)))
        try:
            r = subprocess.run([cmd, str(f), "stdout", "-l", "+".join(codes), "--psm", str((opts or {}).get("psm", 3)), "-c", "tessedit_create_tsv=1", "-c", "tessedit_create_txt=0"],
                               capture_output=True, text=True, encoding="utf-8", env=env, timeout=180)
        finally:
            f.unlink(missing_ok=True)
        if r.returncode != 0:
            return EngineResult(self.name, [], "", langs, time.time() - t0, [f"tesseract failed: {r.stderr[:200]}"])
        rows = [l.split("\t") for l in r.stdout.splitlines()[1:]]
        groups = {}
        for c in rows:
            if len(c) < 12 or not c[11].strip():
                continue
            lvl, blk, par, ln, wd = int(c[0]), c[2], c[3], c[4], c[5]
            x, y, w, h, conf = int(c[6]), int(c[7]), int(c[8]), int(c[9]), float(c[10])
            groups.setdefault((c[2], c[3], c[4]), []).append((c[11], conf, x, y, w, h))
        lines = []
        for key in sorted(groups, key=lambda k: (int(k[0]), int(k[1]), int(k[2]))):
            ws = []
            for t, cf, x, y, w, h in groups[key]:
                ws.append(EWord(t, None if cf < 0 else cf / 100.0, [[x, y], [x + w, y], [x + w, y + h], [x, y + h]]))
            xs = [p[0] for w in ws for p in w.poly]
            ys = [p[1] for w in ws for p in w.poly]
            cs = [w.conf for w in ws if w.conf is not None]
            lines.append(ELine(" ".join(w.text for w in ws), sum(cs) / len(cs) if cs else None,
                               [[min(xs), min(ys)], [max(xs), min(ys)], [max(xs), max(ys)], [min(xs), max(ys)]], ws))
        return EngineResult(self.name, lines, "\n".join(l.text for l in lines), langs, time.time() - t0,
                            extra={"tess_langs": codes})
