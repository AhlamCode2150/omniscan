from .rapid import RapidEngine
from .tesseract import TesseractEngine
from .vlm import OllamaVLM, AnthropicVLM

_ENGINES = {e.name: e for e in (RapidEngine(), TesseractEngine(), OllamaVLM(), AnthropicVLM())}


def get(name):
    return _ENGINES[name]


def all_engines():
    return list(_ENGINES.values())


def describe():
    return [e.describe() for e in _ENGINES.values()]
