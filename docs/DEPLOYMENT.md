# Deployment

## Local Docker demo

```bash
docker build -t academy-manager .
docker run --rm -p 8000:8000 -e DEMO_MODE=true -e COOKIE_SECURE=false academy-manager
```

This container is ephemeral: stopping it discards its database unless a persistent volume is mounted at `/data`. The process runs as a non-root user. Docker configuration is supplied but must be verified on the target host.

## Public fictional demo

Run a single container behind HTTPS, set `DEMO_MODE=true` and `COOKIE_SECURE=true`, and use an isolated database with fictional content only. Configure a persistent `/data` volume if changes should survive restarts. Public demo users share accounts and can modify the same teaching content. A production-quality public showcase should add per-visitor demo isolation or scheduled demo resets.

## Private pilot

Use a fresh database and `DEMO_MODE=false`. This MVP does not include account provisioning or password recovery; add these before inviting real users. Do not simply disable the demo flag on an existing demo database: demo accounts remain in that database.

No public deployment has been performed as part of the initial source package. Do not add a live-demo badge until a hosted instance is running and verified.

## Environment

| Variable | Default | Meaning |
| --- | --- | --- |
| DEMO_MODE | false | Seed fictional users when the database contains no users; expose demo buttons |
| COOKIE_SECURE | true | Send session cookies only over HTTPS; false only for local HTTP development |
| ACADEMY_DB | academy.db | SQLite file path; container default is /data/academy.db |

`.env.example` is a reference file. Environment variables must be exported or configured in the hosting dashboard; automatic dotenv loading is not implemented.
