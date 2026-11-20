"""Exports: TXT, Markdown, JSON, DOCX. User edits take precedence over generated text for the page they belong to."""
import io
import json
import re

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt


def _page_text(p, variant):
    if p.get("edited_text") is not None:
        return p["edited_text"]
    return p["raw_text"] if variant == "raw" else p["cleaned_text"]


def to_txt(res, variant="cleaned"):
    pages = res["pages"]
    if len(pages) == 1:
        return _page_text(pages[0], variant)
    return "\n\n".join(f"--- Page {p['page']} ---\n\n{_page_text(p, variant)}" for p in pages)


def _md_page(p, variant):
    if p.get("edited_text") is not None or variant == "raw":
        return _page_text(p, variant)
    out = []
    byid = {l["id"]: l for l in p["lines"]}
    for b in p["blocks"]:
        t = b["type"]
        if t == "heading":
            out.append("#" * (b.get("level", 2)) + " " + b["text"])
        elif t == "paragraph":
            from .pipeline.clean import join_paragraph, clean_lines
            cl, _ = clean_lines(b["lines"], rtl=p["language"]["rtl"])
            out.append(join_paragraph(cl, rtl=p["language"]["rtl"])[0])
        elif t == "list":
            out.append("\n".join((f"{i + 1}. " if b.get("ordered") else "- ") + it for i, it in enumerate(b["items"])))
        elif t == "checkbox":
            out.append(f"- [{'x' if b.get('checked') else ' '}] {b['text']}")
        elif t == "table":
            rows = [[c["text"].replace("|", "\\|") for c in r] for r in b["rows"]]
            if rows:
                out.append("| " + " | ".join(rows[0]) + " |\n|" + "---|" * len(rows[0]) + "\n" + "\n".join("| " + " | ".join(r) + " |" for r in rows[1:]))
        elif t == "form-field":
            out.append(f"**{b['label']}:** ______")
        elif t in ("header", "footer", "page-number", "footnote"):
            out.append(f"<!-- {t}: {b['text']} -->")
    if p.get("math") and p["math"].get("latex_from_vlm"):
        out.append("<!-- LaTeX (model-generated, unverified) -->\n" + p["math"]["latex_from_vlm"])
    return "\n\n".join(out)


def to_md(res, variant="cleaned"):
    pages = res["pages"]
    return ("\n\n---\n\n".join(_md_page(p, variant) for p in pages)) + "\n"


def to_json(res, meta):
    doc = {"omniscan_version": "1.0", "file": {k: meta[k] for k in ("id", "filename", "kind", "size", "created")},
           "options": meta["options"],
           "notice": "Confidences are engine-reported scores, not calibrated probabilities. 'verification.level' states how the text was checked.",
           "pages": res["pages"]}
    return json.dumps(doc, ensure_ascii=False, indent=2)


def _set_rtl(par):
    pPr = par._p.get_or_add_pPr()
    bidi = OxmlElement("w:bidi")
    pPr.append(bidi)
    par.alignment = WD_ALIGN_PARAGRAPH.RIGHT


def to_docx(res, meta, variant="cleaned"):
    d = Document()
    d.core_properties.title = meta["filename"]
    for pi, p in enumerate(res["pages"]):
        if pi:
            d.add_page_break()
        rtl = p["language"]["rtl"]
        if p.get("edited_text") is not None or variant == "raw":
            for para in _page_text(p, variant).split("\n"):
                par = d.add_paragraph(para)
                if rtl:
                    _set_rtl(par)
            continue
        for b in p["blocks"]:
            t = b["type"]
            if t == "heading":
                d.add_heading(b["text"], level=min(3, b.get("level", 2)))
            elif t == "paragraph":
                from .pipeline.clean import join_paragraph, clean_lines
                cl, _ = clean_lines(b["lines"], rtl=rtl)
                par = d.add_paragraph(join_paragraph(cl, rtl=rtl)[0])
                if rtl:
                    _set_rtl(par)
            elif t == "list":
                for it in b["items"]:
                    d.add_paragraph(it, style="List Number" if b.get("ordered") else "List Bullet")
            elif t == "checkbox":
                d.add_paragraph(("☑ " if b.get("checked") else "☐ ") + b["text"])
            elif t == "table" and b["rows"]:
                tb = d.add_table(rows=len(b["rows"]), cols=max(len(r) for r in b["rows"]))
                tb.style = "Table Grid"
                for ri, r in enumerate(b["rows"]):
                    for ci, c in enumerate(r):
                        tb.cell(ri, ci).text = c["text"]
            elif t == "form-field":
                d.add_paragraph(f"{b['label']}: ______________")
            elif t in ("header", "footer", "page-number"):
                par = d.add_paragraph(b["text"])
                par.runs[0].italic = True
                par.runs[0].font.size = Pt(8)
            else:
                d.add_paragraph(b.get("text", ""))
        if p.get("math") and p["math"].get("latex_from_vlm"):
            d.add_paragraph("LaTeX (model-generated, unverified):")
            d.add_paragraph(p["math"]["latex_from_vlm"]).runs[0].font.name = "Consolas"
    buf = io.BytesIO()
    d.save(buf)
    return buf.getvalue()
