"""Safe file ingestion: validation, EXIF normalisation, PDF rasterisation. Never trusts client filenames or MIME types."""
from dataclasses import dataclass
from io import BytesIO

import cv2
import numpy as np
from PIL import Image, ImageOps

from . import config

Image.MAX_IMAGE_PIXELS = config.MAX_PIXELS


class IngestError(ValueError):
    pass


@dataclass
class Page:
    bgr: np.ndarray
    native: object = None      # (fitz page, zoom) when a PDF text layer is available
    pdf_page: int = 0


def sniff(data: bytes):
    """Identify type from magic bytes."""
    if data[:5] == b"%PDF-":
        return "pdf"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if data[:3] == b"\xff\xd8\xff":
        return "jpeg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    if data[:2] == b"BM":
        return "bmp"
    if data[:4] in (b"II*\x00", b"MM\x00*"):
        return "tiff"
    return None


def validate(data: bytes, filename: str):
    if not data:
        raise IngestError("The file is empty.")
    if len(data) > config.MAX_UPLOAD_MB * 1024 * 1024:
        raise IngestError(f"File exceeds the {config.MAX_UPLOAD_MB} MB limit.")
    kind = sniff(data)
    if kind is None:
        raise IngestError("Unsupported or corrupted file. Accepted: PNG, JPEG, WebP, BMP, TIFF, PDF.")
    return kind


def _pil_to_bgr(im: Image.Image):
    im = ImageOps.exif_transpose(im)
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
        im = Image.alpha_composite(bg, im)
    im = im.convert("RGB")
    return cv2.cvtColor(np.asarray(im), cv2.COLOR_RGB2BGR)


def load_pages(data: bytes, filename: str, force_ocr=False):
    kind = validate(data, filename)
    if kind == "pdf":
        import pymupdf
        try:
            doc = pymupdf.open(stream=data, filetype="pdf")
        except Exception as e:
            raise IngestError(f"Could not open PDF: {e}")
        if doc.needs_pass:
            raise IngestError("This PDF is password protected.")
        if doc.page_count == 0:
            raise IngestError("The PDF has no pages.")
        if doc.page_count > config.MAX_PDF_PAGES:
            raise IngestError(f"PDF has {doc.page_count} pages; the limit is {config.MAX_PDF_PAGES}.")
        zoom = config.PDF_DPI / 72
        pages = []
        for i, pg in enumerate(doc):
            pix = pg.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False)
            if pix.width * pix.height > config.MAX_PIXELS:
                raise IngestError("A PDF page is too large to render safely.")
            arr = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width, 3)
            pages.append(Page(cv2.cvtColor(arr, cv2.COLOR_RGB2BGR), None if force_ocr else (pg.get_text("words"), zoom), i))
        return pages
    try:
        im = Image.open(BytesIO(data))
        n = getattr(im, "n_frames", 1)
        if n > config.MAX_PDF_PAGES:
            raise IngestError(f"Image has {n} frames; the limit is {config.MAX_PDF_PAGES}.")
        out = []
        for i in range(n):
            im.seek(i)
            im.load()
            out.append(Page(_pil_to_bgr(im.copy()), None, i))
        return out
    except IngestError:
        raise
    except Image.DecompressionBombError:
        raise IngestError("Image dimensions are too large.")
    except Exception as e:
        raise IngestError(f"Could not decode image: {e}")
