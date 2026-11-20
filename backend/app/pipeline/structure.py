"""Document structure: reading order, columns, headings, lists, checkboxes, form fields, tables, page furniture.

All heuristics are geometric/regex based and work on boxes in ORIGINAL image coordinates. They are
reported as detected structure, not as ground truth.
"""
import re
import statistics

import cv2
import numpy as np

BULLET = re.compile(r"^\s*([-•*·●▪‣◦–—]|\(?\d{1,3}[.)]|\(?[a-zA-Z][.)])\s+\S")
CHECK = re.compile(r"^\s*(\[\s?\]|\[[xX✓✔]\]|☐|☑|☒|□|■)\s*")
FIELD = re.compile(r"^\s*([^\W\d_][^:]{1,40}):\s*(_{2,}|\.{3,}|\s*)$")
PAGENUM = re.compile(r"^\s*(?:page\s+)?\d{1,4}(?:\s*(?:/|of)\s*\d{1,4})?\s*$|^\s*[-–]\s*\d{1,4}\s*[-–]\s*$", re.I)
FOOT = re.compile(r"^\s*(\d{1,2}|[*†‡§])[\s.)]+\S")


def _med(vals, default=1.0):
    return statistics.median(vals) if vals else default


def _merge_row(items, rtl):
    """Merge several detections that sit on the same text row into one line (ordered by reading direction)."""
    items = sorted(items, key=lambda l: l["box"][0], reverse=rtl)
    if len(items) == 1:
        return items[0]
    words = [w for it in items for w in it["words"]]
    polys = [p for it in items for p in (it["poly"] or [])]
    x0 = min(p[0] for p in polys); y0 = min(p[1] for p in polys); x1 = max(p[0] for p in polys); y1 = max(p[1] for p in polys)
    cs = [it["conf"] for it in items if it["conf"] is not None]
    merged = dict(items[0])
    if all("opoly" in it and it["opoly"] for it in items):
        op = [q for it in items for q in it["opoly"]]
        rect = cv2.boxPoints(cv2.minAreaRect(np.array(op, np.float32)))
        o = np.array(op)
        merged["opoly"] = rect.tolist()
        merged["obox"] = [float(o[:, 0].min()), float(o[:, 1].min()), float(o[:, 0].max() - o[:, 0].min()), float(o[:, 1].max() - o[:, 1].min())]
    merged.update(text=" ".join(it["text"] for it in items), words=words, poly=[[x0, y0], [x1, y0], [x1, y1], [x0, y1]],
                  box=[x0, y0, x1 - x0, y1 - y0], conf=round(sum(cs) / len(cs), 4) if cs else None, merged_from=[it["id"] for it in items])
    return merged


def merge_rows(lines, rtl=False):
    """Cluster boxed lines into rows by vertical overlap, then merge each row."""
    boxed = sorted([l for l in lines if l.get("box")], key=lambda l: l["box"][1] + l["box"][3] / 2)
    rows = []
    for l in boxed:
        top, bot = l["box"][1], l["box"][1] + l["box"][3]
        for r in reversed(rows[-3:]):
            ov = min(bot, r["bot"]) - max(top, r["top"])
            if ov >= 0.5 * min(bot - top, r["bot"] - r["top"]):
                r["items"].append(l); r["top"], r["bot"] = min(top, r["top"]), max(bot, r["bot"]); break
        else:
            rows.append({"top": top, "bot": bot, "items": [l]})
    rows.sort(key=lambda r: r["top"])
    return [_merge_row(r["items"], rtl) for r in rows]


def reading_order(lines, page_w, page_h, rtl=False, tables=None):
    """Table-aware wrapper: lines inside ruled tables are merged row-wise and spliced in by position."""
    tables = tables or []
    if not tables:
        return _reading_order(lines, page_w, page_h, rtl)
    def tidx(l):
        b = l.get("box")
        if not b:
            return None
        cx, cy = b[0] + b[2] / 2, b[1] + b[3] / 2
        for i, t in enumerate(tables):
            if t["box"][0] <= cx <= t["box"][0] + t["box"][2] and t["box"][1] <= cy <= t["box"][1] + t["box"][3]:
                return i
        return None
    groups = {}
    rest = []
    for l in lines:
        i = tidx(l)
        (groups.setdefault(i, []) if i is not None else rest).append(l)
    ordered, ncols, notes = _reading_order(rest, page_w, page_h, rtl)
    for i in sorted(groups, key=lambda k: tables[k]["box"][1], reverse=True):
        rows = merge_rows(groups[i], rtl)
        pos = next((k for k, l in enumerate(ordered) if l.get("box") and l["box"][1] > tables[i]["box"][1]), len(ordered))
        ordered[pos:pos] = rows
    return ordered, ncols, notes


def _reading_order(lines, page_w, page_h, rtl=False):
    """Order lines with column awareness and merge same-row detections. Returns (ordered_lines, n_columns, notes)."""
    boxed = [l for l in lines if l.get("box")]
    unboxed = [l for l in lines if not l.get("box")]
    if len(boxed) < 6:
        return merge_rows(boxed, rtl) + unboxed, 1, []
    bins = 120
    cov = np.zeros(bins)
    for l in boxed:
        x, y, w, h = l["box"]
        if w < 0.6 * page_w:  # full-width lines (titles) do not vote
            cov[int(max(0, x) / page_w * bins):int(min(page_w, x + w) / page_w * bins) + 1] += 1
    gutter, run = None, None
    for i in range(int(bins * 0.2), int(bins * 0.8)):
        if cov[i] == 0:
            run = run or [i, i]
            run[1] = i
        else:
            if run and run[1] - run[0] >= 2 and (gutter is None or run[1] - run[0] > gutter[1] - gutter[0]):
                gutter = run[:]
            run = None
    if run and run[1] - run[0] >= 2 and (gutter is None or run[1] - run[0] > gutter[1] - gutter[0]):
        gutter = run[:]
    if gutter:
        gx = (gutter[0] + gutter[1]) / 2 / bins * page_w
        left = [l for l in boxed if l["box"][0] + l["box"][2] <= gx + 5]
        right = [l for l in boxed if l["box"][0] >= gx - 5]
        if len(left) >= 3 and len(right) >= 3:
            spanning = sorted([l for l in boxed if l not in left and l not in right], key=lambda l: l["box"][1])
            cuts = [-1] + [l["box"][1] + l["box"][3] / 2 for l in spanning] + [1e12]
            out = []
            for a, b in zip(cuts[:-1], cuts[1:]):
                band_l = merge_rows([l for l in left if a < l["box"][1] + l["box"][3] / 2 <= b], rtl)
                band_r = merge_rows([l for l in right if a < l["box"][1] + l["box"][3] / 2 <= b], rtl)
                out += (band_r + band_l) if rtl else (band_l + band_r)
                out += [s for s in spanning if abs(s["box"][1] + s["box"][3] / 2 - b) < 1e-6]
            return out + unboxed, 2, ["two-column layout detected; lines read column by column"]
    return merge_rows(boxed, rtl) + unboxed, 1, []


def detect_tables(gray):
    """Find ruled tables (grid lines) with morphology. Returns list of {box, rows:[[cellbox]]} in gray-image coords."""
    h, w = gray.shape
    sc = 1400 / max(h, w) if max(h, w) > 1400 else 1.0
    g = cv2.resize(gray, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA) if sc != 1.0 else gray
    bw = cv2.adaptiveThreshold(g, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 15, 8)
    H, W = bw.shape
    hor = cv2.morphologyEx(bw, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (max(25, W // 25), 1)))
    ver = cv2.morphologyEx(bw, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(25, H // 25))))
    grid = cv2.dilate(cv2.add(hor, ver), np.ones((3, 3), np.uint8))
    cnts, _ = cv2.findContours(grid, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    tables = []
    for c in cnts:
        x, y, bw_, bh = cv2.boundingRect(c)
        if bw_ < W * 0.2 or bh < H * 0.08:
            continue
        sub_h, sub_v = hor[y:y + bh, x:x + bw_], ver[y:y + bh, x:x + bw_]
        if cv2.countNonZero(sub_h) < 20 or cv2.countNonZero(sub_v) < 20:
            continue
        ys = _peaks(sub_h.sum(1), bh)
        xs = _peaks(sub_v.sum(0), bw_)
        if len(ys) < 3 or len(xs) < 2:
            continue
        rows = []
        for r in range(len(ys) - 1):
            rows.append([[(x + xs[c_]) / sc, (y + ys[r]) / sc, (xs[c_ + 1] - xs[c_]) / sc, (ys[r + 1] - ys[r]) / sc]
                         for c_ in range(len(xs) - 1)])
        tables.append({"box": [x / sc, y / sc, bw_ / sc, bh / sc], "rows": rows})
    return tables


def _peaks(profile, n):
    prof = np.asarray(profile, float)
    if prof.max() == 0:
        return []
    idx = np.nonzero(prof > prof.max() * 0.5)[0]
    groups, cur = [], [idx[0]] if len(idx) else []
    for i in idx[1:]:
        if i - cur[-1] <= 4:
            cur.append(i)
        else:
            groups.append(int(np.mean(cur)))
            cur = [i]
    if cur:
        groups.append(int(np.mean(cur)))
    return groups


def build_blocks(lines, page_w, page_h, tables_orig=None):
    """lines: reading-ordered line dicts. Returns blocks list."""
    heights = [l["box"][3] for l in lines if l.get("box")]
    mh = _med(heights, 20)
    blocks, para = [], []

    def flush():
        nonlocal para
        if para:
            blocks.append({"type": "paragraph", "line_ids": [l["id"] for l in para], "lines": [l["text"] for l in para],
                           "box": _union([l["box"] for l in para if l.get("box")])})
            para = []

    # lines that fall inside a ruled table are emitted as the table instead
    in_table = {}
    for ti, t in enumerate(tables_orig or []):
        tx, ty, tw, th = t["box"]
        for l in lines:
            if l.get("box") and tx <= l["box"][0] + l["box"][2] / 2 <= tx + tw and ty <= l["box"][1] + l["box"][3] / 2 <= ty + th:
                in_table[l["id"]] = ti
    emitted = set()
    prev = None
    for i, l in enumerate(lines):
        if l["id"] in in_table:
            flush()
            ti = in_table[l["id"]]
            if ti not in emitted:
                emitted.add(ti)
                blocks.append(_table_block(tables_orig[ti], lines))
            prev = None
            continue
        t, box = l["text"].strip(), l.get("box")
        if not t:
            continue
        top_band = box and box[1] + box[3] < 0.07 * page_h
        bot_band = box and box[1] > 0.93 * page_h
        if PAGENUM.match(t) and (top_band or bot_band or len(t) <= 8):
            flush(); blocks.append({"type": "page-number", "line_ids": [l["id"]], "text": t, "box": box}); prev = l; continue
        if (top_band or bot_band) and len(t) < 90 and box[3] <= 1.1 * mh:
            flush(); blocks.append({"type": "header" if top_band else "footer", "line_ids": [l["id"]], "text": t, "box": box}); prev = l; continue
        m = CHECK.match(t)
        if m:
            flush()
            sym = m.group(1)
            blocks.append({"type": "checkbox", "line_ids": [l["id"]], "checked": bool(re.search(r"[xX✓✔☑☒■]", sym)),
                           "text": t[m.end():], "box": box}); prev = l; continue
        if box and box[3] >= 1.35 * mh and len(t) < 120:
            flush()
            lvl = 1 if box[3] >= 1.8 * mh else 2
            blocks.append({"type": "heading", "level": lvl, "line_ids": [l["id"]], "text": t, "box": box}); prev = l; continue
        if box and t.isupper() and len(t) < 60 and len(t) > 3 and box[3] >= 1.1 * mh and (prev is None or True) and not BULLET.match(t):
            flush(); blocks.append({"type": "heading", "level": 2, "line_ids": [l["id"]], "text": t, "box": box}); prev = l; continue
        if BULLET.match(t):
            flush()
            if blocks and blocks[-1]["type"] == "list":
                blocks[-1]["items"].append(re.sub(r"^\s*([-•*·●▪‣◦–—]|\(?\w{1,3}[.)])\s+", "", t)); blocks[-1]["line_ids"].append(l["id"])
            else:
                blocks.append({"type": "list", "ordered": bool(re.match(r"^\s*\(?\w{1,3}[.)]", t)),
                               "items": [re.sub(r"^\s*([-•*·●▪‣◦–—]|\(?\w{1,3}[.)])\s+", "", t)], "line_ids": [l["id"]], "box": box})
            prev = l; continue
        if FIELD.match(t):
            flush(); blocks.append({"type": "form-field", "line_ids": [l["id"]], "label": FIELD.match(t).group(1), "text": t, "box": box}); prev = l; continue
        if box and box[1] > 0.8 * page_h and box[3] <= 0.85 * mh and FOOT.match(t):
            flush(); blocks.append({"type": "footnote", "line_ids": [l["id"]], "text": t, "box": box}); prev = l; continue
        # paragraph continuity
        if para and box and para[-1].get("box"):
            pb = para[-1]["box"]
            gap = box[1] - (pb[1] + pb[3])
            if gap > 0.9 * mh or abs(box[0] - pb[0]) > 4 * mh and box[0] > pb[0] + 4 * mh and False:
                flush()
        para.append(l)
        prev = l
    flush()
    return blocks


def _table_block(t, lines):
    rows = []
    for row in t["rows"]:
        cells = []
        for (x, y, w, h) in row:
            ws = [wd for l in lines for wd in l["words"] if wd.get("box")
                  and x <= wd["box"][0] + wd["box"][2] / 2 <= x + w and y <= wd["box"][1] + wd["box"][3] / 2 <= y + h]
            ws.sort(key=lambda wd: (round(wd["box"][1] / max(h / 2, 1)), wd["box"][0]))
            cells.append({"text": " ".join(wd["text"] for wd in ws), "box": [x, y, w, h], "word_ids": [wd["id"] for wd in ws]})
        rows.append(cells)
    ids = [l["id"] for l in lines if l.get("box") and t["box"][0] <= l["box"][0] + l["box"][2] / 2 <= t["box"][0] + t["box"][2]
           and t["box"][1] <= l["box"][1] + l["box"][3] / 2 <= t["box"][1] + t["box"][3]]
    return {"type": "table", "rows": rows, "line_ids": ids, "box": t["box"]}


def _union(boxes):
    if not boxes:
        return None
    x0 = min(b[0] for b in boxes); y0 = min(b[1] for b in boxes)
    x1 = max(b[0] + b[2] for b in boxes); y1 = max(b[1] + b[3] for b in boxes)
    return [x0, y0, x1 - x0, y1 - y0]
