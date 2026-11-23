"""OMNISCAN API (FastAPI). Run:  uvicorn app.main:app --port 8000"""
import asyncio
import hmac
import re
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import BaseModel

from . import config, jobs, export
from .engines import registry
from .ingest import IngestError, validate
from .languages import LANGS, TESS
from .pipeline.run import MODES, STAGES


def _janitor():
    while True:
        try:
            jobs.purge_expired()
        except Exception:
            pass
        time.sleep(900)


@asynccontextmanager
async def lifespan(app):
    jobs.recover_interrupted()
    jobs.purge_expired()
    threading.Thread(target=_janitor, daemon=True).start()
    yield


app = FastAPI(title="OMNISCAN", version="1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=config.CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"])


@app.middleware("http")
async def require_secret(request: Request, call_next):
    """Shared-secret gate: when OMNISCAN_API_SECRET is set, only callers that know it (our Netlify proxy) get in."""
    if config.API_SECRET and request.url.path != "/api/health":
        sent = request.headers.get("x-omniscan-key", "")
        if not hmac.compare_digest(sent.encode(), config.API_SECRET.encode()):
            return JSONResponse({"detail": "Unauthorized"}, status_code=401)
    return await call_next(request)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    resp = await call_next(request)
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["Cache-Control"] = "no-store"
    return resp


def _job(jid):
    if not jobs.valid_id(jid):
        raise HTTPException(404, "Unknown job")
    try:
        return jobs.load_meta(jid)
    except KeyError:
        raise HTTPException(404, "Unknown job")


class Options(BaseModel):
    mode: str = "auto"
    lang: str = "auto"
    enhance: str = "auto"
    cross_check: bool = True
    force_ocr: bool = False
    rotate90: int = 0
    crop: list[float] | None = None


def _clean_opts(o: dict):
    if o.get("mode", "auto") not in MODES:
        raise HTTPException(422, f"mode must be one of {MODES}")
    if o.get("lang", "auto") != "auto" and o["lang"] not in LANGS:
        raise HTTPException(422, f"Unsupported language '{o['lang']}'.")
    if o.get("enhance", "auto") not in ("off", "auto", "aggressive"):
        raise HTTPException(422, "enhance must be off|auto|aggressive")
    return o


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/config")
def get_config():
    engines = registry.describe()
    return {"engines": engines, "modes": MODES, "stages": STAGES, "max_upload_mb": config.MAX_UPLOAD_MB,
            "max_pdf_pages": config.MAX_PDF_PAGES, "retention_hours": config.RETENTION_HOURS,
            "formats": ["PNG", "JPEG", "WebP", "BMP", "TIFF", "PDF"],
            "languages": [{"code": c, "name": v[0], "script": v[1], "rtl": v[2],
                           "rapidocr": True, "tesseract": c in registry.get("tesseract").languages() if registry.get("tesseract").available()[0] else False,
                           "vlm": c in registry.get("ollama-vlm").languages()} for c, v in LANGS.items()],
            "notes": ["Language support is per-engine; only languages marked true for an engine are used with it.",
                      "Confidence values are engine-reported scores, not calibrated probabilities."]}


@app.post("/api/jobs")
async def upload(files: list[UploadFile] = File(...), mode: str = Form("auto"), lang: str = Form("auto"),
                 enhance: str = Form("auto"), cross_check: bool = Form(True), force_ocr: bool = Form(False)):
    if len(files) > 50:
        raise HTTPException(413, "At most 50 files per batch.")
    opts = _clean_opts({"mode": mode, "lang": lang, "enhance": enhance, "cross_check": cross_check, "force_ocr": force_ocr})
    out = []
    for f in files:
        data = await f.read(config.MAX_UPLOAD_MB * 1024 * 1024 + 1)
        try:
            meta = await asyncio.to_thread(jobs.create_job, data, f.filename or "upload", dict(opts))
            out.append({"ok": True, "job": meta})
        except IngestError as e:
            out.append({"ok": False, "filename": f.filename, "error": str(e)})
    if not any(o["ok"] for o in out):
        return JSONResponse({"jobs": out}, status_code=422)
    return {"jobs": out}


@app.get("/api/jobs")
def list_jobs(limit: int = 100):
    return {"jobs": jobs.list_jobs(min(limit, 500))}


@app.get("/api/jobs/{jid}")
def get_job(jid: str):
    meta = _job(jid)
    res = jobs.load_result(jid) if meta["status"] == "done" else None
    return {"job": meta, "result": res}


@app.get("/api/jobs/{jid}/status")
def job_status(jid: str):
    return _job(jid)


@app.get("/api/jobs/{jid}/image/{page}")
def page_image(jid: str, page: int, variant: str = "original"):
    meta = _job(jid)
    d = jobs.jdir(jid)
    name = f"page-{int(page)}-enhanced.jpg" if variant == "enhanced" else f"page-{int(page)}.png"
    p = d / name
    if not p.exists():
        raise HTTPException(404, "Image not available")
    return FileResponse(p)


@app.get("/api/jobs/{jid}/original")
def original_file(jid: str):
    meta = _job(jid)
    p = jobs.jdir(jid) / f"original.{meta['ext']}"
    return FileResponse(p, filename=meta["filename"])


@app.delete("/api/jobs/{jid}")
def delete(jid: str):
    _job(jid)
    jobs.delete_job(jid)
    return {"ok": True}


@app.post("/api/jobs/{jid}/cancel")
def cancel(jid: str):
    _job(jid)
    jobs.cancel(jid)
    return {"ok": True}


class RetryBody(BaseModel):
    mode: str | None = None
    lang: str | None = None
    enhance: str | None = None
    cross_check: bool | None = None
    force_ocr: bool | None = None
    rotate90: int | None = None
    crop: list[float] | None = None
    clear_crop: bool = False


@app.post("/api/jobs/{jid}/retry")
def retry(jid: str, body: RetryBody):
    _job(jid)
    new = {k: v for k, v in body.model_dump().items() if v is not None and k != "clear_crop"}
    if body.clear_crop:
        new["crop"] = None
    _clean_opts({**{"mode": "auto"}, **new})
    try:
        return jobs.retry(jid, new)
    except ValueError as e:
        raise HTTPException(409, str(e))


class EditBody(BaseModel):
    text: str | None


@app.put("/api/jobs/{jid}/pages/{page}/text")
def edit_text(jid: str, page: int, body: EditBody):
    _job(jid)
    res = jobs.load_result(jid)
    if not res or not (1 <= page <= len(res["pages"])):
        raise HTTPException(404, "Page not found")
    if body.text is not None and len(body.text) > 2_000_000:
        raise HTTPException(413, "Text too long")
    res["pages"][page - 1]["edited_text"] = body.text
    jobs._write(jobs.jdir(jid) / "result.json", res)
    return {"ok": True}


@app.get("/api/jobs/{jid}/export")
def do_export(jid: str, format: str = "txt", variant: str = "cleaned"):
    meta = _job(jid)
    res = jobs.load_result(jid)
    if not res:
        raise HTTPException(409, "Nothing to export yet.")
    if variant not in ("raw", "cleaned"):
        raise HTTPException(422, "variant must be raw|cleaned")
    stem = re.sub(r"\.[^.]+$", "", meta["filename"]) or "omniscan"
    if format == "txt":
        body, mt = export.to_txt(res, variant).encode("utf-8"), "text/plain; charset=utf-8"
    elif format == "md":
        body, mt = export.to_md(res, variant).encode("utf-8"), "text/markdown; charset=utf-8"
    elif format == "json":
        body, mt = export.to_json(res, meta).encode("utf-8"), "application/json"
    elif format == "docx":
        body, mt = export.to_docx(res, meta, variant), "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    else:
        raise HTTPException(422, "format must be txt|md|json|docx")
    fn = f"{stem}.{format}"
    return Response(body, media_type=mt, headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(fn)}"})
