# Academy Manager

A small teaching portal for **CodeWithDami Academy**: plan lessons, collect project links, give actionable feedback, and let parents follow their child's progress.

**FastAPI · Python · SQLite · JavaScript · Responsive CSS**

This is a working portfolio MVP using fictional demo data. It is not currently a hosted production service and does not claim real-user adoption or measured business impact.

## Why this exists

For a small coding academy, lesson plans, project links, and feedback can end up scattered across chats. Academy Manager puts that workflow in one place, with different access for teachers, students, and parents.

## What works

| Role | Capabilities |
| --- | --- |
| Teacher | Create lessons and assignments; see student submissions; provide feedback and a score |
| Student | Read the learning timeline; submit and replace a project URL; see personal feedback |
| Parent | Read the learning timeline and assignments; see only their linked child's submissions and feedback |

All students share one academy curriculum in this version. Parent filtering is enforced on the server, not just hidden in the interface. Resubmitting a project clears its previous review so an old grade cannot be mistaken for a review of the new version.

## Run locally

Requires Python 3.12 or newer. No API key, paid service, or frontend build tool is needed.

```bash
python -m venv .venv
# macOS / Linux
source .venv/bin/activate
# Windows PowerShell instead: .venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
```

Set the environment variables and start the app:

```bash
# macOS / Linux
DEMO_MODE=true COOKIE_SECURE=false python -m uvicorn app.main:app --reload
```

```powershell
# Windows PowerShell
$env:DEMO_MODE="true"
$env:COOKIE_SECURE="false"
python -m uvicorn app.main:app --reload
```

Open **http://127.0.0.1:8000**. API documentation is at **/docs**.

Choose a demo role on the login page, or use `teacher@demo.test`, `student@demo.test`, or `parent@demo.test` with password `demo-learning-2026`. All names, submissions, and email addresses are fictional. `other@demo.test` is a second student for checking isolation.

Demo changes persist in `academy.db` and are shared by anyone using that instance. To reset a local demo, stop the server and remove only its demo database, then restart. Never use real student information in a public demo.

## A two-minute walkthrough

1. Enter as **Teacher** → **Plan lessons** → create an assignment.
2. Sign out → enter as **Student** → **Projects** → submit a repository URL.
3. Enter as **Teacher** → **Feedback** → add a score and feedback.
4. Enter as **Parent** → **Feedback** → see the child's reviewed work.
5. Sign in as the second student to confirm the first student's work is not returned.

## Tests

```bash
python -m pytest -q
node --check app/static/app.js
```

The API suite covers the complete review workflow, horizontal data isolation, role enforcement, CSRF rejection, session expiry, login throttling, input validation, missing resources, and resubmission behavior. GitHub Actions runs the suite on pushes and pull requests once the repository is published. Node is needed only for the optional JavaScript syntax check.

## Design choices

- **One same-origin application:** avoids a separate frontend deployment and cross-origin cookie configuration.
- **SQLite:** makes the MVP reproducible with a single command and no database account. A busy multi-instance deployment should move to PostgreSQL with migrations.
- **Vanilla JavaScript:** keeps the initial interface dependency-light. This repository demonstrates JavaScript fundamentals; it does not claim React or TypeScript experience.
- **Server-owned identity:** clients cannot select a student ID when submitting work. The session supplies it.
- **Project links:** avoids file-upload storage and scanning requirements. Links are validated as HTTP(S) and are never fetched by the server.

Read [the architecture](docs/ARCHITECTURE.md), [deployment notes](docs/DEPLOYMENT.md), and [the implementation plan](docs/PLAN.md).

## Security and scope

Passwords use scrypt with per-user salts. Random session tokens are stored hashed, expire after eight hours, and use HttpOnly / SameSite cookies. Mutations require a per-session CSRF token. Database writes use parameterized SQL; rendered text is escaped. Login attempts are throttled per source address and email combination.

This is a **single-academy MVP**, not a complete school information system. It has no attendance tracking, payments, email notifications, password recovery, enrollment UI, or per-class curricula. Demo users can change shared fictional content. Set `DEMO_MODE=false` and use a fresh database before any private pilot; changing the flag does not delete existing demo credentials. Real deployments need HTTPS, account provisioning, backups, retention controls, and a security review.

## Authorship

Created for Damilola Olarewaju's portfolio with AI-assisted implementation. The documentation describes the implemented behavior and trade-offs so the project can be studied, modified, and explained accurately.
