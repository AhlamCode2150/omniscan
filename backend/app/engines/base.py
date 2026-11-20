"""Pluggable OCR engine contract.

An engine returns lines/words in the coordinate space of the image it was given. The pipeline maps
them back to the original image. `conf` is None when the underlying model gives no usable score —
we never fabricate one.
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class EWord:
    text: str
    conf: Optional[float]          # 0..1 as reported by the engine, or None
    poly: list                     # 4 points [[x,y]...] in input-image coordinates
    est_box: bool = False          # True when the word box was estimated by splitting a line box


@dataclass
class ELine:
    text: str
    conf: Optional[float]
    poly: list
    words: list = field(default_factory=list)


@dataclass
class EngineResult:
    engine: str
    lines: list
    text: str = ""
    langs: list = field(default_factory=list)
    seconds: float = 0.0
    notes: list = field(default_factory=list)
    has_boxes: bool = True
    has_conf: bool = True
    extra: dict = field(default_factory=dict)

    def mean_conf(self):
        cs = [l.conf for l in self.lines if l.conf is not None]
        return sum(cs) / len(cs) if cs else None


class Engine:
    name = "base"
    kind = "printed"          # printed | handwriting | vlm
    label = "Base"

    def available(self) -> tuple[bool, str]:
        """(ok, reason). Reason explains *why not* when unavailable."""
        return True, ""

    def languages(self) -> list:
        return []

    def describe(self) -> dict:
        ok, why = self.available()
        return {"name": self.name, "label": self.label, "kind": self.kind, "available": ok,
                "reason": why, "languages": self.languages() if ok else []}

    def recognize(self, bgr, langs, opts=None) -> EngineResult:  # pragma: no cover
        raise NotImplementedError


def split_line_into_words(text, poly, conf):
    """Estimate word boxes by distributing the line box across words proportionally to character width.

    Honest fallback: flagged est_box=True so the UI can say alignment is approximate."""
    import numpy as np
    pts = np.array(poly, float)
    tl, tr, br, bl = pts[0], pts[1], pts[2], pts[3]
    if not text.strip():
        return []
    cjk = any(0x2E80 <= ord(c) <= 0xD7AF for c in text)
    tokens = [(m.group(), m.start(), m.end()) for m in __import__("re").finditer(r"\S+", text)] if not cjk else \
             [(c, i, i + 1) for i, c in enumerate(text) if not c.isspace()]
    n = len(text)
    out = []
    for tok, s, e in tokens:
        a, b = s / n, e / n
        p0, p1 = tl + (tr - tl) * a, tl + (tr - tl) * b
        q0, q1 = bl + (br - bl) * a, bl + (br - bl) * b
        out.append(EWord(tok, conf, [p0.tolist(), p1.tolist(), q1.tolist(), q0.tolist()], est_box=True))
    return out
