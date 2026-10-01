# Architecture

The browser loads static HTML, CSS, and JavaScript from FastAPI. A same-origin JSON API handles authentication and learning workflows. SQLite stores relational data on a persistent disk.

## Request boundary

1. The browser sends its HttpOnly session cookie.
2. The server hashes the token and looks up an unexpired session.
3. Mutating requests must also supply the session's CSRF token.
4. Route dependencies check the user's role.
5. The dashboard filters students and submissions using the authenticated user and parent-child links.

Teacher access is academy-wide. Student access covers the student's own submissions. Parents see only linked children's submissions. Lessons and assignments are shared curriculum, visible to all authenticated users.

## Data model

- `users`: name, unique email, role, password hash, salt.
- `children`: explicit parent-to-student relationships.
- `sessions`: hashed bearer token, user, expiry, CSRF token.
- `lessons`: title, summary, academy-local schedule.
- `assignments`: title, instructions, due date.
- `submissions`: assignment/student pair, URL, feedback, nullable score.
- `login_attempts`: hashed address/email key, failure count, expiry.

Foreign keys are enabled per connection. A unique assignment/student constraint makes resubmission an update rather than a duplicate. Writes commit on successful exit and roll back on exceptions. Connections are closed after each unit of work.

## API map

| Method | Path | Access |
| --- | --- | --- |
| POST | /api/login | Public, throttled |
| POST | /api/logout | Authenticated + CSRF |
| GET | /api/config | Public, demo flag only |
| GET | /api/dashboard | Authenticated, filtered by identity |
| POST | /api/lessons | Teacher |
| POST | /api/assignments | Teacher |
| PUT | /api/assignments/{id}/submission | Student, own identity |
| PUT | /api/submissions/{id}/review | Teacher |
| GET | /health | Public database connectivity check |

## Boundaries and next steps

The app intentionally uses one academy, one shared curriculum, and a small dataset. It has no schema migration framework, pagination, session management UI, or granular teacher-to-class allocation. Schedule timestamps represent the academy's local wall time; timezone conversion is not implemented. Add class membership, timezone configuration, migration tooling, and database indexes after measuring usage needs. Move to PostgreSQL before running multiple instances under sustained write traffic.

The login throttle is basic abuse resistance, not a substitute for gateway-level rate limits. Configure trusted proxy handling explicitly when deploying behind a proxy. The browser never fetches submission destinations on the server's behalf.
