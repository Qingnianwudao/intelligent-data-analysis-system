from unittest.mock import patch

from fastapi.testclient import TestClient


def test_health(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_login_demo_mode(client: TestClient) -> None:
    r = client.post("/api/auth/login", json={"username": "any", "password": "any"})
    assert r.status_code == 200
    body = r.json()
    assert "access_token" in body
    assert body.get("token_type") == "bearer"


def test_sessions_crud(client: TestClient, auth_headers: dict[str, str]) -> None:
    r = client.post("/api/sessions", json={}, headers=auth_headers)
    assert r.status_code == 201
    sid = r.json()["id"]

    r = client.get("/api/sessions", headers=auth_headers)
    assert r.status_code == 200
    assert any(s["id"] == sid for s in r.json())

    r = client.patch(
        f"/api/sessions/{sid}",
        json={"title": "改名"},
        headers=auth_headers,
    )
    assert r.status_code == 200
    assert r.json()["title"] == "改名"

    r = client.delete(f"/api/sessions/{sid}", headers=auth_headers)
    assert r.status_code == 204

    r = client.get(f"/api/sessions/{sid}/messages", headers=auth_headers)
    assert r.status_code == 404


@patch("app.routers.sessions.run_nl2sql_turn")
def test_post_message_persists(
    mock_turn,
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    mock_turn.return_value = {
        "reply": "汇总完成",
        "sql": "SELECT month, SUM(amount) FROM sales GROUP BY month",
        "data": {"columns": ["month", "total"], "rows": [["2024-01", 120.5]]},
        "meta": {"message_count": 5},
    }
    r = client.post("/api/sessions", json={}, headers=auth_headers)
    sid = r.json()["id"]

    r = client.post(
        f"/api/sessions/{sid}/messages",
        json={"content": "按月汇总销售额"},
        headers=auth_headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["reply"] == "汇总完成"
    assert body["sql"] is not None
    assert body["data"]["columns"] == ["month", "total"]

    r = client.get(f"/api/sessions/{sid}/messages", headers=auth_headers)
    assert r.status_code == 200
    msgs = r.json()
    assert len(msgs) == 2
    assert msgs[0]["role"] == "user"
    assert msgs[1]["role"] == "assistant"
    assert msgs[1]["meta"] is not None
    assert msgs[1]["meta"].get("sql")


@patch("app.routers.sessions.stream_nl2sql_sse")
def test_post_message_stream_persists(
    mock_stream,
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    import json

    final_pack = {
        "reply": "流式结果",
        "sql": "SELECT 1",
        "data": {"columns": ["x"], "rows": [[1]]},
        "meta": {"message_count": 3},
    }
    mock_stream.return_value = iter(
        [f"event: final\ndata: {json.dumps(final_pack, ensure_ascii=False)}\n\n"]
    )
    r = client.post("/api/sessions", json={}, headers=auth_headers)
    sid = r.json()["id"]

    with client.stream(
        "POST",
        f"/api/sessions/{sid}/messages/stream",
        json={"content": "hello"},
        headers=auth_headers,
    ) as resp:
        assert resp.status_code == 200
        _ = b"".join(resp.iter_bytes())

    r = client.get(f"/api/sessions/{sid}/messages", headers=auth_headers)
    msgs = r.json()
    assert len(msgs) == 2
    assert msgs[1]["content"] == "流式结果"
