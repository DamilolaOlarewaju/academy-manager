# Implementation plan

## Goal

Build a recruiter-reviewable teaching portal grounded in the workflows of a small coding academy. Demonstrate full-stack request handling, relational modeling, authorization, and testing without invented business metrics.

## First release

1. Define teacher, student, and parent permissions.
2. Build same-origin FastAPI API and SQLite schema.
3. Seed a clearly marked fictional demo.
4. Implement lesson planning, assignment submission, and feedback.
5. Build responsive, keyboard-accessible views with labeled forms.
6. Verify successful workflows and access-control failures.
7. Document setup, architecture, scope, and limitations.
8. Publish as a public `academy-manager` repository under the verified owner's account when repository creation is available.

## Decisions made during implementation

The proposed React/TypeScript/PostgreSQL stack was reduced to a dependency-light JavaScript frontend and SQLite for a smaller runnable first release. This is explicitly disclosed in the README. React/TypeScript and PostgreSQL are possible future upgrades, not completed features.

## Portfolio sequence

After this repository is understood and improved, the next distinct project is a reliable webhook delivery service. A document-grounded AI support desk follows separately and requires an explicit provider/credential decision before API integration. Those projects have not been implemented in this repository.
