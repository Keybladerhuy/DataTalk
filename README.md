# DataTalk

An LLM-powered natural language data query tool. Upload a CSV file, then ask questions about your data in plain English.

## Prerequisites

- Python 3.11+
- Node.js 20+
- An API key for at least one LLM provider (Anthropic, Google Gemini, or OpenAI)

## Backend Setup

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
```

Configure your LLM provider:

```bash
cp .env.example .env
```

Then edit `backend/.env` to set your provider and API key:

```env
# Choose a provider: anthropic, gemini, or openai
LLM_PROVIDER=anthropic

# Optional: override the default model for your provider
# LLM_MODEL=

# Set the API key for your chosen provider
ANTHROPIC_API_KEY=your-key-here
# GEMINI_API_KEY=your-key-here
# OPENAI_API_KEY=your-key-here
```

| Provider | Default Model | Free Tier? |
|----------|--------------|------------|
| `anthropic` | `claude-sonnet-4-6-20250514` | No |
| `gemini` | `gemini-2.5-flash` | Yes |
| `openai` | `gpt-4o` | No |

To switch providers, change `LLM_PROVIDER` and set the matching API key, then restart the backend.

Start the server:

```bash
uvicorn main:app --reload
```

The API runs at `http://localhost:8000`.

## Frontend Setup

```bash
cd frontend
npm install
npm start
```

The app runs at `http://localhost:4200` and proxies API requests to the backend.

## Running Tests

### Backend (pytest)

```bash
cd backend
python -m pytest -v
```

Runs 14 tests covering upload validation, query execution, retry logic, and sandboxing. All tests use mocked LLM calls — no API key needed.

### Frontend (Playwright e2e)

Make sure the frontend dev server is running first (`npm start`).

```bash
cd frontend
npm run e2e            # headless
npm run e2e:headed     # with visible browser
```

Runs 5 tests checking for console errors, UI rendering, and upload/query flows. Tests that need the backend running will auto-skip if it's not available. See `frontend/e2e/README.md` for details.

## Usage

1. Open `http://localhost:4200`
2. Upload a CSV file
3. Review the column info and 5-row preview
4. Type a question in plain English (e.g., "What is the average price by category?")
5. View the result table
