import pytest
from httpx import AsyncClient

from conftest import make_llm_result

VALID_CSV = b"name,age,city\nAlice,30,NYC\nBob,25,LA\nCharlie,35,Chicago"


async def upload_csv(client: AsyncClient, csv_data: bytes = VALID_CSV):
    await client.post("/upload", files={"file": ("test.csv", csv_data, "text/csv")})


@pytest.mark.anyio
async def test_query_no_dataset(client: AsyncClient):
    resp = await client.post("/query", json={"question": "What is the average age?"})
    assert resp.status_code == 400
    assert "No dataset loaded" in resp.json()["detail"]


@pytest.mark.anyio
async def test_query_successful(client: AsyncClient, mock_llm):
    await upload_csv(client)
    mock_llm.return_value = make_llm_result("df['age'].mean()")

    resp = await client.post("/query", json={"question": "What is the average age?"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["error"] is None
    assert data["query"] == "df['age'].mean()"
    assert data["result"] == [{"result": 30.0}]


@pytest.mark.anyio
async def test_query_returns_usage(client: AsyncClient, mock_llm):
    """Response should include token usage."""
    await upload_csv(client)
    mock_llm.return_value = make_llm_result("df['age'].mean()")

    resp = await client.post("/query", json={"question": "What is the average age?"})
    data = resp.json()
    usage = data["usage"]
    assert usage["input_tokens"] == 10
    assert usage["output_tokens"] == 5
    assert usage["total_tokens"] == 15
    assert usage["llm_calls"] == 1


@pytest.mark.anyio
async def test_query_returns_dataframe(client: AsyncClient, mock_llm):
    await upload_csv(client)
    mock_llm.return_value = make_llm_result("df[['name', 'age']].head(2)")

    resp = await client.post("/query", json={"question": "Show first 2 rows"})
    data = resp.json()
    assert data["error"] is None
    assert len(data["result"]) == 2
    assert data["result"][0]["name"] == "Alice"


@pytest.mark.anyio
async def test_query_retries_on_error(client: AsyncClient, mock_llm):
    """First expression fails, second succeeds."""
    await upload_csv(client)
    mock_llm.side_effect = [
        make_llm_result("df['nonexistent']"),  # will raise KeyError
        make_llm_result("df['age'].mean()"),   # retry succeeds
    ]

    resp = await client.post("/query", json={"question": "Average age?"})
    data = resp.json()
    assert data["error"] is None
    assert data["result"] == [{"result": 30.0}]
    assert mock_llm.call_count == 2
    assert data["usage"]["llm_calls"] == 2
    assert data["usage"]["total_tokens"] == 30  # 15 per call


@pytest.mark.anyio
async def test_query_fails_after_retry(client: AsyncClient, mock_llm):
    """Both attempts fail."""
    await upload_csv(client)
    mock_llm.side_effect = [
        make_llm_result("df['bad1']"),
        make_llm_result("df['bad2']"),
    ]

    resp = await client.post("/query", json={"question": "Something impossible"})
    data = resp.json()
    assert data["error"] is not None
    assert "Query failed after retry" in data["error"]
    assert data["result"] is None
    assert data["usage"]["llm_calls"] == 2


@pytest.mark.anyio
async def test_sandbox_blocks_import(client: AsyncClient, mock_llm):
    await upload_csv(client)
    mock_llm.side_effect = [
        make_llm_result("__import__('os').system('echo pwned')"),
        make_llm_result("__import__('os').listdir('.')"),
    ]

    resp = await client.post("/query", json={"question": "hack me"})
    data = resp.json()
    assert data["error"] is not None


@pytest.mark.anyio
async def test_sandbox_blocks_open(client: AsyncClient, mock_llm):
    await upload_csv(client)
    mock_llm.side_effect = [
        make_llm_result("open('/etc/passwd').read()"),
        make_llm_result("open('test.txt', 'w').write('x')"),
    ]

    resp = await client.post("/query", json={"question": "read a file"})
    data = resp.json()
    assert data["error"] is not None


@pytest.mark.anyio
async def test_query_with_nan_in_result(client: AsyncClient, mock_llm):
    """Results containing NaN should be serializable."""
    csv_with_nan = b"name,score\nAlice,90\nBob,\nCharlie,85"
    await upload_csv(client, csv_with_nan)
    mock_llm.return_value = make_llm_result("df")

    resp = await client.post("/query", json={"question": "Show all data"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["error"] is None
    assert data["result"][1]["score"] == ""
