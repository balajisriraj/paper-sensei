import json

import pytest
from fastapi.testclient import TestClient

from papersensei.api import create_app
from papersensei.config import ROOT


@pytest.fixture
def client(settings, service):
    with TestClient(create_app(settings, service)) as c:
        yield c


def sse(body: str) -> list[dict]:
    return [json.loads(line[5:]) for line in body.splitlines() if line.startswith("data:")]


def build(client, **kw) -> str:
    res = client.post("/api/papers/sample", json={"level": "beginner", **kw})
    assert res.status_code == 201
    paper_id = res.json()["id"]
    events = sse(client.get(f"/api/papers/{paper_id}/events").text)
    assert events[-1]["type"] == "done"
    return paper_id


def test_sample_builds_and_persists(client):
    paper_id = build(client)
    paper = client.get(f"/api/papers/{paper_id}").json()
    assert paper["status"] == "ready" and paper["grounding"] == 1.0
    assert len(paper["lessons"]) == len(paper["plan"]["lessons"])
    assert paper["glossary"]
    assert client.get("/api/papers").json()[0]["id"] == paper_id
    assert client.get(f"/api/papers/{paper_id}/pdf").content.startswith(b"%PDF")


def test_upload_and_validation(client):
    pdf = (ROOT / "samples" / "hybrid-retrieval.pdf").read_bytes()
    ok = client.post("/api/papers", files={"file": ("x.pdf", pdf, "application/pdf")}, data={"level": "expert"})
    assert ok.status_code == 201
    bad = client.post("/api/papers", files={"file": ("x.pdf", b"hello", "application/pdf")})
    assert bad.status_code == 422
    assert client.post("/api/papers/arxiv", json={"url": "https://evil.example/abs/1706.03762"}).status_code == 422
    assert client.get("/api/papers/nope").status_code == 404


def test_tutor_streams_verified_citations(client):
    paper_id = build(client)
    res = client.post(f"/api/papers/{paper_id}/ask", json={"question": "How does reciprocal rank fusion merge lists?"})
    events = sse(res.text)
    cites = [e for e in events if e["type"] == "citation"]
    assert cites and all(c["verified"] for c in cites)
    assert events[-1] == {"type": "done", "citations": len(cites), "verified": len(cites)}
    text = "".join(e["text"] for e in events if e["type"] == "text")
    assert text.strip()


def test_rewrite_and_delete(client):
    paper_id = build(client)
    lesson = client.post(f"/api/papers/{paper_id}/lessons/0/rewrite", json={"level": "expert"}).json()
    assert lesson["level"] == "expert"
    assert client.get(f"/api/papers/{paper_id}").json()["lessons"][0]["level"] == "expert"
    assert client.post(f"/api/papers/{paper_id}/lessons/99/rewrite", json={"level": "expert"}).status_code == 404
    assert client.delete(f"/api/papers/{paper_id}").json() == {"deleted": True}
