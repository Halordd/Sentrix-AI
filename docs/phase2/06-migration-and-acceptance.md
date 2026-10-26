# SENTRIX — Phase 2 · Migration Plan, Milestones and Acceptance Tests

| | |
|---|---|
| Status | Proposed plan. Phase 2 itself changes no existing file; every step below is for a later, separately approved phase. |
| Goal | Move the system of record from `domain.js`'s in-memory repository to the backend **without breaking the frontend workflow**, the static ACL, or the existing test/browser checks. |
| Related | [01 current state](01-current-state.md) · [02 architecture](02-architecture-and-security.md) · [03 data model](03-data-model.md) · [04 API](04-api-contract.md) · [05 transitions](05-state-transitions.md) · [07 risks](07-risks-assumptions-decisions.md) |

---

## 1. Strategy: additive strangler, no big-bang cutover

```
Phase 2 (now)        docs + contract only; every file hash unchanged; tests 26/27 green
Phase A (M1)         database + migrations + seed, API skeleton; existing app untouched
Phase B (M2)         read API + bootstrap; parity fixtures prove reads match the snapshot
Phase C (M3)         write API + state machines + audit; in-memory app still the default
Phase D (M4)         adapter contracts (scanner/AI/storage), demo scanner + mock inference
Phase E (M5)         frontend adapter + same-origin proxy + explicit repo switch; browser parity
Phase F (M6)         async runs, worker isolation, security hardening, auth
Phase G (M7)         training/evaluation reproducibility, ops docs, cleanup
```

At every phase: the in-memory demo remains runnable (`npm run dev`, `npm test`), and the only
thing that changes for the frontend is an opt-in repository selector.

### 1.1 Ground rules

1. **Additive files only** until Phase E: `backend/`, `docs/`, new tests, new compose files.
   `app.js`, `domain.js`, `server.mjs`, `static.js`, `index.html`, `styles.css`, `README.md`,
   `package.json` and the four existing tests are frozen (hash-checked in 01 §1.1).
2. **ACL unchanged.** `server.mjs`/`static.js` and their 17 tests are not edited; the API is a
   different process and never serves files from the project root. The static ACL keeps its
   `400/403/404/405`, dot-segment and realpath semantics (01 §8).
3. **Frontend workflow unchanged in behaviour**: same views, same toasts, same errors, same
   filters, same no-off-origin guarantee.
4. **One source of truth at a time.** Never dual-write. Phases B–D read from the API only in
   parity tests; the running app still uses memory. Phase E switches the demo to the API behind a
   flag; Phase F makes it the default and removes the seed from `domain.js` only if the team wants
   (the file can keep the seed for offline tests).
5. **Every phase is independently revertible** (§9).

---

## 2. Phased file plan (what gets added when)

| Phase | New files (additive) | Existing files touched |
|---|---|---|
| A/B | `backend/` (app, migrations, tests), `docker-compose.yml`, `.env.example`, seed script | none |
| C | backend services/routers/tests | none |
| D | `backend/app/adapters/**`, adapter conformance tests, `inference/` | none |
| E | `scripts/dev-proxy.mjs`, `repository.js`, `apiRepository.js`, new tests | `app.js` (import + `await repo.ready()`, async handlers), `README.md` (run instructions), `package.json` (dev script) — **only after X-01 approval** |
| F | worker isolation, auth tests, hardening config | `backend/`, compose |
| G | `training/`, notebooks/docs, CI config | new only |

Phase E is the only point that touches the frontend. The exact minimal diff is specified in §5;
it is deliberately separated from Phase 2 because the brief freezes files now, and it is **gated
on X-01 (supervisor approval, currently PENDING)** — 07 §4.2. No approval is implied by this plan.

---

## 3. Demo data migration (seed, not structure)

The demo dataset from 01 §2 loads through a **seed script** (`python -m app.seed_demo`), not through
migrations, so tests can create an empty database and apply fixtures deterministically. The exact,
machine-readable fixture is [`seed-manifest.json`](../../database/seed-manifest.json); §3.4 states its counts and
rules. Order matters to satisfy the foreign keys and the one-production-model rule: users
(**including `user-system` and one ADMIN**) → prompt templates → models/datasets → projects/members
→ targets/attestations → jobs/runs → findings/evidence/status events → analyses (referencing the
already-seeded model and prompt versions) → remediations/verifications → reports/report_finding →
audit.

| Source | Destination | Mapping rules |
|---|---|---|
| `projects[]` | `project` + `project_member` + `app_user` | `owner` name → seeded user; `createdAt` date → `created_on`; `created_at` = `<date>T09:00:00Z`; status casing mapped; each owner gets an `OWNER` membership |
| `targets[]` | `target` + `target_authorization` | `authorized:true` → active attestation (`attested_by` = project owner, `attested_at` = `<date>T09:10:00Z`, statement = form sentence, scope snapshot); `authorized:false` → no attestation (target appears `BLOCKED`); synthetic `created_at` values are fixed literals (manifest §3.4) and are used only for ordering |
| `scans[]` | `scan_job` + `scan_run` | each scan becomes a job with attempt 1; `profile` display → `profile_id`; `Completed` → run `SUCCEEDED` with `started_at = createdAt`, `finished_at = completedAt`; the seed `Running` job gets a run `RUNNING` with `started_at = createdAt`, `worker_id='seed'`, `heartbeat_at=createdAt`, `stats={"seed":true}` and is **excluded from worker lease recovery** (a demo-only concession, D-07); `simulated` becomes `finding.source='DEMO'`/`analysis.simulated=true` |
| `findings[]` | `finding` + `evidence` + `finding_status_event` | `evidence` string → one `TEXT` evidence row (title “Illustrative evidence”); `scanId` → `job_id`; `status` strings → codes; **exactly one creation event per finding** (`null→status`, actor `user-system`); no `scan_observation` rows (demo findings are `source='DEMO'`, `observation_id NULL` — 03 §4.4) |
| `analyses[]` | `analysis` (references seeded model/prompt versions) | “SENTRIX Risk Engine 4.8.2” **resolves the already-seeded model version** (no duplicate rows); `confidence 91` → `0.91`; `latency_ms=420` derived from the model row's `"Sample 420 ms"` display string; `simulated=true`; pins `ptv-risk-1` |
| `remediations[]` | `remediation` + `verification` | `verification:"Verified"` → a `VERIFIED/MANUAL_REVIEW` verification with note “Migrated from prototype demo.” and verifier_id = `user-system`; the seed task has `verification:null`, so **0 verifications** are created. `assignee` → user |
| `reports[]` | `report` + `report_finding` | snapshot rows captured at seed time in `created_at DESC` order, `position = 1..n`. For `report-atlas` the rows are **bola → debug** (bucket belongs to `project-helix`), so `itemCount = 2` |
| `audit[]` | `audit_event` | actor labels preserved: row 1 `Maya Chen`, row 2 `SENTRIX demo service`; `action` prose → stable verb where mappable; `outcome` mapped; `request_id` = `seed` |
| `models`, `datasets` | `model`, `model_version`, `dataset`, `dataset_version` | seeded **before** analyses; display strings → structured metrics (`0.91`, `420 ms` → `inferenceMs`), `labels` → `label_distribution`; `model_version.is_mock=true`; `dataset.license` = `"sample/demo"` (the real dataset/licence choice is X-03); `content_hash` = sha256 of the shipped fixture file |
| prompt templates | `prompt_template`, `prompt_template_version` | one template (`pt-risk`) + one immutable version (`ptv-risk-1`, content hash fixed in the manifest); analyses pin this version (03 C-16) |
| — | `evaluation_run` | **zero rows in the seed**; only `MEASURED` runs exist after M7 (04 §4.12, 06 M7) |

### 3.1 Ordering

Bootstrap and list endpoints order by creation descending. This reproduces today's array order for
projects, findings, remediations and reports. Two cosmetic differences are accepted and documented:

- `scans` seed array is not sorted by `createdAt` (`scan-atlas` 02:20, `scan-helix` 00:12,
  `scan-atlas-running` 03:44); the API returns newest-first, so “Recent scans” order changes.
- audit seed order is preserved by seed `occurred_at` values (no difference in practice).

No automated check depends on either order (browser checks locate rows by text), but the parity
fixture records the expected order explicitly.

### 3.2 Legacy `Resolved` without verification

The prototype lets a user cycle a finding to `Resolved` with no verification. The migration
backfills a synthetic `MANUAL_REVIEW/VERIFIED` verification (`verifier_id = user-system`,
note “Backfilled: resolved without verification in the frontend prototype.”) for every such row, so
the “resolved implies verification” invariant (05 INV-1/INV-6) holds from day one. The audit row
records the backfill so the provenance is visible.

### 3.3 Ids

Seed rows keep today's readable ids (`project-atlas`, `target-atlas-api`, `scan-atlas`,
`finding-bola`, …). Generated rows use prefixed ULIDs. The API treats ids as opaque; no test may
assume the seed format for new records.

### 3.4 Exact seed fixture manifest (deterministic and testable)

The machine-readable manifest is [`seed-manifest.json`](../../database/seed-manifest.json). It is the single
source of truth for M1: the seed script reads it, and `python -m app.seed_demo --verify` compares
the DB to it row-for-row (ids + counts + key fields), failing on any difference. **Expected rows
after a fresh seed: 51.**

| Table | Rows | Fixed ids (manifest) |
|---|---:|---|
| `scan_profile` (reference data from migration) | 3 | `external_attack_surface`, `api_authorization`, `cloud_configuration` |
| `app_user` | 5 | `user-maya`, `user-jon`, `user-priya`, `user-admin` (ADMIN), `user-system` (inactive) |
| `project` | 3 | `project-atlas`, `project-helix`, `project-northstar` |
| `project_member` | 3 | one `OWNER` per project (the seeded owner) |
| `target` | 4 | `target-atlas-api`, `target-atlas-web`, `target-helix-api`, `target-northstar` |
| `target_authorization` | 3 | active for all targets except `target-northstar` |
| `scan_job` | 3 | `scan-atlas`, `scan-helix`, `scan-atlas-running` |
| `scan_run` | 3 | `run-seed-atlas`, `run-seed-helix`, `run-seed-atlas-running` (attempt 1 each) |
| `scan_observation` | **0** | demo findings are `source='DEMO'`, `observation_id NULL` |
| `finding` | 3 | `finding-bola`, `finding-bucket`, `finding-debug` |
| `evidence` | 3 | `evidence-bola`, `evidence-bucket`, `evidence-debug` (`TEXT`, inline) |
| `finding_status_event` | 3 | one creation event per finding (no transition history in the seed) |
| `analysis` | 1 | `analysis-bola` (model `modelversion-risk-4.8.2`, prompt `ptv-risk-1`, `simulated=true`) |
| `prompt_template` / `prompt_template_version` | 1 / 1 | `pt-risk` / `ptv-risk-1` (fixed content hash in the manifest) |
| `model` / `model_version` | 2 / 2 | `model-risk` 4.8.2, `model-evidence` 2.4.1 (both `is_mock=true`, `PRODUCTION`) |
| `dataset` / `dataset_version` | 1 / 1 | `dataset-demo` / `datasetversion-demo-2026.09` (`license='sample/demo'`, fixed `content_hash`) |
| `evaluation_run` | **0** | no simulated measurements in the seed; first run is `MEASURED` in M7 |
| `remediation` | 1 | `task-bola` (`IN_PROGRESS`) |
| `verification` | **0** | the seed task has no verification |
| `report` / `report_finding` | 1 / 2 | `report-atlas`; rows `finding-bola` (position 1), `finding-debug` (position 2) |
| `audit_event` | 2 | `audit-seed-1`, `audit-seed-2` (both labels preserved) |

**Determinism rules**

1. Every id and timestamp is a literal from the manifest; the seed script must not call `now()`,
   `random`, `uuid`, or depend on locale/timezone. `created_at` values are UTC with `Z`.
2. The seed runs in one transaction as an upsert keyed by id; re-running it must not change counts
   (AT-1.8). A content mismatch for an existing fixed id aborts the seed with a diff.
3. `user-system` is inactive, has no password hash, and is never used as a login; `user-admin` is
   the only seeded `ADMIN` and exists so provisioning/membership tests and demos have an admin
   actor. The demo auto-login user is `user-maya` (ANALYST), matching the current UI's “Maya Chen”.
4. Ordering assertions: projects newest `created_on` first; findings `created_at DESC`; scans
   newest-first (which differs from the unsorted in-memory seed array, 06 §3.1); reports/audit as
   seeded.
5. The manifest records the two documented legacy quirks as **expected** rows, not errors:
   `finding-bola` is `CONFIRMED` while `task-bola` is `IN_PROGRESS`; `finding-debug` references
   `scan-atlas` (job target `target-atlas-api`) while its own target is `target-atlas-web`
   (05 §4.4, 01 Q21/Q22).

---

## 4. Parity harness

The migration is proven, not assumed. Three layers:

1. **Repository parity tests** — a **new** `backend/tests/test_parity.py` reuses the five existing
   `tests/domain.test.js` scenarios against a factory that returns either the in-memory repository
   or an API-backed client pointed at a test server (ephemeral Postgres via
   `pytest`/`testcontainers` or a disposable compose DB). The existing Node file stays untouched
   (06 §1.1); only the scenarios are mirrored. Assertions stay the same; ids are read from returns,
   not hard-coded.
2. **Golden fixtures** — capture `snapshot()` for the seed from the in-memory repository
   (`node -e` script) and compare it with the adapter-built snapshot from `GET /bootstrap`
   (after display mapping). Normalize timestamps/ids; assert deep equality of every collection
   and field in 01 §2. This is the strongest guarantee that views do not change.
3. **Browser parity** — the 13 CDP checks from `scripts/browser-check.mjs` run unchanged against
   `http://127.0.0.1:3000` with the API repository selected. The checks assert specific toasts and
   absence of off-origin requests, so they encode the workflow contract (01 §1.2).

Extra assertions beyond the existing suite:

| Area | Assertion |
|---|---|
| CSV | `GET /reports/{id}/export.csv` is byte-identical to `exportReportCsv` output for the same seed (every cell quoted, `\n` line ends, `sentrix-report.csv` filename) |
| Errors | every frozen sentence in 01 §4.1 is returned by the matching API error |
| Statuses | every code maps to the exact current display string through the adapter (03 §3) |
| Nulls/absent | targets without timestamps, empty remediation `dueDate`, `null` analysis — the adapter produces the same object keys as `snapshot()` |
| Ordering | bootstrap order equals the fixture order (§3.1) |
| No extra calls | one browser session makes no request outside the origin; no request to `/api` happens unless the adapter is enabled |

---

## 5. Frontend adapter and traffic path

> **Gate:** this section is a plan only. Phase E must not start until X-01 (frontend-change
> approval) is granted; until then `app.js` stays untouched and M5 is planned only.

### 5.1 The seam

`app.js` imports `createSentrixRepository` from `./domain.js` and calls the 14 methods
synchronously (01 §4). Two facts shape the adapter:

1. **`snapshot()` must stay synchronous** because every render calls it. Solution: the adapter
   fetches `GET /bootstrap` once during module initialization and serves `snapshot()` from a deep
   clone of that cache. ES modules support top-level `await`, so the entry point can wait for the
   cache before the first `render()`.
2. **Mutations must become asynchronous.** Today a handler calls the repository and immediately
   re-renders. The Phase E diff wraps each handler in `async` and awaits the call before closing
   the modal/toasting. Without this, an unhandled promise silently breaks the toast/error flow.
   A synchronous XHR shim is rejected: it blocks the UI, is deprecated, and would make the
   browser check’s “no uncaught errors / no off-origin” guarantees fragile.

### 5.2 Proposed Phase E diff (small and explicit)

| Change | Purpose |
|---|---|
| new `repository.js` | selects `apiRepository` when `?repo=api` or `window.__SENTRIX_REPO__ === "api"`, otherwise the untouched in-memory `domain.js` |
| new `apiRepository.js` | implements the 14 methods over `fetch("/api/v1/…")`, caches bootstrap, maps codes/messages, polls runs |
| `app.js:1` | import from `./repository.js`; `const repo = await createSentrixRepository();` (top-level await) |
| `app.js` handlers (`bind`/`action`/`submit`) | prefix the callbacks with `async`/`await`; wrap `safely` to also catch rejected promises |
| new `scripts/dev-proxy.mjs` | same-origin `/api` routing (02 §6); static server still runs unchanged on `:3001` |
| error/toast mapping | adapter throws `Error(error.message)` so `notify` is unchanged |

### 5.3 Method → endpoint map

| `domain.js` method | Adapter implementation | Notes |
|---|---|---|
| `snapshot()` | cached `GET /bootstrap`, deep clone | refresh on mutation / `If-None-Match` 304 |
| `createProject(input)` | `POST /projects` | `owner` name → `ownerId` via `EP-27 /users` (also in `/bootstrap`) |
| `archiveProject(id)` | `POST /projects/{id}/archive` | idempotent |
| `createTarget(input)` | `POST /projects/{projectId}/targets` | `authorizationConfirmed` → `authorization.confirmed`; `projectId` from the form |
| `createScan(input)` | `POST /scan-jobs` | `profile` display → `profileId`; project derived |
| `runSimulatedScan(id)` | `POST /scan-jobs/{id}/runs` then poll `GET /scan-runs/{runId}` until terminal (150 ms, ≤ 10 s), then refresh cache | must resolve before `render()` to preserve the toast flow |
| `cancelScan(id)` | `POST /scan-jobs/{id}/cancel` | |
| `updateFindingStatus(id, status)` | `POST /findings/{id}/transitions` `{to}` | mapped code; strict backend may 409 (`→ RESOLVED` without verification) — see §5.4 |
| `createAnalysis(id)` | `POST /findings/{id}/analyses` | 200 existing / 201 new both succeed |
| `createRemediation(input)` | `POST /findings/{id}/remediations` | assignee name → `assigneeId`; `""` due date → omitted |
| `verifyRemediation(taskId, "Verified")` | `POST /remediations/{taskId}/verifications` `{outcome:"VERIFIED", method:"MANUAL_REVIEW", notes:"Recorded from demo UI."}` | one call; task completion and finding resolution happen server-side from the verification. EP-46 (independent verification without a task) is defined for future rescan workflows but has no current UI caller. |
| `createReport(input)` | `POST /reports` | |
| `publishReport(id)` | `POST /reports/{id}/publish` | |
| `exportReportCsv(id)` | client-side generation from the cached snapshot (byte-identical algorithm) **or** `GET /reports/{id}/export.csv` | client-side first for parity, server export verified in M5/M6 |

The adapter also uses `GET /me` and `EP-27 /users` for assignee resolution. In strict production mode
the demo `Maya Chen`/`2026-10-25` constants in `app.js:85` are replaced by real users — a Phase E
follow-up, not Phase 2.

### 5.4 Known frontend follow-ups (deferred, tracked)

| Follow-up | Why |
|---|---|
| “Update status” cycle must not offer `→ Resolved` without verification | today it would receive `409 finding.verification_required`; the automated check never clicks it, but a human can |
| Assignee picker instead of the hard-coded `Maya Chen` | tasks are now user references |
| Display model metrics from structured values instead of “Sample …” strings | the seeded mock can keep the strings via the adapter; real models need a display update |
| Optional login screen / user identity | demo mode auto-authenticates (A-04/D-02) |

These are listed so Phase E cannot silently break the workflow; they are not part of Phase 2.

### 5.5 Traffic path

Same-origin only (02 §6): browser → `:3000` proxy → `/api` → FastAPI, everything else → existing
static server on `:3001`. No CORS, no off-origin request, cookies work with `SameSite=Lax`.

---

## 6. Milestones and acceptance tests

Each milestone is independently reviewable. “Exit” means every listed test is green and the
previous milestones’ tests still pass.

### M0 — Contract freeze (this document set)

**Deliverables:** 01–08, `schema.sql`, `seed-manifest.json`, no code.
**Exit:** reviewer confirms every documented field exists in the source; decisions registered with
owners/gates; baseline hashes captured; existing suite re-run (26 pass/1 skip).
**Tests:** AT-0.1 docs’ file/field claims match a fresh repo read; AT-0.2 `npm test` unchanged;
AT-0.3 no existing file hash changed.

### M1 — Database and migrations (smallest implementation milestone)

**Deliverables:** Alembic baseline; `schema.sql` applied; seed script driven by
[`seed-manifest.json`](../../database/seed-manifest.json); least-privilege roles (`sentrix_app`, migration role,
`sentrix_readonly`, `sentrix_eval`); compose `db`; schema-drift check; no API code.
**Exit:** clean database from empty volumes; seed `--verify` diff empty; seed re-run idempotent;
`upgrade head`/`downgrade base` round-trip; the baseline suite is untouched.
**Acceptance tests (all measurable):**

| Id | Test |
|---|---|
| AT-1.1 | `alembic upgrade head` from an empty DB creates exactly **25 tables, 18 enums, 3 append-only triggers** and the indexes named in `schema.sql`; `downgrade base` then `upgrade head` succeeds |
| AT-1.2 | duplicate project name (case-insensitive) → unique violation |
| AT-1.3 | finding referencing a target/job of another project → FK violation (C-02/C-03) |
| AT-1.4 | two active runs for one job → unique violation (C-05) |
| AT-1.5 | second live analysis for one finding → unique violation (C-07) |
| AT-1.6 | `UPDATE`/`DELETE` on `audit_event` and `finding_status_event` → rejected (trigger/privilege) |
| AT-1.7 | evidence without content or storage_uri → CHECK violation; verification without evidence/note → CHECK violation |
| AT-1.8 | **seed manifest equality:** after a fresh seed, `python -m app.seed_demo --verify` reports zero diffs; the DB matches `seed-manifest.json` exactly — 51 rows total, the ids in `ids`, the counts in `counts`, the `keyFields`, the `ordering`, and the three documented exceptions; a second seed run changes no counts (idempotent) |
| AT-1.9 | one production model version per model enforced (`model_version_one_production_uq`) |
| AT-1.10 | prompt-template versioning: duplicate `(template_id, version)` rejected; `content_hash` format enforced; `UPDATE`/`DELETE` on `prompt_template_version` rejected by trigger |
| AT-1.11 | evaluation provenance: a `MEASURED` row without seed/`finished_at`/metrics fails the CHECK; a `SIMULATED` row is allowed but defaults to `data_origin='SIMULATED'` |
| AT-1.12 | concurrency columns exist and move: `scan_job.updated_at` and `target.updated_at` are NOT NULL; a state update changes them; `updated_at` is never NULL |
| AT-1.13 | schema drift: DDL produced by a fresh migration is normalise-equal to `schema.sql` (empty diff) |
| AT-1.14 | least privilege: app role cannot `UPDATE`/`DELETE` audit/status-history/prompt-version rows; the app cannot run DDL; migration role is separate |
| AT-1.15 | the seed contains the forbidden-empty sets: `evaluation_run = 0`, `scan_observation = 0`, and no `password_hash` values |

### M2 — Identity, read API

**Deliverables:** `/bootstrap`, collection/detail reads, `/me`, `/users`, `/scan-profiles`,
`/healthz`, `/readyz`; **authentication surface EP-50/51** (mechanism and demo auto-login remain
pending decisions D-02/X-05; M2 implements the contract behind a feature flag), CSRF token
issuance; pagination/cursor; error envelope; user directory read.
**Exit:** golden fixture equality for all reads; auth/404/403 matrix; CSRF enforced.
**Acceptance tests:**

| Id | Test |
|---|---|
| AT-2.1 | `GET /bootstrap` (adapter-mapped) deep-equals the in-memory seed snapshot, normalized |
| AT-2.2 | collection endpoints reproduce bootstrap items; filters (`projectId`, `status`, `severity`, `q`) match the frontend’s client-side filter semantics |
| AT-2.3 | pagination: default 50, max 200, cursor round-trip, no duplicates/skips |
| AT-2.4 | unauthenticated → 401; non-member → 404; member-read → 200; VIEWER write → 403 |
| AT-2.5 | frozen error sentences for not-found resources (project/scan/finding/remediation/report) |
| AT-2.6 | `ETag`/`If-None-Match` → 304 without body |
| AT-2.7 | models/datasets/evaluations/profiles shapes match 04 §4.12 and §4.14 (bootstrap compatibility fields included, `isMock` on model versions, `dataOrigin` present in every `/evaluations` response) |
| AT-2.8 | `EP-27 /users`: returns only active users, never emails, paged/cursor-stable; the adapter resolves `Maya Chen` → `user-maya` from it; a non-member gets the same directory but no project data |
| AT-2.9 | `EP-50/51`: login returns `204` + session cookie + CSRF token; an unsafe request without/with wrong CSRF → `403 auth.csrf_failed`; logout invalidates the session; **if** demo mode is enabled (pending D-02), auto-login resolves to `user-maya`, otherwise tests authenticate explicitly |
| AT-2.10 | `GET /me` returns platform role and project roles; no password hash, email never appears in user-visible payloads beyond `/me` |

### M3 — Write API, state machines, audit, membership and provisioning

**Deliverables:** EP-30…EP-42, EP-46…EP-48, EP-52, EP-53; transition service; audit writer;
idempotency; optimistic locking (`If-Match` on project/job/finding/remediation); project-membership
management; ADMIN user provisioning/deactivation.
**Exit:** transition matrix complete; invariants hold; every mutation emits its documented audit
event set; provisioning authz and guards hold.
**Acceptance tests:**

| Id | Test |
|---|---|
| AT-3.1 | every (from,to,trigger) in 05 §2.1/§2.2/§4.1 allowed rows: correct status, events, audit, idempotent replay; denied rows: 409/422 and no writes |
| AT-3.2 | target creation without confirmation → 422 with `Explicit authorization confirmation is required before a target can be used.`; with confirmation → attestation row created |
| AT-3.3 | archived project: create target/scan/report → 409 `Select an active project.`; reads still 200 |
| AT-3.4 | `RESOLVED` without verification is impossible: `POST /transitions {to: RESOLVED}` → 409; SQL invariant INV-1/INV-6 holds after a randomized allowed-transition sequence |
| AT-3.5 | remediation created on `RESOLVED`/`FALSE_POSITIVE`/`ACCEPTED_RISK` → 409; on `NEW`/`CONFIRMED`/`REOPENED` → finding `IN_PROGRESS` |
| AT-3.6 | close task (`PATCH …/COMPLETED`) leaves finding status, `updated_at` and `resolved_at` unchanged; zero finding events |
| AT-3.7 | verification `VERIFIED` from `IN_PROGRESS` **and** from `REOPENED` → task `COMPLETED`, finding `RESOLVED`, `resolved_at`, status event with `verification_id`; `REJECTED` from `IN_PROGRESS`/`RESOLVED` → `REOPENED` with event, from `REOPENED` → verification only, no status event; verification against a `CANCELLED` task → 409 |
| AT-3.8 | verification with evidence of another finding → 409; without evidence and without notes → 422 |
| AT-3.9 | `POST /scan-jobs/{id}/runs` on `COMPLETED`/`CANCELLED`/`RUNNING` → 409 with the frozen message; duplicate active run → 409 `Run already in progress.` |
| AT-3.10 | cancel `QUEUED`→`CANCELLED` (run `PENDING`→`CANCELLED`); cancel `RUNNING`→`CANCELLED`; cancel `COMPLETED` → 409 |
| AT-3.11 | analysis idempotency: second request returns the same analysis id with 200; failed analysis allows a retry row |
| AT-3.12 | report: `jobId` from another project → 422; publish twice → 409; published report immutable; snapshot `report_finding` rows fixed after later finding changes |
| AT-3.13 | CSV byte-equality with the in-memory exporter for the seed (01 §5.1) |
| AT-3.14 | each mutation emits exactly the endpoint’s documented audit event set (remediation creation → `remediation.created` + `finding.transitioned`; verification → `verification.recorded` [+ `finding.transitioned` only if the status changes]), each with actor, request id, resource type/id and outcome; denied authz attempts logged with `DENIED` |
| AT-3.15 | `Idempotency-Key` replay returns the original status/body and creates no new rows; concurrent duplicate submissions create one row |
| AT-3.16 | membership (EP-28/29/47/48): OWNER/ADMIN can grant, re-role and remove; duplicate → `409 membership.exists`; demoting/removing the last OWNER → `409 membership.last_owner`; members can read the list, non-members get 404; every change is audited |
| AT-3.17 | user provisioning (EP-52/53): ADMIN creates a user (`201`, unique email); duplicate email → `409 user.email_conflict`; deactivating/demoting the last active ADMIN → `409 user.last_admin`; non-ADMIN → 403; no user deletion endpoint exists; no password hash is ever returned |
| AT-3.18 | optimistic concurrency: stale `If-Match` on job start/cancel, finding transition and remediation update → `409 conflict.stale_resource`; every successful write bumps the resource's `updated_at` (I-13) |

### M4 — Adapter contracts and demo implementations

**Deliverables:** `ScannerPort` + demo adapter; `InferencePort` + mock adapter; `ArtifactStorePort`
filesystem; `ExecutionBackend` subprocess; conformance suites.
**Exit:** demo scan produces the same finding as `runSimulatedScan`; mock analysis matches
`createAnalysis`; adapters replaceable without service changes.
**Acceptance tests:**

| Id | Test |
|---|---|
| AT-4.1 | adapter conformance suite (02 §4.1) passes for the demo adapter and a deliberately broken adapter |
| AT-4.2 | demo run on the seed target creates `Demo configuration exposure`, severity `LOW`, status `NEW`, evidence string containing “No external target was contacted”; exactly one finding per job |
| AT-4.3 | mock analysis: confidence 0.91 for `CRITICAL`, 0.76 otherwise, `simulated=true`, version pinned |
| AT-4.4 | requesting a non-production model version → 422; inference adapter failure → analysis `FAILED`, no fabricated result |
| AT-4.5 | artifact store: put/get by sha256, mismatch rejected, traversal key rejected, oversized artifact rejected |
| AT-4.6 | swapping adapters via configuration changes no service test |
| AT-4.7 | prompt pinning: the analysis stores the requested/active `prompt_template_version_id`; the adapter receives that id; the returned hash equals the template version's stored `content_hash`; a mismatching hash fails the analysis; the template version cannot be edited |
| AT-4.8 | mock provenance: every mock analysis references a model version with `is_mock=true` and has `simulated=true`; mock model metrics never appear in `/evaluations` (which has 0 rows after seed); the seed creates no simulated evaluation runs |

### M5 — Frontend adapter and parity (gated on X-01)

**Deliverables:** `repository.js`, `apiRepository.js`, proxy, Phase E diff, new tests.
**Exit:** **M5 cannot start until X-01 (frontend-change approval) is granted**; then all 27 Node
tests still pass untouched; 13 browser checks pass in API mode; demo mode unchanged; no off-origin
requests; no uncaught errors.
**Acceptance tests:**

| Id | Test |
|---|---|
| AT-5.1 | repository parity: `tests/domain.test.js` scenarios pass against both implementations |
| AT-5.2 | golden snapshot equality (M2 fixture) through the adapter |
| AT-5.3 | all 13 browser checks pass with `?repo=api`; toasts and error sentences identical |
| AT-5.4 | browser check still passes with the default in-memory repository (no regression) |
| AT-5.5 | scan run flow: click → `POST /runs` → polling → cache refresh → `Completed` row and finding appear |
| AT-5.6 | verification flow: one `POST /verifications`, toast text unchanged, finding `Resolved` and task `Completed` |
| AT-5.7 | CSV download byte-equal to the in-memory export |
| AT-5.8 | request log: no off-origin request; `/api` calls only with the flag; 304 refresh path |
| AT-5.9 | `npm test` and `node --test --test-isolation=none` unaffected by the new files |

### M6 — Security hardening and async execution

**Deliverables:** worker claiming runs; isolation settings; auth/CSRF; audit least privilege;
egress allowlist; artifact download path; rate limits; secret handling.
**Exit:** security suite green; browser checks still green.
**Acceptance tests:**

| Id | Test |
|---|---|
| AT-6.1 | two workers race one `PENDING` run → exactly one executes (SKIP LOCKED) |
| AT-6.2 | stale heartbeat recovery marks the run `FAILED`/job `FAILED` once |
| AT-6.3 | worker has non-root, read-only rootfs, caps dropped, no published ports (inspect compose/run config); resource limits enforced (OOM/timeout kill) |
| AT-6.4 | egress deny: disallowed destination from the execution backend fails; only authorized target allowlist reachable (skipped until a network adapter exists; unit-tested at the allowlist resolver) |
| AT-6.5 | artifact download requires auth, sends `Content-Disposition: attachment` + `nosniff`, never inline HTML/SVG; traversal and `sha256` mismatch rejected |
| AT-6.6 | CSRF: unsafe request without/with wrong token → 403; with token → success |
| AT-6.7 | app role cannot `UPDATE`/`DELETE` audit/status history; migrations role cannot be used by the app |
| AT-6.8 | secrets: no secret material in API responses, logs, or the frontend bundle; log redaction tests for cookie/authorization |
| AT-6.9 | static ACL tests (17) still pass with the API running; no static path is served by the API |
| AT-6.10 | rate limit returns 429 with the frozen message under burst |
| AT-6.11 | credentials (only if D-02 chooses local auth; X-05 pending): passwords are stored as Argon2/bcrypt hashes, never logged or returned; an inactive user cannot authenticate; seeded accounts have no password hash until X-05 is decided |
| AT-6.12 | audit coverage of identity changes: user provisioning/deactivation and membership grant/role-change/removal each emit the documented audit event |

### M7 — Reproducible AI experiments and operations

**Deliverables:** `training/` package + compose profile; dataset export; **`MEASURED`** evaluation
runs; model promotion procedure; ops docs (backup/restore, retention); CI config. Training uses two
DB roles: `sentrix_readonly` for dataset export and a narrowly scoped `sentrix_eval` writer for
`evaluation_run` / `model_version` promotion rows — a single read-only role cannot write the
evaluation records this plan requires. **Dataset/source/licence (X-03) and the reproducibility
target (X-04) must be recorded before this milestone is accepted.**
**Exit:** a clean clone reproduces a `MEASURED` metric from fixed dataset hash + seed; training
never imported by the API image; no simulated data is reported as a measurement; docs updated.
**Acceptance tests:**

| Id | Test |
|---|---|
| AT-7.1 | dataset export is byte-stable (`content_hash` reproducible); `sentrix_readonly` cannot mutate, and the export path needs no write grant; `dataset.license` and provenance are populated per X-03 |
| AT-7.2 | **only `MEASURED` rows are accepted:** a training/evaluation run with fixed seed and dataset version writes `data_origin='MEASURED'` and reproduces the recorded metrics exactly (or within the tolerance documented in X-04); the seed creates 0 evaluation runs, so this test always starts from an empty evaluation table |
| AT-7.3 | `evaluation_run` records environment (image digest), seed and dataset/model versions |
| AT-7.4 | API image contains no training dependency and no dataset; `pip install` graph check |
| AT-7.5 | model promotion: stage transition is auditable; analysis pins the promoted version; a second PRODUCTION version is rejected (C-13); `sentrix_eval` can write evaluation/model rows and nothing else |
| AT-7.6 | `docker compose up` from empty volumes + migrate + seed + smoke test passes; `pg_dump`/restore reproduces the demo state |
| AT-7.7 | **simulated ≠ measured:** no `SIMULATED` evaluation row can be created by M7 tooling; `/evaluations` always returns `dataOrigin`; the adapter renders “Sample …” metrics only for `is_mock` models; any thesis table/claim drawn from the app excludes `SIMULATED` rows |
| AT-7.8 | prompt provenance for real analyses: every `MEASURED`/real analysis pins a prompt-template version whose hash is verified; the template content is retrievable from the DB; changing template content requires a new version |
| AT-7.9 | decisions X-03/X-04 are recorded in 07 §4 with a named dataset, licence and primary metric before AT-7.2 is marked passed |

### 6.1 Global acceptance gates (all phases)

| Gate | Criterion |
|---|---|
| G1 | Existing 27 Node tests pass; 17 static/server tests unchanged (ACL frozen). |
| G2 | 13 CDP browser checks pass in API mode and in demo mode; zero off-origin requests; zero uncaught errors. |
| G3 | 100 % of the transition matrix covered; all invariants checkable and checked in SQL; frozen messages asserted. |
| G4 | Every mutation emits its documented audit event set (≥1 per created/changed resource); denied operations are audited; audit/status-history tables are tamper-proof. |
| G5 | Clean-machine reproduction: compose, migrations, seed, tests, browser check — no manual steps beyond `.env`. |
| G6 | Docs updated (run/test/verify instructions) and every open decision either closed or explicitly deferred. |
| G7 | No Kubernetes, no microservices, no new frontend dependency, no change to the static ACL. |
| G8 | Simulated ≠ measured: no simulated evaluation data is ever surfaced as a measurement; `dataOrigin`/`isMock`/`simulated` are asserted by tests. |
| G9 | Identity is complete: auth, CSRF, user provisioning and project-membership management are implemented and tested (M2/M3 tests green), or explicitly deferred with the affected endpoints feature-flagged off. |
| G10 | The seed is a verifiable oracle: `seed-manifest.json` matches the database after a fresh seed and after a re-run (AT-1.8). |

---

## 7. Test inventory after migration

| Suite | Count | Runs in | Notes |
|---|---:|---|---|
| `tests/domain.test.js` | 5 | Node, unchanged | never edited; its five scenarios are mirrored by the new parity suite in M5 |
| `tests/app.test.js` | 5 | Node, unchanged | DOM stub; in-memory repository |
| `tests/server.test.js` | 9 | Node, unchanged | ACL/containment (ACL frozen) |
| `tests/static.test.js` | 8 | Node, unchanged | path classifier |
| `scripts/browser-check.mjs` | 13 | CDP | unchanged; run in both repository modes |
| `backend/tests/test_schema.py` (new) | ~15 | pytest + Postgres | M1; includes AT-1.1–1.7, 1.10–1.15 |
| `backend/tests/test_seed.py` (new) | ~5 | pytest + Postgres | M1; manifest equality/idempotency (AT-1.8) |
| `backend/tests/test_identity.py` (new) | ~8 | pytest | M2/M3; auth, CSRF, users, memberships (AT-2.9/2.10, AT-3.16/3.17) |
| `backend/tests/test_reads.py` (new) | ~10 | pytest | M2 |
| `backend/tests/test_transitions.py` (new) | ~40 (matrix) | pytest | M3 |
| `backend/tests/test_invariants.py` (new) | ~13 | pytest + SQL | M3 |
| `backend/tests/test_adapters.py` (new) | ~12 | pytest | M4; includes prompt pinning (AT-4.7/4.8) |
| `backend/tests/test_security.py` (new) | ~12 | pytest/compose | M6 |
| `training/tests` (new) | ~8 | pytest/container | M7; includes measured-vs-simulated (AT-7.2/7.7/7.8) |

---

## 8. Phase exit reviews

Each milestone closes with a review against G1–G10 plus:

- **M1:** schema review by an independent reader (field meanings match 03, no invented columns);
  `seed-manifest.json` diff report attached (counts, ids, key fields, idempotent re-run).
- **M2:** read-shape diff report (bootstrap vs in-memory snapshot) plus auth/CSRF matrix attached.
- **M3:** transition matrix report (allowed/denied pairs, messages) plus membership/provisioning
  authz report attached.
- **M4:** adapter conformance report including prompt-template pinning.
- **M5:** parity report with the 13 browser checks’ output and the frozen-message diff.
- **M6:** isolation evidence (inspect/limits/egress/audit tamper) attached.
- **M7:** reproduction log (dataset hash, seed, metrics).

---

## 9. Rollback

| Situation | Rollback |
|---|---|
| Adapter bug in Phase E | Remove `?repo=api`/flag → in-memory repository, zero server dependency |
| API regression | Stop `api`/`worker`; the demo keeps running from memory; API is not in the static path |
| Migration problem | `alembic downgrade` + re-seed; no frontend impact (frontend never touched before Phase E) |
| Security finding in an adapter | Disable the adapter via config; jobs remain `QUEUED`/fail closed; audit records the disable |
| Frontend parity failure | Keep default repository as memory; do not flip the default until AT-5.3/AT-5.4 are green |

No phase requires deleting `domain.js` or the existing server; the in-memory path remains a
permanent offline mode and the reference implementation for parity tests.

---

## 10. What Phase 2 completes vs. defers

**Completed by Phase 2 (this document set):** current-state inventory; workflow→API traceability;
architecture and adapters; ERD/schema/data dictionary; API contract (including auth/membership
provisioning and concurrency); state machines and invariants; prompt-template provenance;
simulated-vs-measured separation; migration plan; exact seed manifest; measurable M1 ticket;
milestones and acceptance tests; risks/assumptions/decisions (D-01…D-18, X-01…X-06); validation
report (08).

**Deferred to implementation phases:** any code, any dependency, any file change outside `docs/`,
auth mechanism (D-02), real scanner/model (X-02), dataset content/licence (X-03), reproducibility
metric (X-04), upload pipeline (D-16), PDF export, retention policy (D-14), and the frontend
async-adapter diff (Phase E, gated on X-01 — currently PENDING, not approved).
