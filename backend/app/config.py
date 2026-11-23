"""Central configuration. Everything is overridable via environment variables (see .env.example)."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _env(name, default):
    return os.environ.get(name, default)


DATA_DIR = Path(_env("OMNISCAN_DATA_DIR", str(ROOT / "data")))
MODEL_DIR = Path(_env("OMNISCAN_MODEL_DIR", str(ROOT / "models")))
MAX_UPLOAD_MB = int(_env("OMNISCAN_MAX_UPLOAD_MB", "25"))
MAX_PIXELS = int(_env("OMNISCAN_MAX_PIXELS", str(60_000_000)))   # decompression-bomb guard
MAX_PDF_PAGES = int(_env("OMNISCAN_MAX_PDF_PAGES", "40"))
PDF_DPI = int(_env("OMNISCAN_PDF_DPI", "200"))
OCR_MAX_SIDE = int(_env("OMNISCAN_OCR_MAX_SIDE", "3200"))        # longest side fed to the engines
RETENTION_HOURS = float(_env("OMNISCAN_RETENTION_HOURS", "72"))  # 0 = keep forever
WORKERS = int(_env("OMNISCAN_WORKERS", "2"))
TESSERACT_CMD = _env("TESSERACT_CMD", "")
TESSDATA_DIR = _env("TESSDATA_PREFIX", "")
OLLAMA_URL = _env("OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_VLM_MODEL = _env("OMNISCAN_VLM_MODEL", "qwen2.5vl:3b")
VLM_TIMEOUT_S = int(_env("OMNISCAN_VLM_TIMEOUT", "600"))
ANTHROPIC_API_KEY = _env("ANTHROPIC_API_KEY", "")                # never sent to the browser
ANTHROPIC_MODEL = _env("OMNISCAN_ANTHROPIC_MODEL", "claude-sonnet-5-5")
API_SECRET = _env("OMNISCAN_API_SECRET", "")                    # when set, every /api request must carry it
CORS_ORIGINS = [o for o in _env("OMNISCAN_CORS", "http://localhost:3000,http://127.0.0.1:3000").split(",") if o]
ALLOWED_EXT = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff", ".pdf"}

for d in (DATA_DIR, MODEL_DIR):
    d.mkdir(parents=True, exist_ok=True)
