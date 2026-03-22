# DataTalk

An LLM-powered natural language data query tool. Upload a CSV file, then ask questions about your data in plain English.

## Prerequisites

- Python 3.11+
- Node.js 20+
- An Anthropic API key

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

Set your API key:

```bash
cp .env.example .env
# Then edit .env and paste your Anthropic API key
```

Or set it manually per session:

```bash
# Windows (PowerShell)
$env:ANTHROPIC_API_KEY="your-key-here"

# macOS/Linux
export ANTHROPIC_API_KEY="your-key-here"
```

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

## Usage

1. Open `http://localhost:4200`
2. Upload a CSV file
3. Review the column info and 5-row preview
4. Type a question in plain English (e.g., "What is the average price by category?")
5. View the result table
