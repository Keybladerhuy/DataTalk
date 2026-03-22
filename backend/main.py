from io import StringIO

from dotenv import load_dotenv

load_dotenv()

import anthropic
import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="DataTalk API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state: single DataFrame at a time
store: dict = {"df": None, "filename": None}

client = anthropic.Anthropic()  # uses ANTHROPIC_API_KEY env var


class QueryRequest(BaseModel):
    question: str


# --- Sandboxed eval helpers ---

SAFE_BUILTINS = {
    "True": True,
    "False": False,
    "None": None,
    "abs": abs,
    "all": all,
    "any": any,
    "bool": bool,
    "dict": dict,
    "enumerate": enumerate,
    "float": float,
    "int": int,
    "len": len,
    "list": list,
    "max": max,
    "min": min,
    "range": range,
    "round": round,
    "set": set,
    "sorted": sorted,
    "str": str,
    "sum": sum,
    "tuple": tuple,
    "zip": zip,
}


def safe_eval(expression: str, df: pd.DataFrame):
    """Evaluate a pandas expression with restricted builtins."""
    allowed_globals = {"__builtins__": SAFE_BUILTINS, "df": df, "pd": pd}
    return eval(expression, allowed_globals)


# --- LLM helpers ---

SYSTEM_PROMPT_TEMPLATE = """You are a data analyst assistant. The user has loaded a pandas DataFrame called `df` with the following schema:

{schema}

When the user asks a question, respond with ONLY a single valid Python pandas expression that answers the question. The expression will be evaluated against the variable `df`.

Rules:
- Return ONLY the expression, no explanation, no markdown, no code fences
- The expression must be valid Python that works with pandas
- Use `df` as the DataFrame variable name
- You may use `pd` (pandas) for helper functions like pd.to_datetime()
- Do NOT use import statements, open(), exec(), eval(), or any file/system operations"""


def build_schema(df: pd.DataFrame) -> str:
    lines = []
    for col in df.columns:
        lines.append(f"- {col}: {df[col].dtype}")
    return f"Columns ({len(df.columns)} total):\n" + "\n".join(lines)


def generate_query(question: str, df: pd.DataFrame, error_context: str | None = None) -> str:
    schema = build_schema(df)
    system = SYSTEM_PROMPT_TEMPLATE.format(schema=schema)

    user_message = question
    if error_context:
        user_message = (
            f"Previous attempt to answer this question failed with error:\n{error_context}\n\n"
            f"Please try a different approach. Original question: {question}"
        )

    response = client.messages.create(
        model="claude-sonnet-4-6-20250514",
        max_tokens=512,
        system=system,
        messages=[{"role": "user", "content": user_message}],
    )
    return response.content[0].text.strip()


# --- Endpoints ---


@app.post("/upload")
async def upload_csv(file: UploadFile = File(...)):
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported.")

    contents = await file.read()
    try:
        df = pd.read_csv(StringIO(contents.decode("utf-8")))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse CSV: {e}")

    store["df"] = df
    store["filename"] = file.filename

    columns = [{"name": col, "dtype": str(df[col].dtype)} for col in df.columns]
    preview = df.head(5).fillna("").to_dict(orient="records")

    return {"filename": file.filename, "columns": columns, "preview": preview}


@app.post("/query")
async def query_data(request: QueryRequest):
    df = store.get("df")
    if df is None:
        raise HTTPException(status_code=400, detail="No dataset loaded. Upload a CSV first.")

    # First attempt
    expression = generate_query(request.question, df)
    try:
        result = safe_eval(expression, df)
    except Exception as first_error:
        # Retry once with error feedback
        try:
            expression = generate_query(
                request.question, df, error_context=f"Expression: {expression}\nError: {first_error}"
            )
            result = safe_eval(expression, df)
        except Exception as second_error:
            return {
                "query": expression,
                "result": None,
                "error": f"Query failed after retry: {second_error}",
            }

    # Normalize result to list of dicts for JSON response
    if isinstance(result, pd.DataFrame):
        result_data = result.fillna("").to_dict(orient="records")
    elif isinstance(result, pd.Series):
        result_data = result.reset_index().fillna("").to_dict(orient="records")
    else:
        result_data = [{"result": result}]

    return {"query": expression, "result": result_data, "error": None}
