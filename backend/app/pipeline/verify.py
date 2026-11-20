"""Verification layer: cross-engine comparison and suspicious-output detection.

Rules of engagement
  * Original engine output is NEVER rewritten here. Disagreements become `alts` + flags.
  * "cross-checked" only means >=2 independent engines were compared. It does not mean correct.
  * Confidence values are whatever the engine reported; they are not calibrated probabilities.
"""
import re
import unicodedata
from difflib import SequenceMatcher

LOW_CONF = 0.60      # below this the word is flagged uncertain (engine-reported score)
REVIEW_CONF = 0.80

_punct = re.compile(r"^[\W_]+|[\W_]+$", re.UNICODE)


def norm(t):
    return _punct.sub("", unicodedata.normalize("NFKC", t)).casefold()


def lev(a, b):
    if a == b:
        return 0
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def _word_list(lines):
    out = []
    for li, l in enumerate(lines):
        for wi, w in enumerate(l["words"]):
            out.append((li, wi, w))
    return out


def add_flag(w, flag):
    if flag not in w["flags"]:
        w["flags"].append(flag)


def confidence_flags(lines, engine_has_conf):
    for l in lines:
        for w in l["words"]:
            c = w.get("conf")
            if c is None:
                continue
            if c < LOW_CONF:
                add_flag(w, "low-confidence")
                w["status"] = "uncertain"
            elif c < REVIEW_CONF:
                add_flag(w, "review")


def sanity_flags(lines):
    """Engine-independent suspicion checks."""
    issues = []
    prev = None
    for li, l in enumerate(lines):
        for wi, w in enumerate(l["words"]):
            t = w["text"]
            core = _punct.sub("", t)
            if "[?]" in t:
                add_flag(w, "illegible")
                w["status"] = "uncertain"
            if t.startswith("~~") and t.endswith("~~") and len(t) > 4:
                add_flag(w, "crossed-out")
            if len(core) >= 4 and re.search(r"[A-Za-z]", core) and re.search(r"\d", core) \
                    and not re.fullmatch(r"(?i)(\d+[a-z]{1,3}|[a-z]{1,3}\d+[a-z]?|\d+[a-z]{0,2}\d*|[0-9a-f]{8,})", core):
                add_flag(w, "mixed-letters-digits")
            if re.search(r"[|¦{}~`^]", core):
                add_flag(w, "suspicious-char")
            if "�" in t:
                add_flag(w, "invalid-char")
            if prev and len(core) >= 3 and norm(t) == norm(prev[2]["text"]) and not re.fullmatch(r"\d+", core):
                add_flag(w, "repeated-word")
                issues.append({"type": "repeated-word", "line": li, "word": wi, "text": t,
                               "detail": "Same word twice in a row – may be a genuine repeat or an engine duplication."})
            prev = (li, wi, w)
    return issues


def cross_check(primary_lines, secondary_lines, secondary_name):
    """Align two engines' word streams; annotate primary words with alternatives where they disagree."""
    issues = []
    a, b = _word_list(primary_lines), _word_list(secondary_lines)
    if not a or not b:
        if a and not b:
            issues.append({"type": "second-engine-empty", "detail": f"{secondary_name} found no text; no cross-check possible."})
        return issues, {"compared_words": 0, "agree": 0, "conflict": 0, "agreement": None}
    ta, tb = [norm(x[2]["text"]) for x in a], [norm(x[2]["text"]) for x in b]
    sm = SequenceMatcher(None, ta, tb, autojunk=False)
    agree = conflict = 0
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            agree += i2 - i1
            for k in range(i1, i2):
                add_flag(a[k][2], "agreed")
        elif tag == "replace":
            n = min(i2 - i1, j2 - j1)
            for k in range(n):
                wa, wb = a[i1 + k][2], b[j1 + k][2]
                conflict += 1
                if lev(norm(wa["text"]), norm(wb["text"])) == 0:
                    continue
                add_flag(wa, "conflict")
                wa["status"] = "uncertain"
                wa["alts"].append({"text": wb["text"], "engine": secondary_name, "conf": wb.get("conf")})
                digits = re.search(r"\d", wa["text"]) or re.search(r"\d", wb["text"])
                if digits:
                    add_flag(wa, "number-mismatch")
                    issues.append({"type": "number-mismatch", "line": a[i1 + k][0], "word": a[i1 + k][1],
                                   "text": wa["text"], "alt": wb["text"],
                                   "detail": f"Engines read this number differently: '{wa['text']}' vs '{wb['text']}'."})
            for k in range(n, i2 - i1):
                add_flag(a[i1 + k][2], "unmatched-in-" + secondary_name)
            if j2 - j1 > i2 - i1:
                issues.append({"type": "possibly-missing-text", "line": b[j1 + n][0] if j1 + n < len(b) else None,
                               "text": " ".join(x[2]["text"] for x in b[j1 + n:j2]),
                               "detail": f"{secondary_name} read extra words here that the primary engine did not."})
        elif tag == "delete":
            for k in range(i1, i2):
                add_flag(a[k][2], "only-in-primary")
        elif tag == "insert":
            issues.append({"type": "possibly-missing-text", "line": b[j1][0],
                           "text": " ".join(x[2]["text"] for x in b[j1:j2]),
                           "detail": f"{secondary_name} read text that the primary engine did not: '{' '.join(x[2]['text'] for x in b[j1:j2])}'"})
    total = max(1, len(a))
    return issues, {"compared_words": len(a), "agree": agree, "conflict": conflict, "agreement": round(agree / total, 3)}


def line_order_issues(lines):
    """Flag reading-order suspicion: a line that jumps far upward relative to its predecessor."""
    issues = []
    for i in range(1, len(lines)):
        p, c = lines[i - 1].get("box"), lines[i].get("box")
        if not p or not c:
            continue
        if c[1] + c[3] < p[1] - 0.5 * p[3] and abs(c[0] - p[0]) < 0.3 * max(p[2], 1):
            issues.append({"type": "reading-order", "line": i,
                           "detail": "Line appears above the previous one in the same column; check paragraph order."})
    return issues
