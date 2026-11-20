# OMNISCAN

Image / PDF → text with confidence, word-level alignment and cross-engine verification. FastAPI + OpenCV backend, Next.js 15 UI.

## Run
```
python -m venv .venv && .venv\Scripts\pip install -r backend\requirements.txt
.venv\Scripts\python backend\scripts\fetch_models.py     # Tesseract language packs (optional)
cd frontend && npm install && cd ..
.\start.ps1                                              # API :8000, UI :3000
```
RapidOCR (PaddleOCR PP-OCRv5) models download on first use. For handwriting/math install Ollama and `ollama pull qwen2.5vl:3b`.

## Pipeline
analysis (resolution, sharpness, skew, lighting, noise, page quad) → non-destructive enhancement (perspective, deskew, shadow
flattening, CLAHE, upscale, sharpen; original untouched; all geometry kept in one matrix so boxes map back) → recognition
(PP-OCRv5 per script family; Tesseract as second opinion; VLM for handwriting/math) → verification (word alignment between engines,
conflicts → `alts`, number mismatches, repeats, illegible markers) → structure (rows, columns, headings, lists, checkboxes, ruled tables,
headers/footers) → rule-based cleaning with a change log (no LLM rewriting).

## Honesty rules enforced in code
* Primary engine text is never overwritten; disagreements become alternatives. Raw / Cleaned / User-edited are stored separately.
* `conf` is the engine's own score or `null` (VLMs give none). Never invented, never calibrated.
* `verification.level` is `cross-checked` only if two engines were compared, `native-text` for PDF text layers, otherwise `single-engine`.
* Languages are advertised per engine only when it can run them (`/api/config`).

## Known limitations
* Handwriting relies on a small local VLM (qwen2.5-vl 3B) – CPU only, minutes per page, no word confidence, no independent verification. The
  bundled handwriting fixtures are **font-rendered**, not human handwriting; add real samples to `backend/benchmarks/fixtures/` (+ `.txt`).
* Math: PP-OCR flattens superscripts (`x²`→`x2`). LaTeX only comes from the VLM (academic mode) and is unverified.
* Tables: ruled (gridded) tables only. Borderless tables are returned as rows of text.
* Two-column detection is histogram-based; irregular layouts can misorder lines (flagged when detectable).
* Handwriting-vs-print detection is a heuristic; pick Handwriting mode explicitly for reliable routing.
* Anthropic cloud engine is implemented but untested here (no key); Hindi/Urdu/Arabic via Tesseract are present but benchmarked only for Arabic.

## Tests & benchmark
`pytest backend/tests` (fast unit tests) · `python backend/benchmarks/run_benchmark.py` (CER/WER vs ground truth; results in
`backend/benchmarks/results/`). Regenerate fixtures with `make_fixtures.py`.
