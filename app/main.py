"""Academy Manager: a same-origin teaching portal with server-side permissions."""

import hashlib
import hmac
import os
import secrets
import sqlite3
import time
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, HttpUrl

ROOT = Path(__file__).parent
DB_PATH = os.getenv("ACADEMY_DB", "academy.db")
DEMO = os.getenv("DEMO_MODE", "false").lower() == "true"
SECURE = os.getenv("COOKIE_SECURE", "true").lower() == "true"


@contextmanager
def database():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    try:
        with db:
            yield db
    finally:
        db.close()


def password_hash(password, salt):
    return hashlib.scrypt(
        password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1
    ).hex()


def initialize():
    with database() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL, role TEXT NOT NULL CHECK(role IN ('teacher','student','parent')), salt TEXT NOT NULL, password TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS children(parent_id INTEGER REFERENCES users(id), student_id INTEGER REFERENCES users(id), PRIMARY KEY(parent_id,student_id));
        CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY, user_id INTEGER REFERENCES users(id), expires REAL NOT NULL, csrf TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS lessons(id INTEGER PRIMARY KEY, title TEXT NOT NULL, summary TEXT NOT NULL, scheduled TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS assignments(id INTEGER PRIMARY KEY, title TEXT NOT NULL, instructions TEXT NOT NULL, due TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS submissions(id INTEGER PRIMARY KEY, assignment_id INTEGER REFERENCES assignments(id), student_id INTEGER REFERENCES users(id), url TEXT NOT NULL, feedback TEXT NOT NULL DEFAULT '', score INTEGER CHECK(score BETWEEN 0 AND 100), UNIQUE(assignment_id,student_id));
        CREATE TABLE IF NOT EXISTS login_attempts(key TEXT PRIMARY KEY, count INTEGER NOT NULL, expires REAL NOT NULL);
        """)
        if DEMO and not db.execute("SELECT 1 FROM users").fetchone():
            for i, name, role in [
                (1, "Alex Morgan", "teacher"),
                (2, "Jamie Morgan", "student"),
                (3, "Robin Morgan", "parent"),
                (4, "Casey Lee", "student"),
            ]:
                salt = secrets.token_hex(16)
                db.execute(
                    "INSERT INTO users VALUES(?,?,?,?,?,?)",
                    (
                        i,
                        name,
                        f"{role if i != 4 else 'other'}@demo.test",
                        role,
                        salt,
                        password_hash("demo-learning-2026", salt),
                    ),
                )
            db.execute("INSERT INTO children VALUES(3,2)")
            db.executemany(
                "INSERT INTO lessons(title,summary,scheduled) VALUES(?,?,?)",
                [
                    (
                        "Python: decisions that matter",
                        "Build a small eligibility checker with if, elif and else.",
                        "2026-10-05T16:00",
                    ),
                    (
                        "From loops to useful tools",
                        "Use loops to turn a repetitive task into a program.",
                        "2026-10-07T16:00",
                    ),
                ],
            )
            db.executemany(
                "INSERT INTO assignments(title,instructions,due) VALUES(?,?,?)",
                [
                    (
                        "Build a mini ATM",
                        "Create balance, deposit and withdrawal commands. Reject invalid amounts. Share your repository URL.",
                        "2026-10-09",
                    ),
                    (
                        "Personal profile page",
                        "Build a responsive page with semantic HTML and accessible form labels.",
                        "2026-10-12",
                    ),
                ],
            )
            db.execute(
                "INSERT INTO submissions(assignment_id,student_id,url,feedback,score) VALUES(2,2,'https://example.com/demo-project','Clear structure. Next, check the keyboard focus styles.',85)"
            )


@asynccontextmanager
async def lifespan(app):
    initialize()
    yield


app = FastAPI(title="Academy Manager API", version="1.0.0", lifespan=lifespan)


@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers.update(
        {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "Referrer-Policy": "same-origin",
            "Cache-Control": "no-store",
        }
    )
    if not request.url.path.startswith("/docs"):
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        )
    return response


def current_user(request: Request):
    token = request.cookies.get("academy_session", "")
    with database() as db:
        row = db.execute(
            "SELECT users.*,sessions.csrf FROM sessions JOIN users ON users.id=sessions.user_id WHERE token=? AND expires>?",
            (hashlib.sha256(token.encode()).hexdigest(), time.time()),
        ).fetchone()
    if not row:
        raise HTTPException(401, "Please sign in.")
    if request.method not in ("GET", "HEAD", "OPTIONS") and not hmac.compare_digest(
        request.headers.get("X-CSRF-Token", ""), row["csrf"]
    ):
        raise HTTPException(403, "Invalid CSRF token.")
    return dict(row)


def teacher(user: Annotated[dict, Depends(current_user)]):
    if user["role"] != "teacher":
        raise HTTPException(403, "Teacher access required.")
    return user


class Login(BaseModel):
    email: str = Field(max_length=200)
    password: str = Field(max_length=200)


@app.post("/api/login")
def login(body: Login, request: Request, response: Response):
    key = hashlib.sha256(
        f"{request.client.host}:{body.email.lower()}".encode()
    ).hexdigest()
    with database() as db:
        db.execute("DELETE FROM login_attempts WHERE expires<?", (time.time(),))
        attempt = db.execute(
            "SELECT count FROM login_attempts WHERE key=?", (key,)
        ).fetchone()
        if attempt and attempt["count"] >= 10:
            raise HTTPException(429, "Too many attempts. Try again in 15 minutes.")
        row = db.execute(
            "SELECT * FROM users WHERE email=?", (body.email.lower(),)
        ).fetchone()
        valid = hmac.compare_digest(
            password_hash(body.password, row["salt"] if row else "00" * 16),
            row["password"] if row else "0" * 128,
        )
        if not row or not valid:
            db.execute(
                "INSERT INTO login_attempts VALUES(?,1,?) ON CONFLICT(key) DO UPDATE SET count=count+1",
                (key, time.time() + 900),
            )
        else:
            db.execute("DELETE FROM login_attempts WHERE key=?", (key,))
            db.execute("DELETE FROM sessions WHERE expires<?", (time.time(),))
            token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
            db.execute(
                "INSERT INTO sessions VALUES(?,?,?,?)",
                (
                    hashlib.sha256(token.encode()).hexdigest(),
                    row["id"],
                    time.time() + 28800,
                    csrf,
                ),
            )
    if not row or not valid:
        raise HTTPException(401, "Incorrect email or password.")
    response.set_cookie(
        "academy_session",
        token,
        httponly=True,
        secure=SECURE,
        samesite="strict",
        max_age=28800,
    )
    return {"csrf": csrf}


@app.post("/api/logout", status_code=204)
def logout(
    request: Request, response: Response, user: Annotated[dict, Depends(current_user)]
):
    with database() as db:
        db.execute(
            "DELETE FROM sessions WHERE token=?",
            (hashlib.sha256(request.cookies["academy_session"].encode()).hexdigest(),),
        )
    response.delete_cookie("academy_session")


@app.get("/api/config")
def config():
    return {"demo": DEMO}


@app.get("/api/dashboard")
def dashboard(user: Annotated[dict, Depends(current_user)]):
    with database() as db:
        if user["role"] == "teacher":
            students = db.execute(
                "SELECT id,name FROM users WHERE role='student'"
            ).fetchall()
        elif user["role"] == "parent":
            students = db.execute(
                "SELECT id,name FROM users JOIN children ON student_id=id WHERE parent_id=?",
                (user["id"],),
            ).fetchall()
        else:
            students = db.execute(
                "SELECT id,name FROM users WHERE id=?", (user["id"],)
            ).fetchall()
        ids = [s["id"] for s in students]
        submissions = db.execute(
            f"SELECT * FROM submissions WHERE student_id IN ({','.join('?' for _ in ids) or 'NULL'})",
            ids,
        ).fetchall()
        return {
            "user": {k: user[k] for k in ["id", "name", "role", "csrf"]},
            "students": [dict(s) for s in students],
            "lessons": [
                dict(r) for r in db.execute("SELECT * FROM lessons ORDER BY scheduled")
            ],
            "assignments": [
                dict(r) for r in db.execute("SELECT * FROM assignments ORDER BY due")
            ],
            "submissions": [dict(r) for r in submissions],
        }


class Lesson(BaseModel):
    title: str = Field(min_length=1, max_length=120, pattern=r".*\S.*")
    summary: str = Field(min_length=1, max_length=2000)
    scheduled: str


class Assignment(BaseModel):
    title: str = Field(min_length=1, max_length=120, pattern=r".*\S.*")
    instructions: str = Field(min_length=1, max_length=4000)
    due: str


@app.post("/api/lessons", status_code=201)
def create_lesson(body: Lesson, user: Annotated[dict, Depends(teacher)]):
    from datetime import datetime

    try:
        datetime.fromisoformat(body.scheduled)
    except ValueError:
        raise HTTPException(422, "Use an ISO date and time.")
    with database() as db:
        cursor = db.execute(
            "INSERT INTO lessons(title,summary,scheduled) VALUES(?,?,?)",
            (body.title, body.summary, body.scheduled),
        )
        return {"id": cursor.lastrowid}


@app.post("/api/assignments", status_code=201)
def create_assignment(body: Assignment, user: Annotated[dict, Depends(teacher)]):
    from datetime import date

    try:
        date.fromisoformat(body.due)
    except ValueError:
        raise HTTPException(422, "Use an ISO date.")
    with database() as db:
        cursor = db.execute(
            "INSERT INTO assignments(title,instructions,due) VALUES(?,?,?)",
            (body.title, body.instructions, body.due),
        )
        return {"id": cursor.lastrowid}


class Submission(BaseModel):
    url: HttpUrl = Field(max_length=2000)


@app.put("/api/assignments/{assignment_id}/submission")
def submit(
    assignment_id: int, body: Submission, user: Annotated[dict, Depends(current_user)]
):
    if user["role"] != "student":
        raise HTTPException(403, "Student access required.")
    with database() as db:
        if not db.execute(
            "SELECT 1 FROM assignments WHERE id=?", (assignment_id,)
        ).fetchone():
            raise HTTPException(404, "Assignment not found.")
        db.execute(
            "INSERT INTO submissions(assignment_id,student_id,url) VALUES(?,?,?) ON CONFLICT(assignment_id,student_id) DO UPDATE SET url=excluded.url, feedback='', score=NULL",
            (assignment_id, user["id"], str(body.url)),
        )
    return {"status": "submitted"}


class Review(BaseModel):
    feedback: str = Field(min_length=1, max_length=4000)
    score: int = Field(ge=0, le=100, strict=True)


@app.put("/api/submissions/{submission_id}/review")
def review(submission_id: int, body: Review, user: Annotated[dict, Depends(teacher)]):
    with database() as db:
        cursor = db.execute(
            "UPDATE submissions SET feedback=?,score=? WHERE id=?",
            (body.feedback, body.score, submission_id),
        )
        if cursor.rowcount == 0:
            raise HTTPException(404, "Submission not found.")
    return {"status": "reviewed"}


@app.get("/health")
def health():
    with database() as db:
        db.execute("SELECT 1")
    return {"status": "ok"}


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")


@app.get("/")
def index():
    return FileResponse(ROOT / "static" / "index.html")
