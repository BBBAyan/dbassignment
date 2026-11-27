# CSCI 341 — Assignment 3
**Research Conference and Paper Review Management System** — Python 3.11+, PostgreSQL 16, SQLAlchemy 2.0, Flask 3.1.

This is a study/reference implementation. Review and understand it before submission; team contributions must reflect actual work. UI is deliberately administrative and simple. Authentication and file upload are not implemented because the assignment does not require them. Files are represented as paths, never uploaded.

## Quick start (with Docker and PostgreSQL)

1. Install Docker Desktop and ensure Docker Compose works.
2. In this directory run `docker compose up -d --build`.
3. Once the DB is healthy, run `docker compose exec app python seed.py --reset` (this deletes **all existing** application tables and recreates them).
4. Open **http://localhost:5000** and browse Users, Papers, Reviews, Sessions and Accepted Schedule.
5. Run `docker compose exec app python queries.py > query_results.txt`. This is the Part 2 evidence log, including SQLAlchemy-generated SQL, bound inputs, numbered query results, before/after mutation evidence and transaction rollbacks. **IMPORTANT:** `queries.py` begins with a full seed reset; do not run it on a database containing work you want to keep.
6. Export the required *plain SQL* file (includes actual data and database view):
   `docker compose exec -T db pg_dump -U conference -d conference_db --no-owner --no-privileges --inserts --clean --if-exists > schema_and_seed.sql`
7. Verify the export: create a separate empty PostgreSQL database and restore with `psql -v ON_ERROR_STOP=1 -U conference -d <new_db_name> -f schema_and_seed.sql`, then check record counts and the view. Do not restore over the database currently in use.

## Native install (no Docker)

Create an empty PostgreSQL database and user with permission to create tables. Set (and **export**) `DATABASE_URL` and `SECRET_KEY` into your shell (Python does not auto-read `.env`). Use:

```bash
python -m venv .venv
# Activate virtualenv (Windows: .venv\\Scripts\\activate; macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
# PowerShell example:
# $env:DATABASE_URL="postgresql+psycopg2://conference:conference@localhost:5432/conference_db"
python seed.py --reset
python queries.py > query_results.txt
python app.py
# Note: HTML files must live in a `templates/` folder next to app.py (Flask requirement).
```

`seed.py --reset` is deliberately destructive; it ensures a repeatable original dataset. The `queries.py` script calls the same reset itself. **Never** run these commands against a deployed database with user-entered records.

## Schema: keys and references

All identifiers are integers, with PK as specified. All FKs and CHECKs are in `models.py`.

| Table | Primary key | Important references / constraints |
|---|---|---|
| app_user | user_id | email UNIQUE, non-null profile fields |
| author | author_id | FK app_user, ON DELETE CASCADE |
| author_research_area | (author_id, area_label) | FK author, ON DELETE CASCADE |
| reviewer | reviewer_id | FK app_user, experience >= 0 |
| reviewer_expertise | (reviewer_id, area_label) | FK reviewer, ON DELETE CASCADE |
| conference | conference_id | end_date >= start_date |
| conference_host | (conference_id, host_name) | FK conference, ON DELETE CASCADE |
| conference_reviewer | (conference_id, reviewer_id) | FK conference / reviewer |
| track | track_id | FK conference; coordinator_id FK reviewer |
| conference_session | session_id | FK conference; chair_id FK reviewer; end > start |
| paper | paper_id | FK track; nullable session FK; enumerated status CHECK |
| paper_keyword | (paper_id, keyword) | FK paper, ON DELETE CASCADE |
| paper_author | (paper_id, author_id) | FK paper/author; unique paper+position; positive position |
| paper_version | (paper_id, version_no) | FK paper ON DELETE CASCADE; positive version number |
| review | review_id | FK paper ON DELETE CASCADE, reviewer; unique paper+reviewer; score 1..5; accept/reject |

`accepted_paper_schedule` is a PostgreSQL VIEW, not a table; the view joins accepted scheduled papers to their track, conference, session, chair and corresponding author. `PAPER.session_id` permits at most one session per paper; null denotes unscheduled. Versions use a composite PK `(paper_id, version_no)`, allow gaps, and highest version is current. Multivalued attributes use join tables, never delimited storage columns. Forms accept comma-separated labels, but values are split and stored relationally.

**Deletion policy:** paper deletion cascades to versions, authorships, keywords and reviews. Author / reviewer / track / conference records referenced by independent records generally reject deletion via foreign keys. User role deletion is blocked by references; no conference removal is available on the site, so conferences cannot delete users. Deleting a session unassigns its papers first. Database-level constraints remain enabled.

## Required checks and optional rules

* **Required**: database PK/FK, NOT NULL, UNIQUE and CHECK constraints; review uniqueness; version identity and cascade; status/recommendation/score/positivity/date validation; `services.validate_self_review` rejects an author reviewing their paper both on review create/update and on paper author changes; `services.validate_assignment` rejects nonaccepted or cross-conference paper sessions on paper save; `services.save_session` rejects conference moves that break existing assignments. All saves and deletes run inside one SQLAlchemy transaction and roll back on validation or integrity failures.
* **Optional rules enforced through web workflows**: every newly saved user is an author, a reviewer or both; papers require at least one author and exactly one corresponding author; duplicate authors/positions disallowed. Paper author/reviewer profiles are managed alongside users, and paper versions / keywords / authorships alongside papers.
* **Optional rules documented but not automatically enforced**: corresponding author presence when someone bypasses the application and inserts raw SQL; chair and coordinator membership in their conference's reviewer pool after changing seed data directly; required child records for conferences and other independent entities. The seed obeys these rules. Direct SQL bypassing the web application can bypass the two required *application* checks, as expressly permitted by the assignment.

## Sample data coverage

12 fictional users (author-only, reviewer-only, both); 12 papers; 14 versions; 16 reviews; three conferences (Astana twice, Prague once); all five paper statuses; mixed authors and multiple versions; empty track 5; conference 3 has no papers; reviewer 10 has no reviews; accepted papers scheduled and unscheduled; empty Astana sessions 4/5; Arman and Amina by exact required emails; Amina corresponding on two withdrawn papers (8, 9); different review counts and averages.

## Part 2 tasks and bound parameters

`queries.py` prints task labels 1–8. It uses PostgreSQL `ILIKE`, `FILTER`, `::numeric` and date arithmetic, so it must run on PostgreSQL, not SQLite. All filtering, joins and aggregates happen in SQL. Independent actions get rolled back; the initial seed is restored by reset and remains unchanged after the query run.

* 3.1 email `arman.armanov@example.com`, phone `+77773414141`.
* 3.2 city branch `Astana` versus all other cities (single conditional UPDATE).
* 4.1 corresponding-author email `amina.aminova@example.com`.
* 4.2 empty sessions and city `Astana`.
* 5.2 pattern `%machine learning%`.
* 5.3 selected paper ID `1` (two versions).
* 5.4 conference ID `1`, expertise label `Databases`, minimum years `3`.
* 8 accepted-papers view is created in `models.create_schema()` and queried live, never materialized.

For demonstration of rule rejection, create a review on paper `4` by reviewer `1` (Arman, who authored it), with score `4` and valid completed-review fields. The UI rejects **self-review**. For invalid scheduling, edit rejected paper `3` and choose session `1` — the UI rejects it. For conference mismatch, edit accepted paper `2` and select session `3` — also rejected.

## Part 3 CRUD details

`/users` handles profile records and role-specific expertise/research areas, `/papers` handles paper fields, author lists, keywords and versions (JSON arrays in the simple form), `/reviews` handles reviews and `/sessions` handles sessions. The list view is READ, form routes CREATE/UPDATE and POST delete is DELETE. Supporting tables are read-only seeded data. The schedule view is accessible at `/schedule`. Application error notifications describe invalid input, foreign keys and business rules. There are intentionally no actual paper uploads or login.

**Operational note:** This is a bare administrative app without authentication because the rubric allows it; do not use it with real personal or sensitive data on a public host.

## Testing and limitations

Test with `pytest -q`; the tests use an in-memory SQLite *test double* for checks; required Part 2 SQL must be independently run against PostgreSQL. The submitted authoring environment could not install dependencies or connect to PostgreSQL, so actual integration results and `pg_dump` output must be generated and verified on your own environment before marking them complete. Test the full user, paper, review and session create/edit/delete flows with PostgreSQL.

## Deployment

Choose a host supporting persistent PostgreSQL (e.g. Render/Railway/another host). Provision a **persistent** PostgreSQL database, set `DATABASE_URL` and a strong `SECRET_KEY`, deploy the source using Dockerfile or `gunicorn app:app --bind 0.0.0.0:$PORT`. In the deployed environment, **once on an empty database**, run `python seed.py --reset`; never run it again after users create data. Confirm public `/health`, `/papers`, `/schedule`, and all four CRUD sections from another browser. Save the exact public URL in `links.txt`. Do **not** treat a local `localhost` link as a deployed URL.

## Final submission checklist

- [ ] Start real PostgreSQL; create/seed and test all constraints.
- [ ] Run numbered query script; retain `query_results.txt` output and capture readable results for the video.
- [ ] Generate **real** `schema_and_seed.sql` via `pg_dump`; test restoration in a fresh database.
- [ ] Deploy with persistent PostgreSQL; open public application URL.
- [ ] Demonstrate successful CRUD and both rejected self-review and invalid scheduling.
- [ ] Record <=10-minute walkthrough of Parts 1, 2, 3; upload to Google Drive and grant link access.
- [ ] Fill in real names, IDs, genuine contributions and any unfinished work in one-page executive summary.
- [ ] Replace placeholders in `links.txt`, check both links with a different browser, and create an appropriately named ZIP.
- [ ] Ensure team registration was submitted by November 15; ask instructor if this was missed.

## Alignment with submitted Assignment 1 and UML feedback

The implementation is based on **Assignment-1_Ayaulym_Lespekova.pdf**, pages 1–2,
with its conceptual USER (total, overlapping AUTHOR/REVIEWER), CONFERENCES,
TRACK, PAPER, REVIEW, PAPER_VERSION, SESSIONS, and their multivalued attributes.
Appendix A of Assignment 3 supplies the equivalent normalized relational representation.
The implementation uses `app_user` for USER, `conference` for CONFERENCES,
`conference_session` for SESSIONS, and `paper_version` for VERSION. This is a
terminology / relational-normalization change, not a change to the domain meaning.

**Instructor feedback applied:**

1. `MAINTAIN POOL` multiplicities are **1..*** reviewers per conference and
   **0..*** conferences per reviewer. This is an M:N association represented by
   `conference_reviewer(conference_id, reviewer_id)` with a composite primary key.
   The seed has multiple reviewers for each conference, reviewers in multiple
   conferences, and a reviewer who need not join every pool. Database FKs enforce
   membership references, but the `1..*` minimum is an optional business rule
   respected by the seed and not automatically enforced on arbitrary SQL inserts.
2. `PAPER` to `REVIEW` is **0..*** reviews per paper, not 0..1. The `review`
   relation has an independent `review_id` PK and a many-to-one `paper_id` FK.
   `UNIQUE (paper_id, reviewer_id)` prevents the *same reviewer* from reviewing
   the same paper twice, **not** multiple different reviewers from doing so.
   Papers 1, 2, 3 and 6 in the seed each have two completed reviews; some papers
   may have zero reviews.

**Other original rules:** a user must have an author and/or reviewer role;
only an author can be linked to a paper; authorship stores positive unique author
positions and exactly one corresponding author per paper in the web workflow;
a reviewer cannot review their own paper; track coordinators and session chairs
must be selected from their conference's reviewer pool (true in seed, not enforced
when modifying supporting tables through raw SQL); paper versions use a composite
`(paper_id,version_no)` PK and highest-number-is-current convention; paper
scheduling is restricted to accepted papers in the same conference.

These clarifications address the instructor's UML corrections, rather than
re-submitting UML diagrams (which Assignment 3 explicitly does not require).
# dbassignment
