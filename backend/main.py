from io import StringIO

import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from llm import generate_query

app = FastAPI(title="DataTalk API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state: single DataFrame at a time
store: dict = {"df": None, "filename": None}


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
    qr = generate_query(request.question, df)
    try:
        result = safe_eval(qr.expression, df)
    except Exception as first_error:
        # Retry once with error feedback
        try:
            retry_qr = generate_query(
                request.question, df, error_context=f"Expression: {qr.expression}\nError: {first_error}"
            )
            qr.expression = retry_qr.expression
            qr.usage.extend(retry_qr.usage)
            result = safe_eval(qr.expression, df)
        except Exception as second_error:
            return {
                "query": qr.expression,
                "result": None,
                "error": f"Query failed after retry: {second_error}",
                "usage": qr.total_usage,
            }

    # Normalize result to list of dicts for JSON response
    if isinstance(result, pd.DataFrame):
        result_data = result.fillna("").to_dict(orient="records")
    elif isinstance(result, pd.Series):
        result_data = result.reset_index().fillna("").to_dict(orient="records")
    else:
        result_data = [{"result": result}]

    return {"query": qr.expression, "result": result_data, "error": None, "usage": qr.total_usage}
