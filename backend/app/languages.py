"""Language / script registry. A language is only listed for an engine if that engine really supports it."""

# code -> (display name, script, rtl)
LANGS = {
    "en": ("English", "latin", False), "de": ("German", "latin", False), "fr": ("French", "latin", False),
    "es": ("Spanish", "latin", False), "pt": ("Portuguese", "latin", False), "it": ("Italian", "latin", False),
    "nl": ("Dutch", "latin", False), "tr": ("Turkish", "latin", False),
    "ru": ("Russian", "cyrillic", False),
    "ar": ("Arabic", "arabic", True), "ur": ("Urdu", "arabic", True),
    "hi": ("Hindi", "devanagari", False),
    "zh": ("Chinese", "han", False), "ja": ("Japanese", "japanese", False), "ko": ("Korean", "hangul", False),
}
# Tesseract traineddata names
TESS = {"en": "eng", "de": "deu", "fr": "fra", "es": "spa", "pt": "por", "it": "ita", "nl": "nld", "tr": "tur",
        "ru": "rus", "ar": "ara", "ur": "urd", "hi": "hin", "zh": "chi_sim", "ja": "jpn", "ko": "kor"}
# PP-OCRv5 recognizer family (RapidOCR LangRec name) per script
RAPID_REC = {"latin": "LATIN", "cyrillic": "CYRILLIC", "arabic": "ARABIC", "devanagari": "DEVANAGARI",
             "han": "CH", "japanese": "CH", "hangul": "KOREAN"}

STOPWORDS = {
    "en": "the and of to in is that for it with as was on be at by this are from or have an not",
    "de": "der die das und ist nicht ein eine zu mit den von auf für sich dem im es auch wird",
    "fr": "le la les et de des est un une que pour dans qui pas sur au avec ce il être plus",
    "es": "el la los las de que y en un una es por con para no se su al lo como más",
    "pt": "o a os as de que e em um uma é para com não se por mais do da dos",
    "it": "il lo la gli le di che e in un una è per con non si da del della sono",
    "nl": "de het een en van ik te dat die in is niet op zijn met voor aan er maar",
    "tr": "ve bir bu için ile de da çok ne ben gibi daha olarak olan kadar",
}


def is_rtl(code):
    return LANGS.get(code, ("", "", False))[2]


def script_of(ch):
    o = ord(ch)
    if 0x0600 <= o <= 0x06FF or 0x0750 <= o <= 0x077F or 0xFB50 <= o <= 0xFDFF or 0xFE70 <= o <= 0xFEFF: return "arabic"
    if 0x0900 <= o <= 0x097F: return "devanagari"
    if 0x0400 <= o <= 0x04FF: return "cyrillic"
    if 0xAC00 <= o <= 0xD7AF or 0x1100 <= o <= 0x11FF or 0x3130 <= o <= 0x318F: return "hangul"
    if 0x3040 <= o <= 0x30FF: return "kana"
    if 0x4E00 <= o <= 0x9FFF or 0x3400 <= o <= 0x4DBF: return "han"
    if ch.isalpha(): return "latin"
    return None


def script_histogram(text):
    h = {}
    for ch in text:
        s = script_of(ch)
        if s: h[s] = h.get(s, 0) + 1
    return h


def guess_language(text):
    """Heuristic language guess from script + stopwords. Returns (code|None, basis, confidence 0..1)."""
    h = script_histogram(text)
    if not h: return None, "no letters found", 0.0
    total = sum(h.values()); top, n = max(h.items(), key=lambda kv: kv[1])
    share = n / total
    if h.get("kana", 0) > 0 and h.get("kana", 0) + h.get("han", 0) >= 0.8 * total: return "ja", "kana present", 0.9
    if top == "han": return "zh", "Han script", 0.8 * share
    if top == "hangul": return "ko", "Hangul script", share
    if top == "cyrillic": return "ru", "Cyrillic script (assumed Russian; other Cyrillic languages not distinguished)", 0.6 * share
    if top == "devanagari": return "hi", "Devanagari script (assumed Hindi)", 0.6 * share
    if top == "arabic":
        urdu_marks = sum(text.count(c) for c in "ٹڈڑںھےگپچژ")
        return ("ur", "Urdu-specific letters", 0.7) if urdu_marks >= 2 else ("ar", "Arabic script (Urdu/Persian not excluded)", 0.6 * share)
    words = [w.lower().strip(".,;:!?\"'()") for w in text.split()]
    best, bscore = None, 0
    for code, sw in STOPWORDS.items():
        s = len(set(sw.split()) & set(words)) + sum(1 for ch in text if ch in {"de": "äöüß", "fr": "éèêàçù", "es": "ñ¿¡áíóú", "pt": "ãõç", "it": "àèìòù", "tr": "ğışçö", "nl": ""}.get(code, ""))*0.3
        if s > bscore: best, bscore = code, s
    if best is None or bscore < 1: return "en", "Latin script, no distinguishing words (defaulted to English)", 0.3
    return best, f"stopword/diacritic match ({bscore:.1f})", min(0.9, 0.35 + 0.1 * bscore)
