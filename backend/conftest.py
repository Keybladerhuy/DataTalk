from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from main import app, store


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


def make_mock_response(text: str):
    """Create a mock Anthropic API response."""
    content_block = MagicMock()
    content_block.text = text
    response = MagicMock()
    response.content = [content_block]
    return response


@pytest.fixture
def mock_anthropic():
    """Patch the Anthropic client's messages.create method."""
    with patch("main.client") as mock_client:
        yield mock_client
