"""Fast tests (no OCR models needed) for validation, verification, cleaning, structure, exports."""
import io
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import ingest, export  # noqa: E402
from app.languages import guess_language  # noqa: E402
from app.pipeline import verify as V, clean as C, structure as S  # noqa: E402


def W(t, conf=0.95):
    return {"text": t, "conf": conf, "flags": [], "alts": [], "status": "recognized"}


def L(words):
    return {"words": [W(w) if isinstance(w, str) else w for w in words]}


# ---- ingest / security
def test_rejects_non_image():
    with pytest.raises(ingest.IngestError):
        ingest.validate(b"MZ\x90\x00 definitely an exe", "evil.png")


def test_rejects_empty_and_oversize(monkeypatch):
    with pytest.raises(ingest.IngestError):
        ingest.validate(b"", "a.png")
    monkeypatch.setattr(ingest.config, "MAX_UPLOAD_MB", 0)
    with pytest.raises(ingest.IngestError):
        ingest.validate(b"\x89PNG\r\n\x1a\n" + b"0" * 10, "a.png")


def test_png_roundtrip_and_exif_safe():
    import cv2
    ok, buf = cv2.imencode(".png", np.full((40, 60, 3), 255, np.uint8))
    pages = ingest.load_pages(buf.tobytes(), "x.png")
    assert len(pages) == 1 and pages[0].bgr.shape == (40, 60, 3)


def test_pdf_page_limit(monkeypatch):
    import pymupdf
    d = pymupdf.open()
    for _ in range(3):
        d.new_page()
    monkeypatch.setattr(ingest.config, "MAX_PDF_PAGES", 2)
    with pytest.raises(ingest.IngestError):
        ingest.load_pages(d.tobytes(), "x.pdf")


# ---- verification honesty
def test_cross_check_flags_number_mismatch_and_keeps_primary_text():
    a = [L(["Total", "1250.75", "dollars"])]
    b = [L(["Total", "1260.75", "dollars"])]
    issues, stats = V.cross_check(a, b, "tesseract")
    w = a[0]["words"][1]
    assert w["text"] == "1250.75"                      # primary never rewritten
    assert "number-mismatch" in w["flags"] and w["alts"][0]["text"] == "1260.75"
    assert w["status"] == "uncertain" and stats["conflict"] == 1


def test_low_confidence_marked_uncertain():
    lines = [L([W("maybe", 0.31), W("fine", 0.99)])]
    V.confidence_flags(lines, True)
    assert lines[0]["words"][0]["status"] == "uncertain" and lines[0]["words"][1]["status"] == "recognized"


def test_no_confidence_means_no_invented_score():
    lines = [L([W("x", None)])]
    V.confidence_flags(lines, False)
    assert lines[0]["words"][0]["conf"] is None and lines[0]["words"][0]["status"] == "recognized"


def test_illegible_marker_and_repeat():
    lines = [L(["the", "the", "wor[?]"])]
    issues = V.sanity_flags(lines)
    assert "repeated-word" in lines[0]["words"][1]["flags"]
    assert "illegible" in lines[0]["words"][2]["flags"]


# ---- cleaning is deterministic and logged
def test_clean_dehyphenate_and_log():
    out, log = C.clean_lines(["exam-", "ple  text ,", "ﬁne"])
    assert out[2] == "fine" and out[1] == "ple text," and log
    txt, lg = C.join_paragraph(["an exam-", "ple of it"])
    assert txt == "an example of it" and lg


def test_chem_only_real_elements():
    assert C.chem_formulas("H2O and CO2") == [("H2O", "H₂O"), ("CO2", "CO₂")]
    assert C.chem_formulas("XYZ3") == []


def test_unicode_math_to_latex():
    assert C.unicode_math_to_latex("x² ≤ y₁") == r"x^{2} \leq  y_{1}"


# ---- language heuristics
@pytest.mark.parametrize("text,code", [("Die Straße ist heute nicht gesperrt und das ist gut", "de"), ("今日はとても良い天気です", "ja"),
                                       ("Москва является столицей России", "ru"), ("오늘은 날씨가 아주 좋습니다", "ko"), ("القاهرة هي عاصمة مصر", "ar")])
def test_guess_language(text, code):
    assert guess_language(text)[0] == code


# ---- structure
def mk(i, x, y, w, h, t):
    return {"id": f"l{i}", "text": t, "box": [x, y, w, h], "poly": [[x, y], [x + w, y], [x + w, y + h], [x, y + h]], "conf": .9, "words": []}


def test_same_row_detections_are_merged_in_order():
    rows = S.merge_rows([mk(0, 300, 10, 80, 30, "Price"), mk(1, 10, 12, 100, 28, "Item")])
    assert len(rows) == 1 and rows[0]["text"] == "Item Price"
    rows = S.merge_rows([mk(0, 300, 10, 80, 30, "اول"), mk(1, 10, 12, 100, 28, "ثان")], rtl=True)
    assert rows[0]["text"] == "اول ثان"


def test_blocks_heading_list_checkbox():
    lines = [mk(0, 10, 10, 400, 60, "ANNUAL REPORT"), mk(1, 10, 100, 500, 20, "Intro text here."),
             mk(2, 10, 130, 300, 20, "- first"), mk(3, 10, 155, 300, 20, "- second"), mk(4, 10, 190, 300, 20, "[x] agreed")]
    for l in lines:
        l["words"] = []
    b = S.build_blocks(lines, 800, 1000)
    assert [x["type"] for x in b] == ["heading", "paragraph", "list", "checkbox"]
    assert b[2]["items"] == ["first", "second"] and b[3]["checked"] is True


# ---- export
def _res():
    from app.pipeline.run import C as _  # noqa: F401
    page = {"page": 1, "raw_text": "Hello\nWorld", "cleaned_text": "Hello World", "edited_text": None, "language": {"rtl": False},
            "blocks": [{"type": "heading", "level": 1, "text": "Hello", "line_ids": []},
                       {"type": "table", "rows": [[{"text": "a"}, {"text": "b"}], [{"text": "1"}, {"text": "2"}]], "line_ids": []}],
            "lines": [], "math": None}
    return {"pages": [page]}


def test_exports_and_user_edit_precedence():
    r = _res()
    assert export.to_txt(r) == "Hello World"
    md = export.to_md(r)
    assert md.startswith("# Hello") and "| a | b |" in md
    r["pages"][0]["edited_text"] = "my edit"
    assert export.to_txt(r) == "my edit"
    r["pages"][0]["edited_text"] = None
    from docx import Document
    assert Document(io.BytesIO(export.to_docx(r, {"filename": "x.png"}))).tables
