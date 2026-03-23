import os

# Set dummy API key before importing app (config validates at import time)
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")

from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from llm import LLMResult
from main import app, store


def make_llm_result(text: str) -> LLMResult:
    """Create an LLMResult with dummy token counts for testing."""
    return LLMResult(text=text, input_tokens=10, output_tokens=5)


@pytest.fixture(autouse=True)
def reset_store():
    """Reset global state between tests."""
    store["df"] = None
    store["filename"] = None
    yield
    store["df"] = None
    store["filename"] = None


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.fixture
def mock_llm():
    """Patch the LLM call function (provider-agnostic)."""
    with patch("llm.call_llm") as mock:
        yield mock
