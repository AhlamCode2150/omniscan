"""RapidOCR engine: PaddleOCR PP-OCRv5 detection + recognition models executed on ONNX Runtime (CPU).

Recognition models exist per script family; we only advertise languages whose script family has a model.
"""
import threading
import time
import warnings

from .base import Engine, EngineResult, ELine, EWord, split_line_into_words
from .. import config
from ..languages import LANGS, RAPID_REC

_lock = threading.Lock()
_cache = {}


def _get(rec_name):
    with _lock:
        if rec_name in _cache:
            return _cache[rec_name]
        warnings.filterwarnings("ignore")
        from rapidocr import RapidOCR, LangRec, LangDet, ModelType, OCRVersion
        eng = RapidOCR(params={
            "Det.ocr_version": OCRVersion.PPOCRV5, "Rec.ocr_version": OCRVersion.PPOCRV5, "Cls.ocr_version": OCRVersion.PPOCRV5,
            "Det.model_type": ModelType.MOBILE, "Rec.model_type": ModelType.MOBILE, "Cls.model_type": ModelType.MOBILE,
            "Det.lang_type": LangDet.MULTI, "Rec.lang_type": getattr(LangRec, rec_name),
            "Global.log_level": "error", "Global.model_root_dir": str(config.MODEL_DIR / "rapidocr"),
        })
        _cache[rec_name] = eng
        return eng


class RapidEngine(Engine):
    name = "rapidocr"
    kind = "printed"
    label = "PaddleOCR PP-OCRv5 (RapidOCR/ONNX)"

    def available(self):
        try:
            import rapidocr  # noqa: F401
            return True, ""
        except Exception as e:  # pragma: no cover
            return False, f"rapidocr not importable: {e}"

    def languages(self):
        return sorted(LANGS)

    def recognize(self, bgr, langs, opts=None):
        opts = opts or {}
        script = LANGS.get((langs or ["en"])[0], ("", "latin", False))[1]
        rec = opts.get("rec_override") or RAPID_REC.get(script, "LATIN")
        t0 = time.time()
        eng = _get(rec)
        want_words = script in ("latin", "cyrillic")
        out = eng(bgr, return_word_box=want_words)
        lines = []
        notes = []
        if out is None or out.txts is None:
            return EngineResult(self.name, [], "", langs, time.time() - t0, ["no text detected"])
        words_by_line = getattr(out, "word_results", None)
        for i, (box, txt, sc) in enumerate(zip(out.boxes, out.txts, out.scores)):
            poly = [[float(x), float(y)] for x, y in box]
            ws = []
            wr = words_by_line[i] if words_by_line and i < len(words_by_line) else None
            if wr:
                for item in wr:
                    wt, wsc, wb = item[0], item[1], item[2]
                    if not str(wt).strip():
                        continue
                    ws.append(EWord(str(wt), float(wsc), [[float(x), float(y)] for x, y in wb]))
            if not ws:
                ws = split_line_into_words(txt, poly, float(sc))
            lines.append(ELine(txt, float(sc), poly, ws))
        # reading order: top-to-bottom, left-to-right (structure stage refines columns later)
        text = "\n".join(l.text for l in lines)
        return EngineResult(self.name, lines, text, langs, time.time() - t0, notes,
                            extra={"rec_model": rec})
