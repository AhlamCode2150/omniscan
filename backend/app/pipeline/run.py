"""Page / document orchestration: analysis -> enhancement -> recognition -> verification -> structuring."""
import re
import time
from difflib import SequenceMatcher

import cv2
import numpy as np

from . import enhance as E, verify as V, clean as C, structure as S
from .. import config
from ..engines import registry
from ..engines.base import EngineResult, split_line_into_words
from ..languages import LANGS, RAPID_REC, guess_language, is_rtl, script_histogram

STAGES = ["Analyzing image", "Detecting text regions", "Enhancing image", "Recognizing characters",
          "Verifying extraction", "Formatting results"]
MODES = ("auto", "printed", "handwriting", "academic")


class Progress:
    def __init__(self, cb=None, page=0, pages=1):
        self.cb, self.page, self.pages = cb, page, pages

    def __call__(self, stage, frac=0.0, msg=""):
        if self.cb:
            pct = (self.page + (stage + frac) / len(STAGES)) / self.pages
            self.cb({"stage": stage, "stage_name": STAGES[stage], "pct": round(pct * 100, 1), "message": msg,
                     "page": self.page + 1, "pages": self.pages})


# --------------------------------------------------------------------------- helpers
def _box_of(poly):
    xs = [p[0] for p in poly]; ys = [p[1] for p in poly]
    return [float(min(xs)), float(min(ys)), float(max(xs) - min(xs)), float(max(ys) - min(ys))]


def _to_orig(pts, Minv):
    return E.map_points(Minv, pts).tolist()


def _convert(res: EngineResult, Minv, page_no, prefix="l"):
    """EngineResult (processed coords) -> list of line dicts in original coords."""
    lines = []
    for li, l in enumerate(res.lines):
        lid = f"p{page_no}-{prefix}{li}"
        poly = _to_orig(l.poly, Minv) if l.poly else None
        words = []
        for wi, w in enumerate(l.words):
            wp = _to_orig(w.poly, Minv) if w.poly else None
            words.append({"id": f"{lid}-w{wi}", "text": w.text, "conf": None if w.conf is None else round(w.conf, 4),
                          "poly": wp, "box": _box_of(wp) if wp else None, "flags": [], "alts": [], "status": "recognized",
                          "est_box": w.est_box, "engine": res.engine, "pbox": _box_of(w.poly) if w.poly else None})
        lines.append({"id": lid, "text": l.text, "conf": None if l.conf is None else round(l.conf, 4), "poly": poly,
                      "box": _box_of(poly) if poly else None, "words": words, "engine": res.engine, "kind": "printed",
                      "pbox": _box_of(l.poly) if l.poly else None})
    return lines


def handwriting_features(bgr, lines_proc, mean_conf):
    """Heuristic only: handwriting tends to show variable stroke width, uneven component heights and lower recogniser confidence."""
    g = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    if max(g.shape) > 1600:
        f = 1600 / max(g.shape); g = cv2.resize(g, None, fx=f, fy=f, interpolation=cv2.INTER_AREA)
    bw = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    n, lab, stats, _ = cv2.connectedComponentsWithStats(bw, 8)
    hs = [stats[i, cv2.CC_STAT_HEIGHT] for i in range(1, n) if 6 < stats[i, cv2.CC_STAT_HEIGHT] < g.shape[0] * 0.3 and stats[i, cv2.CC_STAT_AREA] > 12]
    h_cv = float(np.std(hs) / (np.mean(hs) + 1e-6)) if len(hs) > 8 else 0.0
    dt = cv2.distanceTransform(bw, cv2.DIST_L2, 3)
    sk = cv2.ximgproc.thinning(bw) if hasattr(cv2, "ximgproc") else None
    widths = dt[(bw > 0) & (dt >= np.percentile(dt[bw > 0], 60))] if (bw > 0).any() else np.array([0.0])
    s_cv = float(np.std(widths) / (np.mean(widths) + 1e-6)) if widths.size > 20 else 0.0
    angs = []
    for l in lines_proc:
        p = np.array(l.poly) if l.poly else None
        if p is not None and len(p) == 4:
            angs.append(np.degrees(np.arctan2(p[1][1] - p[0][1], p[1][0] - p[0][0])))
    base_jit = float(np.std(angs)) if len(angs) > 2 else 0.0
    score = 0.0
    score += min(1.0, max(0.0, (0.93 - (mean_conf or 0.5)) * 3.0)) * 0.45
    score += min(1.0, h_cv / 0.9) * 0.25
    score += min(1.0, s_cv / 0.45) * 0.15
    score += min(1.0, base_jit / 3.0) * 0.15
    return {"score": round(score, 3), "recognizer_conf": None if mean_conf is None else round(mean_conf, 3),
            "component_height_cv": round(h_cv, 3), "stroke_width_cv": round(s_cv, 3), "baseline_jitter_deg": round(base_jit, 2),
            "note": "Heuristic estimate, not a trained classifier. Choose 'Handwriting' mode to force the handwriting path."}


def orientation_trial(bgr, langs):
    """Try 0/90/180/270 on a small copy; return the number of 90° clockwise turns that gives the most confident text."""
    f = 1000 / max(bgr.shape[:2])
    small = cv2.resize(bgr, None, fx=f, fy=f, interpolation=cv2.INTER_AREA) if f < 1 else bgr
    eng = registry.get("rapidocr")
    best, best_k = -1, 0
    for k in range(4):
        im = np.ascontiguousarray(np.rot90(small, -k))
        r = eng.recognize(im, langs)
        chars = sum(len(l.text) for l in r.lines)
        sc = (r.mean_conf() or 0) * min(chars, 200)
        if sc > best * 1.15 or (k == 0 and best < 0):
            best, best_k = sc, k
    return best_k


def auto_language(img, prog):
    """Detect script by trying recogniser families on the same image and picking the best-scoring one."""
    eng = registry.get("rapidocr")
    cands = []
    r = eng.recognize(img, ["en"], {"rec_override": "LATIN"})
    txt = r.text
    hist = script_histogram(txt)
    latin_share = hist.get("latin", 0) / max(1, sum(hist.values()))
    cands.append(("latin", r, (r.mean_conf() or 0) * len(txt) * (0.5 + latin_share)))
    if not (latin_share > 0.9 and (r.mean_conf() or 0) > 0.85 and len(txt) > 15):
        fam = [("han", "CH"), ("hangul", "KOREAN"), ("cyrillic", "CYRILLIC"), ("arabic", "ARABIC"), ("devanagari", "DEVANAGARI")]
        for i, (script, rec) in enumerate(fam):
            prog(1, 0.2 + 0.6 * (i + 1) / len(fam), f"Trying {script} recogniser")
            rr = eng.recognize(img, ["en"], {"rec_override": rec})
            h = script_histogram(rr.text)
            share = h.get({"han": "han", "hangul": "hangul", "cyrillic": "cyrillic", "arabic": "arabic", "devanagari": "devanagari"}[script], 0)
            if script == "han":
                share += h.get("kana", 0)
            share = share / max(1, sum(h.values()))
            cands.append((script, rr, (rr.mean_conf() or 0) * len(rr.text) * (0.2 + share)))
    best = max(cands, key=lambda c: c[2])
    code, basis, conf = guess_language(best[1].text)
    return best[1], code or "en", basis, conf, [(c[0], round(c[2], 1)) for c in cands]


def _vlm_candidates(prefer=None):
    out = []
    for n in ([prefer] if prefer else []) + ["anthropic-vlm", "ollama-vlm"]:
        if n and n not in out and registry.get(n).available()[0]:
            out.append(n)
    return out


_STRUCT = re.compile(r"\[\?\]")


def _to_struct(lines):
    for l in lines:
        if l.get("pbox"):
            l["obox"], l["opoly"], l["box"] = l["box"], l["poly"], l["pbox"]
        for w in l["words"]:
            if w.get("pbox"):
                w["obox"], w["opoly"], w["box"] = w["box"], w["poly"], w["pbox"]


def _map_box(Minv, b):
    pts = E.map_points(Minv, [[b[0], b[1]], [b[0] + b[2], b[1]], [b[0] + b[2], b[1] + b[3]], [b[0], b[1] + b[3]]])
    return _box_of(pts.tolist())


def _restore_orig(ordered, blocks, tables, Minv):
    byid = {}
    for l in ordered:
        if "obox" in l:
            l["box"], l["poly"] = l.pop("obox"), l.pop("opoly")
        l.pop("pbox", None)
        for w in l["words"]:
            if "obox" in w:
                w["box"], w["poly"] = w.pop("obox"), w.pop("opoly")
            w.pop("pbox", None)
        byid[l["id"]] = l
        for src in l.get("merged_from", []):
            byid[src] = l
    for b in blocks:
        if b["type"] == "table":
            b["box"] = _map_box(Minv, b["box"])
            for r in b["rows"]:
                for c in r:
                    c["box"] = _map_box(Minv, c["box"])
        else:
            bx = [byid[i]["box"] for i in b.get("line_ids", []) if i in byid and byid[i].get("box")]
            if bx:
                x0 = min(q[0] for q in bx); y0 = min(q[1] for q in bx)
                x1 = max(q[0] + q[2] for q in bx); y1 = max(q[1] + q[3] for q in bx)
                b["box"] = [x0, y0, x1 - x0, y1 - y0]
    out = []
    for t in tables:
        out.append({"box": _map_box(Minv, t["box"]), "rows": [[_map_box(Minv, c) for c in r] for r in t["rows"]]})
    return out


def align_vlm(vlm: EngineResult, base_lines, page_no, Minv_unused=None):
    """Attach boxes from a box-bearing engine to a VLM transcription (line-wise, order preserving)."""
    vl = vlm.lines
    used, last = set(), -1
    out = []
    nb = len(base_lines)
    same_count = len(vl) == nb
    for i, l in enumerate(vl):
        j = None
        if same_count:
            j = i
        else:
            best, bj = 0.0, None
            for k in range(last + 1, min(nb, last + 4)):
                if k in used:
                    continue
                r = SequenceMatcher(None, V.norm(l.text), V.norm(base_lines[k]["text"])).ratio()
                if r > best:
                    best, bj = r, k
            if best >= 0.35:
                j = bj
        lid = f"p{page_no}-v{i}"
        if j is not None:
            used.add(j); last = j
            bl = base_lines[j]
            poly, box = bl["poly"], bl["box"]
        else:
            poly = box = None
        words = []
        toks = l.text.split()
        bws = base_lines[j]["words"] if j is not None else []
        for wi, t in enumerate(toks):
            wb = None; est = True
            if j is not None and len(bws) == len(toks) and bws[wi]["poly"]:
                wb = bws[wi]["poly"]; est = bws[wi].get("est_box", False)
            elif j is not None and poly:
                ew = split_line_into_words(l.text, poly, None)
                if wi < len(ew):
                    wb = ew[wi].poly
            words.append({"id": f"{lid}-w{wi}", "text": t, "conf": None, "poly": wb, "box": _box_of(wb) if wb else None,
                          "flags": ["no-engine-confidence"], "alts": [], "status": "recognized", "est_box": est,
                          "engine": vlm.engine})
        out.append({"id": lid, "text": l.text, "conf": None, "poly": poly, "box": box, "words": words, "engine": vlm.engine,
                    "kind": "handwritten", "pbox": base_lines[j].get("pbox") if j is not None else None})
    return out


# --------------------------------------------------------------------------- main page processor
def process_page(bgr, page_no=1, opts=None, prog=None):
    opts = opts or {}
    prog = prog or Progress()
    t_all = time.time()
    mode = opts.get("mode", "auto")
    lang_opt = opts.get("lang", "auto")
    level = opts.get("enhance", "auto")
    warnings, engines_log = [], []
    H0, W0 = bgr.shape[:2]

    prog(0, 0.1, "Measuring resolution, sharpness, skew, lighting")
    info = E.analyze(bgr)
    prog(0, 1.0, ", ".join(info["issues"]) or "no major issues")

    # ---- detect (orientation) ----
    prog(1, 0.1, "Checking page orientation")
    rotate = int(opts.get("rotate90", 0))
    probe_langs = ["en"] if lang_opt == "auto" else [lang_opt]
    if not rotate and opts.get("auto_orient", True):
        probe, _, _ = E.enhance(bgr, info, "off", 0, 1000)
        eng0 = registry.get("rapidocr")
        base = eng0.recognize(probe, probe_langs, {"rec_override": "LATIN"} if lang_opt == "auto" else None)
        chars = sum(len(l.text) for l in base.lines)
        if (base.mean_conf() or 0) < 0.55 or chars < 8:
            rotate = orientation_trial(probe, probe_langs)
            if rotate:
                warnings.append(f"Page appears rotated; auto-rotated {rotate * 90}° clockwise.")
    prog(1, 1.0, "")

    # ---- enhance ----
    prog(2, 0.1, "Building enhanced copy (original is preserved)")
    proc, M, steps = E.enhance(bgr, info, level, rotate, config.OCR_MAX_SIDE)
    Minv = np.linalg.inv(M)
    prog(2, 1.0, ", ".join(steps) or "no enhancement needed")

    # ---- recognize ----
    prog(3, 0.05, "Selecting engines")
    primary_res, lang_code, lang_basis, lang_conf, lang_trials = None, None, "", 0.0, []
    if lang_opt == "auto":
        primary_res, lang_code, lang_basis, lang_conf, lang_trials = auto_language(proc, prog)
        lang_source = "auto-detected"
    else:
        lang_code, lang_basis, lang_conf, lang_source = lang_opt, "chosen by user", 1.0, "user"
    langs = [lang_code]
    # Alternate preprocessing candidate: keep whichever view the engine is more confident about
    rapid = registry.get("rapidocr")
    if primary_res is None:
        prog(3, 0.2, f"PaddleOCR PP-OCRv5 ({lang_code})")
        primary_res = rapid.recognize(proc, langs)
    if (primary_res.mean_conf() or 0) < 0.75 and steps and level != "off":
        alt, Malt, _ = E.enhance(bgr, info, "off", rotate, config.OCR_MAX_SIDE)
        alt_res = rapid.recognize(alt, langs)
        if (alt_res.mean_conf() or 0) > (primary_res.mean_conf() or 0) + 0.03:
            primary_res, proc, Minv = alt_res, alt, np.linalg.inv(Malt)
            steps = ["enhancement skipped: engine was more confident on the un-enhanced image"]
    engines_log.append({"name": "rapidocr", "seconds": round(primary_res.seconds, 2), "mean_conf": primary_res.mean_conf(),
                        "lines": len(primary_res.lines), "model": primary_res.extra.get("rec_model"), "role": "primary-boxes"})
    base_lines = _convert(primary_res, Minv, page_no)
    hw = handwriting_features(proc, primary_res.lines, primary_res.mean_conf())

    # handwriting / math via VLM
    academic = mode == "academic"
    want_hw = mode == "handwriting" or (mode == "auto" and hw["score"] >= 0.55)
    vlm_lines, vlm_res, math_latex = None, None, None
    if want_hw or academic:
        names = _vlm_candidates(opts.get("vlm"))
        if not names:
            reason = registry.get("ollama-vlm").available()[1]
            warnings.append("No vision-language engine is available (" + reason + "). Handwriting and math recognition fall back to the "
                            "printed-text recogniser and are unreliable – see Recognition Details.")
        for n in names[:1]:
            try:
                prog(3, 0.55, f"Vision-language model {n} – this can take a few minutes on CPU")
                vlm_res = registry.get(n).recognize(proc, langs, {"math": academic and not want_hw or academic})
                engines_log.append({"name": n, "seconds": round(vlm_res.seconds, 1), "mean_conf": None, "lines": len(vlm_res.lines),
                                    "model": vlm_res.extra.get("model"), "role": "handwriting/math transcription"})
            except Exception as e:  # graceful degradation
                warnings.append(f"{n} failed: {str(e)[:160]}. Using printed-text recogniser output instead.")
                engines_log.append({"name": n, "error": str(e)[:200]})
    if vlm_res is not None and vlm_res.lines:
        if academic:
            math_latex = vlm_res.text
        if want_hw:
            vlm_lines = align_vlm(vlm_res, base_lines, page_no)
    lines = vlm_lines if vlm_lines else base_lines
    primary_name = "vlm" if vlm_lines else "rapidocr"

    # Optional second box-bearing engine for cross-check (printed text)
    second = None
    sec_issues, agreement = [], None
    prog(3, 0.8, "Second opinion engine")
    tess = registry.get("tesseract")
    if not vlm_lines and tess.available()[0] and lang_code in tess.languages() and opts.get("cross_check", True):
        try:
            tres = tess.recognize(proc, langs)
            engines_log.append({"name": "tesseract", "seconds": round(tres.seconds, 2), "mean_conf": tres.mean_conf(),
                                "lines": len(tres.lines), "role": "verification"})
            second = _convert(tres, Minv, page_no, "t")
        except Exception as e:
            warnings.append(f"tesseract failed: {str(e)[:120]}")
    elif not vlm_lines:
        why = tess.available()[1] or f"no Tesseract language data for '{lang_code}'"
        engines_log.append({"name": "tesseract", "skipped": why})

    # ---- verify ----
    prog(4, 0.2, "Cross-checking engines")
    issues = []
    for l in lines:
        l["words"] = [w for w in l["words"] if w["text"].strip()]
    V.confidence_flags(lines, primary_res.has_conf)
    if second is not None:
        iss, stats = V.cross_check(lines, second, "tesseract")
        issues += iss; agreement = stats
        # Line-level: second engine text for lines the primary may have truncated/missed
    issues += V.sanity_flags(lines)
    prog(4, 0.8, "Reading-order checks")
    rtl = is_rtl(lang_code)
    Hp, Wp = proc.shape[:2]
    _to_struct(lines)   # layout analysis runs in the deskewed image space; results are mapped back afterwards
    tables = S.detect_tables(cv2.cvtColor(proc, cv2.COLOR_BGR2GRAY)) if (mode != "handwriting" and not vlm_lines) else []
    ordered, ncols, order_notes = S.reading_order(lines, Wp, Hp, rtl, tables)
    issues += V.line_order_issues(ordered)
    if vlm_lines:
        warnings.append("Handwriting was transcribed by a single vision-language model. It provides no per-word confidence and was not "
                        "independently verified; words marked [?] were declared illegible by the model.")
    cross_checked = second is not None and agreement and agreement["compared_words"] > 0
    verification = {"level": "cross-checked" if cross_checked else "single-engine",
                    "engines_compared": ["rapidocr", "tesseract"] if cross_checked else [primary_name],
                    "agreement": agreement,
                    "statement": ("Two independent engines were compared. Agreement does not guarantee correctness." if cross_checked else
                                  "Only one engine produced this text. It has not been independently verified.")}

    # ---- structure & cleaning ----
    prog(5, 0.2, "Detecting layout")
    for i, l in enumerate(ordered):
        l["order"] = i
    blocks = S.build_blocks(ordered, Wp, Hp, tables)
    tables = _restore_orig(ordered, blocks, tables, Minv)
    raw_text = "\n".join(l["text"] for l in ordered)
    cleaned_lines, clog = C.clean_lines([l["text"] for l in ordered], rtl=rtl)
    cleaned_parts, para_log = [], []
    by_id = {l["id"]: c for l, c in zip(ordered, cleaned_lines)}
    for b in blocks:
        if b["type"] == "paragraph":
            t, lg = C.join_paragraph([by_id[i] for i in b["line_ids"]], rtl=rtl); para_log += lg; cleaned_parts.append(t)
        elif b["type"] == "heading":
            cleaned_parts.append(by_id[b["line_ids"][0]])
        elif b["type"] == "table":
            cleaned_parts.append("\n".join(" | ".join(c["text"] for c in r) for r in b["rows"]))
        elif b["type"] == "list":
            cleaned_parts.append("\n".join(("%d. " % (k + 1) if b.get("ordered") else "- ") + it for k, it in enumerate(b["items"])))
        else:
            cleaned_parts.append(by_id.get(b["line_ids"][0], b.get("text", "")))
    cleaned_text = "\n\n".join(cleaned_parts)
    math = None
    if academic or re.search(r"[⁰¹²³⁴⁵⁶⁷⁸⁹₀-₉√∑∫≤≥≠π∞±×÷]", raw_text):
        chem = C.chem_formulas(raw_text)
        math = {"latex_from_vlm": math_latex, "normalized_latex": C.unicode_math_to_latex(raw_text),
                "chemical_formulas": [{"recognized": a, "normalized": b} for a, b in chem],
                "note": ("LaTeX produced by a vision-language model; unverified." if math_latex else
                         "No math-capable model was available. 'normalized_latex' only converts Unicode math symbols that the OCR engine "
                         "already produced; it cannot recover structure (fractions, roots) from the image.")}
        if academic and not math_latex:
            warnings.append("Academic mode needs a vision-language model for equations; none produced output.")

    all_words = [w for l in ordered for w in l["words"]]
    confs = [w["conf"] for w in all_words if w["conf"] is not None]
    stats = {"lines": len(ordered), "words": len(all_words), "characters": len(raw_text.replace("\n", "")),
             "mean_conf": round(sum(confs) / len(confs), 4) if confs else None,
             "uncertain_words": sum(1 for w in all_words if w["status"] == "uncertain"),
             "flagged_words": sum(1 for w in all_words if w["flags"] and w["flags"] != ["agreed"] and w["flags"] != ["no-engine-confidence"]),
             "columns": ncols, "tables": sum(1 for b in blocks if b["type"] == "table"), "seconds": round(time.time() - t_all, 2)}
    if not all_words:
        warnings.append("No text was recognised. The image may be blank, too blurry, or too low-contrast. Try the "
                        "'Aggressive' enhancement level, rotate the image, or choose another language/mode and retry.")
    prog(5, 1.0, "")
    return {
        "page": page_no, "width": W0, "height": H0, "source": "ocr", "mode": mode, "analysis": info,
        "enhancement": {"level": level, "steps": steps, "rotate90": rotate},
        "language": {"code": lang_code, "name": LANGS.get(lang_code, (lang_code,))[0], "source": lang_source, "basis": lang_basis,
                     "confidence": round(lang_conf, 2), "rtl": rtl, "trials": lang_trials,
                     "note": "Automatic language detection is heuristic (script + common words)." if lang_source != "user" else ""},
        "handwriting": hw | {"used_vlm": bool(vlm_lines)},
        "engines": engines_log, "primary_engine": primary_name, "verification": verification,
        "lines": ordered, "blocks": blocks, "tables": tables, "raw_text": raw_text,
        "cleaned_text": cleaned_text, "cleaning_log": clog + para_log, "layout_notes": order_notes,
        "issues": issues, "math": math, "warnings": warnings, "stats": stats, "edited_text": None,
        "has_word_boxes": any(w["box"] for w in all_words), "_enhanced": proc,
    }


def native_pdf_page(words, page_no, img_w, img_h, zoom):
    """Use the PDF text layer when present (exact text; no OCR confidence applies)."""
    if len(" ".join(w[4] for w in words)) < 30:
        return None
    lines = {}
    for x0, y0, x1, y1, t, b, ln, wn in words:
        lines.setdefault((b, ln), []).append((x0 * zoom, y0 * zoom, x1 * zoom, y1 * zoom, t, wn))
    out = []
    for i, key in enumerate(sorted(lines, key=lambda k: (min(w[1] for w in lines[k]), min(w[0] for w in lines[k])))):
        ws = sorted(lines[key], key=lambda w: w[5])
        lid = f"p{page_no}-n{i}"
        wd = [{"id": f"{lid}-w{j}", "text": w[4], "conf": None, "poly": [[w[0], w[1]], [w[2], w[1]], [w[2], w[3]], [w[0], w[3]]],
               "box": [w[0], w[1], w[2] - w[0], w[3] - w[1]], "flags": ["pdf-text-layer"], "alts": [], "status": "recognized",
               "est_box": False, "engine": "pdf-text-layer"} for j, w in enumerate(ws)]
        x0 = min(w[0] for w in ws); y0 = min(w[1] for w in ws); x1 = max(w[2] for w in ws); y1 = max(w[3] for w in ws)
        out.append({"id": lid, "text": " ".join(w[4] for w in ws), "conf": None,
                    "poly": [[x0, y0], [x1, y0], [x1, y1], [x0, y1]], "box": [x0, y0, x1 - x0, y1 - y0], "words": wd,
                    "engine": "pdf-text-layer", "kind": "printed"})
    ordered, ncols, notes = S.reading_order(out, img_w, img_h, False)
    for i, l in enumerate(ordered):
        l["order"] = i
    blocks = S.build_blocks(ordered, img_w, img_h, [])
    raw = "\n".join(l["text"] for l in ordered)
    cl, log = C.clean_lines([l["text"] for l in ordered])
    by_id = {l["id"]: c for l, c in zip(ordered, cl)}
    parts = []
    for b in blocks:
        if b["type"] == "paragraph":
            t, lg = C.join_paragraph([by_id[i] for i in b["line_ids"]]); log += lg; parts.append(t)
        elif b["type"] == "list":
            parts.append("\n".join("- " + it for it in b["items"]))
        else:
            parts.append(by_id.get(b["line_ids"][0], b.get("text", "")) if b.get("line_ids") else b.get("text", ""))
    return {"page": page_no, "width": img_w, "height": img_h, "source": "pdf-text-layer", "mode": "native", "analysis": None,
            "enhancement": {"level": "n/a", "steps": [], "rotate90": 0},
            "language": {"code": None, "name": "n/a", "source": "n/a", "basis": "PDF text layer", "confidence": 0, "rtl": False, "trials": [], "note": ""},
            "handwriting": None, "engines": [{"name": "pdf-text-layer", "role": "embedded text"}], "primary_engine": "pdf-text-layer",
            "verification": {"level": "native-text", "engines_compared": [], "agreement": None,
                             "statement": "Text was read from the PDF's embedded text layer, not recognised from pixels. "
                                          "Its accuracy is that of whoever produced the PDF (it may itself be earlier OCR output)."},
            "lines": ordered, "blocks": blocks, "tables": [], "raw_text": raw, "cleaned_text": "\n\n".join(parts), "cleaning_log": log,
            "layout_notes": notes, "issues": [], "math": None, "warnings": [], "edited_text": None, "has_word_boxes": True,
            "stats": {"lines": len(ordered), "words": sum(len(l["words"]) for l in ordered), "characters": len(raw.replace("\n", "")),
                      "mean_conf": None, "uncertain_words": 0, "flagged_words": 0, "columns": ncols, "tables": 0, "seconds": 0}}
