import pytest
from httpx import AsyncClient


VALID_CSV = b"name,age,city\nAlice,30,NYC\nBob,25,LA\nCharlie,35,Chicago\nDiana,28,Seattle\nEve,32,Boston"
CSV_WITH_BLANKS = b"name,score,notes\nAlice,90,good\nBob,,\nCharlie,85,ok"


@pytest.mark.anyio
async def test_upload_valid_csv(client: AsyncClient):
    resp = await client.post("/upload", files={"file": ("test.csv", VALID_CSV, "text/csv")})
    assert resp.status_code == 200
    data = resp.json()
    assert data["filename"] == "test.csv"
    assert len(data["columns"]) == 3
    assert data["columns"][0]["name"] == "name"
    assert len(data["preview"]) == 5
    assert data["preview"][0]["name"] == "Alice"


@pytest.mark.anyio
async def test_upload_returns_dtypes(client: AsyncClient):
    resp = await client.post("/upload", files={"file": ("test.csv", VALID_CSV, "text/csv")})
    data = resp.json()
    col_map = {c["name"]: c["dtype"] for c in data["columns"]}
    assert col_map["age"] == "int64"
    assert col_map["name"] in ("object", "str")


@pytest.mark.anyio
async def test_upload_rejects_non_csv(client: AsyncClient):
    resp = await client.post("/upload", files={"file": ("data.txt", b"hello", "text/plain")})
    assert resp.status_code == 400
    assert "CSV" in resp.json()["detail"]


@pytest.mark.anyio
async def test_upload_rejects_malformed_csv(client: AsyncClient):
    bad_csv = b"\x00\x01\x02\xff\xfe"
    resp = await client.post("/upload", files={"file": ("bad.csv", bad_csv, "text/csv")})
    assert resp.status_code == 400
    assert "Failed to parse" in resp.json()["detail"]


@pytest.mark.anyio
async def test_upload_handles_nan_values(client: AsyncClient):
    """NaN values in CSV should become empty strings in the preview (not crash)."""
    resp = await client.post("/upload", files={"file": ("blanks.csv", CSV_WITH_BLANKS, "text/csv")})
    assert resp.status_code == 200
    data = resp.json()
    # Bob's row has blank score and notes
    bob_row = data["preview"][1]
    assert bob_row["name"] == "Bob"
    assert bob_row["score"] == ""
    assert bob_row["notes"] == ""


@pytest.mark.anyio
async def test_upload_replaces_previous(client: AsyncClient):
    """Uploading a second CSV should replace the first."""
    csv1 = b"x\n1\n2"
    csv2 = b"y,z\na,b"
    await client.post("/upload", files={"file": ("first.csv", csv1, "text/csv")})
    resp = await client.post("/upload", files={"file": ("second.csv", csv2, "text/csv")})
    data = resp.json()
    assert data["filename"] == "second.csv"
    assert [c["name"] for c in data["columns"]] == ["y", "z"]
