"""Vision-language engines (handwriting / math / hard images).

Two backends share one interface:
  * OllamaVLM   – local model through Ollama (default qwen2.5-vl). No data leaves the machine.
  * AnthropicVLM – Claude vision through the Anthropic API; key is read server-side from ANTHROPIC_API_KEY.

VLMs return text only (no calibrated per-word confidence, no boxes). We therefore:
  * report conf=None, never an invented score,
  * ask the model to mark unreadable parts with [?] and to NOT guess,
  * let the verification stage align the VLM text with the box-bearing engines.
"""
import base64
import re
import time

import cv2
import httpx

from .base import Engine, EngineResult, ELine, EWord
from .. import config

PROMPT_TEXT = (
    "You are a meticulous transcription system. Transcribe ALL text visible in this image exactly as written, "
    "line by line, preserving line breaks, spelling, punctuation, numbers and the original language/script. "
    "Do NOT correct spelling, do NOT translate, do NOT summarise, do NOT add words. "
    "If a word or character is illegible or you are unsure, write [?] in its place (or word[?] if you have a best guess). "
    "Crossed-out text: wrap it as ~~text~~. Output only the transcription."
)
PROMPT_MATH = (
    "Transcribe all text in this image. Write every mathematical expression, equation or chemical formula as LaTeX "
    "inside $...$ (inline) or $$...$$ (display). Keep ordinary prose as plain text, one line per source line. "
    "Do not solve or simplify anything and do not add content. Use [?] for anything illegible."
)


def _png_b64(bgr, max_side=1600):
    h, w = bgr.shape[:2]
    if max(h, w) > max_side:
        f = max_side / max(h, w)
        bgr = cv2.resize(bgr, None, fx=f, fy=f, interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode(".png", bgr)
    return base64.b64encode(buf.tobytes()).decode()


def _to_result(name, text, t0, langs, extra=None, notes=None):
    text = re.sub(r"^```[a-z]*\n|\n```$", "", text.strip())
    lines = [ELine(l, None, [], []) for l in text.splitlines() if l.strip()]
    for l in lines:
        l.words = [EWord(w, None, [], False) for w in l.text.split()]
    return EngineResult(name, lines, text, langs, time.time() - t0, notes or [], has_boxes=False, has_conf=False,
                        extra=extra or {})


class OllamaVLM(Engine):
    name = "ollama-vlm"
    kind = "vlm"
    label = "Local vision-language model (Ollama)"

    @property
    def model(self):
        return config.OLLAMA_VLM_MODEL

    def available(self):
        try:
            r = httpx.get(f"{config.OLLAMA_URL}/api/tags", timeout=2.5)
            names = [m["name"] for m in r.json().get("models", [])]
        except Exception:
            return False, "Ollama is not running"
        if not any(n == self.model or n.split(":")[0] == self.model.split(":")[0] and n == self.model for n in names):
            return False, f"model '{self.model}' not pulled (run: ollama pull {self.model})"
        return True, ""

    def languages(self):
        return ["en", "de", "fr", "es", "pt", "it", "nl", "tr", "ru", "ar", "hi", "zh", "ja", "ko"]  # model-dependent; not verified per language

    def recognize(self, bgr, langs, opts=None):
        opts = opts or {}
        t0 = time.time()
        prompt = PROMPT_MATH if opts.get("math") else PROMPT_TEXT
        body = {"model": self.model, "stream": False, "keep_alive": "2m",
                "messages": [{"role": "user", "content": prompt, "images": [_png_b64(bgr, opts.get("max_side", 1344))]}],
                "options": {"temperature": 0, "num_predict": 900, "num_ctx": 4096}}
        r = httpx.post(f"{config.OLLAMA_URL}/api/chat", json=body, timeout=config.VLM_TIMEOUT_S)
        r.raise_for_status()
        txt = r.json()["message"]["content"]
        return _to_result(self.name, txt, t0, langs, {"model": self.model, "math": bool(opts.get("math"))})


class AnthropicVLM(Engine):
    name = "anthropic-vlm"
    kind = "vlm"
    label = "Claude vision (Anthropic API)"

    def available(self):
        if not config.ANTHROPIC_API_KEY:
            return False, "ANTHROPIC_API_KEY not set"
        return True, ""

    def languages(self):
        return ["en", "de", "fr", "es", "pt", "it", "nl", "tr", "ru", "ar", "ur", "hi", "zh", "ja", "ko"]

    def recognize(self, bgr, langs, opts=None):
        opts = opts or {}
        t0 = time.time()
        body = {"model": config.ANTHROPIC_MODEL, "max_tokens": 2000, "temperature": 0,
                "messages": [{"role": "user", "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": _png_b64(bgr, 2000)}},
                    {"type": "text", "text": PROMPT_MATH if opts.get("math") else PROMPT_TEXT}]}]}
        r = httpx.post("https://api.anthropic.com/v1/messages", json=body, timeout=120,
                       headers={"x-api-key": config.ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01"})
        r.raise_for_status()
        txt = "".join(b.get("text", "") for b in r.json()["content"])
        return _to_result(self.name, txt, t0, langs, {"model": config.ANTHROPIC_MODEL})
