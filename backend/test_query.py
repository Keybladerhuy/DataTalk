import pytest
from httpx import AsyncClient

from conftest import make_mock_response

VALID_CSV = b"name,age,city\nAlice,30,NYC\nBob,25,LA\nCharlie,35,Chicago"


async def upload_csv(client: AsyncClient, csv_data: bytes = VALID_CSV):
    await client.post("/upload", files={"file": ("test.csv", csv_data, "text/csv")})


@pytest.mark.anyio
async def test_query_no_dataset(client: AsyncClient):
    resp = await client.post("/query", json={"question": "What is the average age?"})
    assert resp.status_code == 400
    assert "No dataset loaded" in resp.json()["detail"]


@pytest.mark.anyio
async def test_query_successful(client: AsyncClient, mock_anthropic):
    await upload_csv(client)
    mock_anthropic.messages.create.return_value = make_mock_response("df['age'].mean()")

    resp = await client.post("/query", json={"question": "What is the average age?"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["error"] is None
    assert data["query"] == "df['age'].mean()"
    assert data["result"] == [{"result": 30.0}]


@pytest.mark.anyio
async def test_query_returns_dataframe(client: AsyncClient, mock_anthropic):
    await upload_csv(client)
    mock_anthropic.messages.create.return_value = make_mock_response(
        "df[['name', 'age']].head(2)"
    )

    resp = await client.post("/query", json={"question": "Show first 2 rows"})
    data = resp.json()
    assert data["error"] is None
    assert len(data["result"]) == 2
    assert data["result"][0]["name"] == "Alice"


@pytest.mark.anyio
async def test_query_retries_on_error(client: AsyncClient, mock_anthropic):
    """First expression fails, second succeeds."""
    await upload_csv(client)
    mock_anthropic.messages.create.side_effect = [
        make_mock_response("df['nonexistent']"),  # will raise KeyError
        make_mock_response("df['age'].mean()"),   # retry succeeds
    ]

    resp = await client.post("/query", json={"question": "Average age?"})
    data = resp.json()
    assert data["error"] is None
    assert data["result"] == [{"result": 30.0}]
    assert mock_anthropic.messages.create.call_count == 2


@pytest.mark.anyio
async def test_query_fails_after_retry(client: AsyncClient, mock_anthropic):
    """Both attempts fail."""
    await upload_csv(client)
    mock_anthropic.messages.create.side_effect = [
        make_mock_response("df['bad1']"),
        make_mock_response("df['bad2']"),
    ]

    resp = await client.post("/query", json={"question": "Something impossible"})
    data = resp.json()
    assert data["error"] is not None
    assert "Query failed after retry" in data["error"]
    assert data["result"] is None


@pytest.mark.anyio
async def test_sandbox_blocks_import(client: AsyncClient, mock_anthropic):
    await upload_csv(client)
    mock_anthropic.messages.create.side_effect = [
        make_mock_response("__import__('os').system('echo pwned')"),
        make_mock_response("__import__('os').listdir('.')"),
    ]

    resp = await client.post("/query", json={"question": "hack me"})
    data = resp.json()
    assert data["error"] is not None


@pytest.mark.anyio
async def test_sandbox_blocks_open(client: AsyncClient, mock_anthropic):
    await upload_csv(client)
    mock_anthropic.messages.create.side_effect = [
        make_mock_response("open('/etc/passwd').read()"),
        make_mock_response("open('test.txt', 'w').write('x')"),
    ]

    resp = await client.post("/query", json={"question": "read a file"})
    data = resp.json()
    assert data["error"] is not None


@pytest.mark.anyio
async def test_query_with_nan_in_result(client: AsyncClient, mock_anthropic):
    """Results containing NaN should be serializable."""
    csv_with_nan = b"name,score\nAlice,90\nBob,\nCharlie,85"
    await upload_csv(client, csv_with_nan)
    mock_anthropic.messages.create.return_value = make_mock_response("df")

    resp = await client.post("/query", json={"question": "Show all data"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["error"] is None
    assert data["result"][1]["score"] == ""
