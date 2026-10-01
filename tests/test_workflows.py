import pytest
from fastapi.testclient import TestClient

from app import main


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setattr(main, "DEMO", True)
    monkeypatch.setattr(main, "SECURE", False)
    with TestClient(main.app) as c:
        yield c


def login(client, role):
    assert (
        client.post(
            "/api/login",
            json={"email": role + "@demo.test", "password": "demo-learning-2026"},
        ).status_code
        == 200
    )
    csrf = client.get("/api/dashboard").json()["user"]["csrf"]
    client.headers["X-CSRF-Token"] = csrf


def test_authentication_required(client):
    assert client.get("/api/dashboard").status_code == 401
    assert (
        client.post(
            "/api/login", json={"email": "teacher@demo.test", "password": "wrong"}
        ).status_code
        == 401
    )


def test_complete_workflow(client):
    login(client, "teacher")
    a = client.post(
        "/api/assignments",
        json={
            "title": "Test project",
            "instructions": "Share a project",
            "due": "2026-11-01",
        },
    )
    assert a.status_code == 201
    assignment_id = a.json()["id"]
    login(client, "student")
    result = client.put(
        f"/api/assignments/{assignment_id}/submission",
        json={"url": "https://example.com/project"},
    )
    assert result.status_code == 200
    submissions = client.get("/api/dashboard").json()["submissions"]
    submission = next(s for s in submissions if s["assignment_id"] == assignment_id)
    login(client, "teacher")
    assert (
        client.put(
            f"/api/submissions/{submission['id']}/review",
            json={"score": 92, "feedback": "Good validation."},
        ).status_code
        == 200
    )
    login(client, "parent")
    dashboard = client.get("/api/dashboard").json()
    assert (
        next(s for s in dashboard["submissions"] if s["id"] == submission["id"])[
            "score"
        ]
        == 92
    )


def test_parent_cannot_see_other_child(client):
    login(client, "other")
    client.put(
        "/api/assignments/1/submission", json={"url": "https://example.com/private"}
    )
    login(client, "parent")
    data = client.get("/api/dashboard").json()
    assert [s["id"] for s in data["students"]] == [2]
    assert all(s["student_id"] == 2 for s in data["submissions"])
    assert "private" not in str(data)


@pytest.mark.parametrize("role", ["student", "parent"])
def test_non_teacher_cannot_write_teacher_resources(client, role):
    login(client, role)
    assert (
        client.post(
            "/api/lessons",
            json={"title": "x", "summary": "x", "scheduled": "2026-10-01T12:00"},
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/assignments",
            json={"title": "x", "instructions": "x", "due": "2026-10-01"},
        ).status_code
        == 403
    )
    assert (
        client.put(
            "/api/submissions/1/review", json={"score": 100, "feedback": "x"}
        ).status_code
        == 403
    )


def test_parent_cannot_submit(client):
    login(client, "parent")
    assert (
        client.put(
            "/api/assignments/1/submission", json={"url": "https://example.com"}
        ).status_code
        == 403
    )


def test_csrf_and_logout(client):
    login(client, "teacher")
    csrf = client.headers.pop("X-CSRF-Token")
    assert client.post("/api/logout").status_code == 403
    client.headers["X-CSRF-Token"] = csrf
    assert client.post("/api/logout").status_code == 204
    assert client.get("/api/dashboard").status_code == 401


def test_resubmission_clears_old_grade_and_is_unique(client):
    login(client, "student")
    for _ in range(2):
        assert (
            client.put(
                "/api/assignments/2/submission",
                json={"url": "https://example.com/updated"},
            ).status_code
            == 200
        )
    rows = client.get("/api/dashboard").json()["submissions"]
    assert len(rows) == 1
    assert rows[0]["score"] is None and rows[0]["feedback"] == ""


def test_invalid_input_and_missing_resources(client):
    login(client, "student")
    assert (
        client.put(
            "/api/assignments/1/submission", json={"url": "javascript:alert(1)"}
        ).status_code
        == 422
    )
    assert (
        client.put(
            "/api/assignments/999/submission", json={"url": "https://example.com"}
        ).status_code
        == 404
    )
    login(client, "teacher")
    assert (
        client.put(
            "/api/submissions/1/review", json={"score": 101, "feedback": "x"}
        ).status_code
        == 422
    )
    assert (
        client.put(
            "/api/submissions/999/review", json={"score": 80, "feedback": "x"}
        ).status_code
        == 404
    )
    assert (
        client.post(
            "/api/lessons",
            json={"title": "x", "summary": "x", "scheduled": "not a date"},
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/assignments",
            json={"title": "x", "instructions": "x", "due": "tomorrow"},
        ).status_code
        == 422
    )


def test_login_rate_limit(client):
    for _ in range(10):
        assert (
            client.post(
                "/api/login", json={"email": "teacher@demo.test", "password": "wrong"}
            ).status_code
            == 401
        )
    assert (
        client.post(
            "/api/login", json={"email": "teacher@demo.test", "password": "wrong"}
        ).status_code
        == 429
    )


def test_expired_session(client):
    login(client, "teacher")
    with main.database() as db:
        db.execute("UPDATE sessions SET expires=0")
    assert client.get("/api/dashboard").status_code == 401


def test_headers_and_no_password_leak(client):
    login(client, "teacher")
    r = client.get("/api/dashboard")
    assert "password" not in r.text and "salt" not in r.text
    assert r.headers["cache-control"] == "no-store"
    assert "frame-ancestors" in r.headers["content-security-policy"]


def test_demo_disabled_does_not_seed_users(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "DB_PATH", str(tmp_path / "empty.db"))
    monkeypatch.setattr(main, "DEMO", False)
    main.initialize()
    with main.database() as db:
        assert db.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0
