# Repository Guidelines

## Project Structure & Module Organization

The active implementation is the Python pipeline in `ai-engine/`. `main.py` orchestrates layout analysis, Gemini vision calls, JSON output, and LaTeX/PDF generation. Reusable pipeline components belong in `ai-engine/core/`:

- `layout_analyzer.py` handles DocLayout/YOLO and page or figure extraction.
- `inference.py` owns model/API calls.
- `extractor.py`, `formatter.py`, and `graphic_engine.py` transform extracted content into the expected output.
- `prompts/` contains versioned prompt and LaTeX-rule text; `models/` is local-only for downloaded weights.

`database/init.sql` contains database initialization. `backend/pom.xml` is currently empty, so do not assume a Java backend build exists.

## Build, Test, and Development Commands

Run commands from `ai-engine/` so imports such as `from core...` resolve:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
python core/test_layout.py
```

`main.py` runs the end-to-end digitization flow; update its local `TEST_FILE` before running. `core/test_layout.py` is a manual layout smoke test and also requires its configured input path. No automated test runner or formatter is currently configured.

## Coding Style & Naming Conventions

Use Python with four-space indentation, `snake_case` for functions, variables, and files, and `PascalCase` for classes (for example, `DocLayoutEngine`). Keep orchestration in `main.py`; put reusable logic in the matching `core/` module. Prefer `pathlib.Path` for new path handling, explicit UTF-8 when writing JSON/text, and concise comments only where pipeline stages are non-obvious.

Keep prompt changes deliberate: retain expected JSON keys and the `extest` LaTeX rules unless the matching formatter is updated too.

## Testing Guidelines

Add focused tests alongside the module they exercise, named `test_<feature>.py`. Avoid tests that call paid external APIs; mock `call_ai_vision` and use small local fixtures. Before submitting, run the layout smoke test and verify generated JSON parses and generated LaTeX compiles for a representative document.

## Commit & Pull Request Guidelines

Recent history uses short, imperative updates (for example, `Update readme` and `Debug Incorrect key name`). Prefer a clearer scoped form: `Fix formatter JSON key`. Keep commits single-purpose. PRs should describe the affected pipeline stage, validation performed, required model/API configuration, and include sanitized sample output or screenshots for extraction/LaTeX changes. Never commit API keys, downloaded model weights, PDFs, or generated exam output.
