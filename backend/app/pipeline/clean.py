"""Deterministic text normalisation. Never uses a language model and never guesses words.

Every change is logged so the user can see exactly how Cleaned Text differs from the raw recognition.
"""
import re
import unicodedata

_LIGS = {"ﬁ": "fi", "ﬂ": "fl", "ﬀ": "ff", "ﬃ": "ffi", "ﬄ": "ffl"}
_QUOTES = {"‘": "'", "’": "'", "“": '"', "”": '"', "‚": "'", "„": '"'}
_CJK = re.compile(r"[⺀-鿿가-힯぀-ヿ]")
_RTL = re.compile(r"[֐-ࣿיִ-﷿ﹰ-﻿]")


def clean_lines(lines_text, rtl=False, normalize_quotes=False):
    """lines_text: list[str] (one per source line, already reading-ordered). Returns (text, log)."""
    log = []
    out = []
    for raw in lines_text:
        t = unicodedata.normalize("NFC", raw)
        n = t
        for k, v in _LIGS.items():
            n = n.replace(k, v)
        if n != t:
            log.append({"change": "ligature expanded", "before": t, "after": n})
        t = n
        n = re.sub(r"[ \t ]+", " ", t).strip()
        if n != t.strip() and re.search(r"[ \t ]{2,}", t):
            log.append({"change": "collapsed repeated spaces", "before": t, "after": n})
        t = n
        if not rtl and not _CJK.search(t):
            n = re.sub(r"\s+([,.;:!?])", r"\1", t)
            if n != t:
                log.append({"change": "removed space before punctuation", "before": t, "after": n})
            t = n
        if normalize_quotes:
            n = "".join(_QUOTES.get(c, c) for c in t)
            if n != t:
                log.append({"change": "straightened quotes", "before": t, "after": n})
            t = n
        out.append(t)
    return out, log


def join_paragraph(lines, rtl=False):
    """Join the lines of one paragraph. De-hyphenates only the unambiguous 'word-<newline>lowercase' case."""
    log = []
    if not lines:
        return "", log
    if any(_CJK.search(l) for l in lines):
        return "".join(lines), log
    text = lines[0]
    for nxt in lines[1:]:
        if re.search(r"[A-Za-zÀ-ÿ]{2,}-$", text) and nxt[:1].islower():
            joined = text[:-1] + nxt
            log.append({"change": "joined hyphenated line break", "before": f"{text} / {nxt}", "after": joined[-40:]})
            text = joined
        else:
            text = text + " " + nxt
    return text, log


# ---- academic helpers (kept separate from text: shown as 'normalized math') ----
_SUP = {"0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴", "5": "⁵", "6": "⁶", "7": "⁷", "8": "⁸", "9": "⁹", "+": "⁺", "-": "⁻"}
_SUB = {"0": "₀", "1": "₁", "2": "₂", "3": "₃", "4": "₄", "5": "₅", "6": "₆", "7": "₇", "8": "₈", "9": "₉"}
_FORMULA = re.compile(r"\b((?:[A-Z][a-z]?\d*){2,})\b")
_ELEMENTS = set("H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Fe Cu Zn Br Ag I Au Hg Pb Mn Cr Ni Co Sn Ti Ba".split())


def chem_formulas(text):
    """Find candidate chemical formulas (every symbol must be a real element). Returns [(src, normalized)]."""
    found = []
    for m in _FORMULA.finditer(text):
        tok = m.group(1)
        syms = re.findall(r"[A-Z][a-z]?", tok)
        if len(tok) >= 2 and all(s in _ELEMENTS for s in syms) and re.search(r"\d", tok):
            found.append((tok, re.sub(r"(?<=[A-Za-z\)])(\d+)", lambda g: "".join(_SUB[c] for c in g.group(1)), tok)))
    return found


def unicode_math_to_latex(t):
    """Conservative conversion of Unicode super/subscripts and symbols to LaTeX. Output is marked 'normalized'."""
    sup_rev = {v: k for k, v in _SUP.items()}
    sub_rev = {v: k for k, v in _SUB.items()}
    out = re.sub("([⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻]+)", lambda m: "^{" + "".join(sup_rev[c] for c in m.group(1)) + "}", t)
    out = re.sub("([₀₁₂₃₄₅₆₇₈₉]+)", lambda m: "_{" + "".join(sub_rev[c] for c in m.group(1)) + "}", out)
    for k, v in {"√": r"\sqrt", "×": r"\times", "÷": r"\div", "≤": r"\leq", "≥": r"\geq", "≠": r"\neq", "π": r"\pi",
                 "∞": r"\infty", "±": r"\pm", "≈": r"\approx", "°": r"^{\circ}", "∑": r"\sum", "∫": r"\int"}.items():
        out = out.replace(k, v + (" " if v.startswith("\\") else ""))
    return out
