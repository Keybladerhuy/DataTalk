from dataclasses import dataclass, field

import anthropic
import openai
from google import genai
from google.genai import types as genai_types

import pandas as pd

from config import settings


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


@dataclass
class LLMResult:
    text: str
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    def usage_dict(self) -> dict:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
        }


# --- Provider implementations ---


def _call_anthropic(system: str, user_message: str) -> LLMResult:
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    response = client.messages.create(
        model=settings.active_model,
        max_tokens=512,
        system=system,
        messages=[{"role": "user", "content": user_message}],
    )
    return LLMResult(
        text=response.content[0].text.strip(),
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
    )


def _call_gemini(system: str, user_message: str) -> LLMResult:
    client = genai.Client(api_key=settings.gemini_api_key)
    response = client.models.generate_content(
        model=settings.active_model,
        contents=user_message,
        config=genai_types.GenerateContentConfig(
            system_instruction=system,
            max_output_tokens=512,
        ),
    )
    usage = response.usage_metadata
    return LLMResult(
        text=response.text.strip(),
        input_tokens=usage.prompt_token_count if usage else 0,
        output_tokens=usage.candidates_token_count if usage else 0,
    )


def _call_openai(system: str, user_message: str) -> LLMResult:
    client = openai.OpenAI(api_key=settings.openai_api_key)
    response = client.chat.completions.create(
        model=settings.active_model,
        max_tokens=512,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_message},
        ],
    )
    usage = response.usage
    return LLMResult(
        text=response.choices[0].message.content.strip(),
        input_tokens=usage.prompt_tokens if usage else 0,
        output_tokens=usage.completion_tokens if usage else 0,
    )


_PROVIDERS = {
    "anthropic": _call_anthropic,
    "gemini": _call_gemini,
    "openai": _call_openai,
}


def call_llm(system: str, user_message: str) -> LLMResult:
    return _PROVIDERS[settings.llm_provider](system, user_message)


@dataclass
class QueryResult:
    expression: str
    usage: list = field(default_factory=list)

    @property
    def total_usage(self) -> dict:
        total_in = sum(u["input_tokens"] for u in self.usage)
        total_out = sum(u["output_tokens"] for u in self.usage)
        return {
            "input_tokens": total_in,
            "output_tokens": total_out,
            "total_tokens": total_in + total_out,
            "llm_calls": len(self.usage),
        }


def generate_query(question: str, df: pd.DataFrame, error_context: str | None = None) -> QueryResult:
    schema = build_schema(df)
    system = SYSTEM_PROMPT_TEMPLATE.format(schema=schema)

    user_message = question
    if error_context:
        user_message = (
            f"Previous attempt to answer this question failed with error:\n{error_context}\n\n"
            f"Please try a different approach. Original question: {question}"
        )

    result = call_llm(system, user_message)
    qr = QueryResult(expression=result.text)
    qr.usage.append(result.usage_dict())
    return qr
