# DataTalk

LLM-powered natural language data query tool. Upload a CSV, ask questions in English, get tabular results.

## Tech Stack

- **Backend**: Python 3.11+, FastAPI, pandas, pydantic-settings
- **Frontend**: Angular 19, standalone components, plain CSS
- **LLM**: Multi-provider — Anthropic, Google Gemini, OpenAI (configurable via `.env`)
- No auth, no Docker

## Project Structure

- `backend/main.py` — FastAPI app (endpoints + sandboxed eval)
- `backend/config.py` — pydantic-settings config (provider, model, API keys)
- `backend/llm.py` — LLM provider dispatch + query generation
- `frontend/src/app/app.component.*` — single Angular component (upload + query + results)

## Dev Commands

```bash
# Backend (port 8000): http://localhost:8000/docs
cd backend && uvicorn main:app --reload

# Frontend (port 4200, proxies API to backend)
cd frontend && npm start
```

Requires `.env` with `LLM_PROVIDER` and the corresponding API key (see `.env.example`)

## Coding Conventions

### Backend
- `main.py` for endpoints, `config.py` for settings, `llm.py` for LLM logic
- Pydantic `BaseModel` for request bodies, `pydantic-settings` for config
- Global `store` dict for in-memory DataFrame state (one CSV at a time)
- `safe_eval()` with restricted `__builtins__` (SAFE_BUILTINS allowlist) — only `df` and `pd` in eval scope

### Frontend
- Standalone components (no NgModules)
- `@if` / `@for` control flow (not `*ngIf` / `*ngFor`)
- `HttpClient` provided via `provideHttpClient()` in bootstrap
- No service layer — HTTP calls live in the component for now

### LLM Integration
- Multi-provider: Anthropic, Google Gemini, OpenAI — configured via `LLM_PROVIDER` in `.env`
- Provider dispatch in `llm.py` — each provider has a `_call_*` function, routed by `call_llm()`
- DataFrame schema (column names + dtypes) injected into the system prompt
- LLM returns a bare pandas expression (no markdown, no explanation)
- Expression executed via sandboxed `eval()` against `df`
- On failure: one retry with the error message fed back to the LLM
