"""Job store + background worker pool. Files live under DATA_DIR/jobs/<id>/ and are purged by the retention policy."""
import json
import re
import shutil
import threading
import time
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import cv2

from . import config
from .ingest import load_pages, IngestError
from .pipeline.run import process_page, native_pdf_page, Progress, STAGES

JOBS = config.DATA_DIR / "jobs"
JOBS.mkdir(parents=True, exist_ok=True)
_ID = re.compile(r"^[0-9a-f]{32}$")
_pool = ThreadPoolExecutor(max_workers=config.WORKERS, thread_name_prefix="omniscan")
_lock = threading.Lock()
_cancel = set()


def valid_id(jid):
    return bool(_ID.match(jid or ""))


def jdir(jid):
    if not valid_id(jid):
        raise KeyError(jid)
    return JOBS / jid


def _write(path, obj):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def load_meta(jid):
    p = jdir(jid) / "meta.json"
    if not p.exists():
        raise KeyError(jid)
    return json.loads(p.read_text(encoding="utf-8"))


def save_meta(meta):
    with _lock:
        _write(jdir(meta["id"]) / "meta.json", meta)


def load_result(jid):
    p = jdir(jid) / "result.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def create_job(data: bytes, filename: str, options: dict):
    """Validate synchronously (so the user gets an immediate, clear error) and enqueue."""
    from .ingest import validate
    kind = validate(data, filename)
    jid = uuid.uuid4().hex
    d = jdir(jid)
    d.mkdir(parents=True)
    ext = {"jpeg": "jpg"}.get(kind, kind)
    (d / f"original.{ext}").write_bytes(data)
    safe = re.sub(r"[^\w.\- ()]+", "_", Path(filename or "upload").name)[:120] or "upload"
    meta = {"id": jid, "filename": safe, "kind": kind, "ext": ext, "size": len(data), "created": time.time(), "status": "queued",
            "progress": {"stage": 0, "stage_name": STAGES[0], "pct": 0, "message": "Queued", "page": 0, "pages": 1},
            "options": options, "pages": 0, "error": None, "summary": None, "attempts": 0}
    save_meta(meta)
    _pool.submit(_run, jid)
    return meta


def retry(jid, new_options=None):
    meta = load_meta(jid)
    if meta["status"] in ("queued", "running"):
        raise ValueError("Job is still running.")
    if new_options:
        meta["options"] = {**meta["options"], **new_options}
    meta.update(status="queued", error=None, progress={**meta["progress"], "pct": 0, "message": "Queued"})
    save_meta(meta)
    _pool.submit(_run, jid)
    return meta


def cancel(jid):
    _cancel.add(jid)


def _shift(res, dx, dy):
    def sp(p):
        return [[x + dx, y + dy] for x, y in p] if p else p

    def sb(b):
        return [b[0] + dx, b[1] + dy, b[2], b[3]] if b else b
    for l in res["lines"]:
        l["poly"], l["box"] = sp(l["poly"]), sb(l["box"])
        for w in l["words"]:
            w["poly"], w["box"] = sp(w["poly"]), sb(w["box"])
    for b in res["blocks"]:
        b["box"] = sb(b.get("box"))
        for r in b.get("rows", []):
            for c in r:
                c["box"] = sb(c["box"])


def _run(jid):
    meta = load_meta(jid)
    d = jdir(jid)
    meta["status"] = "running"
    meta["attempts"] += 1
    save_meta(meta)
    last = {"t": 0}

    def cb(p):
        meta["progress"] = p
        if time.time() - last["t"] > 0.4:
            last["t"] = time.time()
            try:
                save_meta(meta)
            except Exception:
                pass
    try:
        data = (d / f"original.{meta['ext']}").read_bytes()
        opts = meta["options"]
        pages = load_pages(data, meta["filename"], force_ocr=bool(opts.get("force_ocr")))
        meta["pages"] = len(pages)
        results = []
        for i, pg in enumerate(pages):
            if jid in _cancel:
                _cancel.discard(jid)
                meta.update(status="cancelled")
                save_meta(meta)
                return
            cv2.imwrite(str(d / f"page-{i + 1}.png"), pg.bgr)
            prog = Progress(cb, i, len(pages))
            if pg.native:
                words, zoom = pg.native
                res = native_pdf_page(words, i + 1, pg.bgr.shape[1], pg.bgr.shape[0], zoom)
            else:
                res = None
            if res is None:
                bgr, dx, dy = pg.bgr, 0, 0
                crop = opts.get("crop")
                if crop and len(pages) == 1:
                    x, y, w, h = [int(v) for v in crop]
                    H, W = bgr.shape[:2]
                    x, y = max(0, min(x, W - 2)), max(0, min(y, H - 2))
                    w, h = max(2, min(w, W - x)), max(2, min(h, H - y))
                    bgr, dx, dy = bgr[y:y + h, x:x + w], x, y
                res = process_page(bgr, i + 1, opts, prog)
                enh = res.pop("_enhanced", None)
                if enh is not None:
                    cv2.imwrite(str(d / f"page-{i + 1}-enhanced.jpg"), enh, [cv2.IMWRITE_JPEG_QUALITY, 88])
                if dx or dy:
                    _shift(res, dx, dy)
                    res["crop"] = [dx, dy, bgr.shape[1], bgr.shape[0]]
                    res["width"], res["height"] = pg.bgr.shape[1], pg.bgr.shape[0]
            results.append(res)
        # preserve manual edits across a retry
        old = load_result(jid)
        if old:
            for o, n in zip(old["pages"], results):
                n["edited_text"] = o.get("edited_text") if o.get("raw_text") == n["raw_text"] else None
        _write(d / "result.json", {"pages": results})
        allw = sum(r["stats"]["words"] for r in results)
        confs = [r["stats"]["mean_conf"] for r in results if r["stats"].get("mean_conf") is not None]
        first = results[0]
        meta["summary"] = {"words": allw, "lines": sum(r["stats"]["lines"] for r in results),
                           "mean_conf": round(sum(confs) / len(confs), 3) if confs else None,
                           "uncertain": sum(r["stats"]["uncertain_words"] for r in results),
                           "language": first["language"]["code"], "language_name": first["language"]["name"],
                           "verification": first["verification"]["level"], "seconds": round(sum(r["stats"].get("seconds", 0) for r in results), 1),
                           "preview": first["raw_text"][:160], "warnings": sum(len(r["warnings"]) for r in results),
                           "empty": allw == 0}
        meta.update(status="done", error=None, progress={"stage": 5, "stage_name": "Done", "pct": 100, "message": "", "page": len(pages), "pages": len(pages)})
    except IngestError as e:
        meta.update(status="failed", error=str(e))
    except Exception as e:
        traceback.print_exc()
        meta.update(status="failed", error=f"Processing failed: {type(e).__name__}: {str(e)[:200]}. You can retry, or retry with a different mode/enhancement.")
    save_meta(meta)


def list_jobs(limit=100):
    out = []
    for p in JOBS.iterdir():
        m = p / "meta.json"
        if m.exists():
            try:
                out.append(json.loads(m.read_text(encoding="utf-8")))
            except Exception:
                pass
    out.sort(key=lambda j: j["created"], reverse=True)
    return out[:limit]


def delete_job(jid):
    d = jdir(jid)
    if d.exists():
        shutil.rmtree(d, ignore_errors=True)


def purge_expired():
    if config.RETENTION_HOURS <= 0:
        return 0
    cutoff = time.time() - config.RETENTION_HOURS * 3600
    n = 0
    for j in list_jobs(10_000):
        if j["created"] < cutoff and j["status"] not in ("queued", "running"):
            delete_job(j["id"])
            n += 1
    tmp = config.DATA_DIR / "_tmp"
    if tmp.exists():
        for f in tmp.iterdir():
            if f.stat().st_mtime < time.time() - 3600:
                f.unlink(missing_ok=True)
    return n


def recover_interrupted():
    """Jobs that were 'running' when the server stopped are marked failed so the user can retry them."""
    for j in list_jobs(10_000):
        if j["status"] in ("queued", "running"):
            j.update(status="failed", error="The server restarted while this job was running. Use Retry.")
            save_meta(j)
