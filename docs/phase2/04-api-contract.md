# SENTRIX — Phase 2 · REST API Contract (v1)

| | |
|---|---|
| Status | Proposed contract. Not implemented; no existing file changed. |
| Base URL | `http://127.0.0.1:3000/api/v1` — same origin as the page (02 §6); loopback only in development. |
| Media type | `application/json; charset=utf-8` except the CSV export. |
| Related | [03 data model](03-data-model.md) · [05 state transitions](05-state-transitions.md) · [06 frontend adapter](06-migration-and-acceptance.md#5-frontend-adapter-and-traffic-path) |
| Compatibility promise | The Phase-E frontend adapter must reproduce today's DOM, toasts and error sentences from these responses. Frozen sentences are in §7; display-string mapping is 03 §3. |

---

## 1. Conventions

### 1.1 Identity and authorization

- Every request is authenticated by a session cookie (`sentrix_session`, `HttpOnly`, `SameSite=Lax`, `Secure` outside development) or, for tooling, a bearer token issued by the same auth surface. The mechanism is open decision **D-02**; the contract only assumes an authenticated actor is available.
- Unsafe methods (`POST`, `PATCH`, `DELETE`) with cookie auth require `X-CSRF-Token` matching the session's CSRF value. Missing/mismatched → `403 auth.csrf_failed`.
- Roles: `ADMIN`, `ANALYST`, `VIEWER`; project membership roles `OWNER`, `ANALYST`, `VIEWER` (04 §6). Unauthenticated → `401`; authenticated but not a project member → `404` (existence not leaked); member but insufficient role → `403`.
- Demo mode seeds a session for `Maya Chen` (`SENTRIX_DEV_AUTO_LOGIN=1`) so the current UI, which has no login screen, keeps working (01 §7.6).

### 1.2 Wire conventions

| Rule | Value |
|---|---|
| Ids | opaque strings (`project-atlas` in the demo seed; `prj_01JC…` for new rows). Clients must not parse or construct them. |
| Timestamps | ISO-8601 UTC with `Z`; date-only `YYYY-MM-DD` only where today's UI already uses a date (project `createdAt`, remediation `dueDate`). |
| Enums | canonical UPPER_SNAKE codes; the adapter maps them (03 §3). `null` is never used to mean “unknown state”. |
| Nulls | absent optional values are omitted, not `null`, unless the field is semantically nullable (e.g. `jobId`). |
| Errors | one envelope, §7. HTTP status is the primary signal; `error.code` is stable for clients. |
| Request id | `X-Request-Id` accepted or generated; echoed on the response and stored on audit rows. |
| Pagination | `?limit=50&cursor=<opaque>` → `{ "items": [...], "nextCursor": "<opaque>" | null }`; default 50, max 200. |
| Filtering/sorting | list endpoints accept documented filters; default order is `created_at DESC` (newest first). This matches the in-memory collections for created rows, with one caveat: the seed `scans` array is not sorted, so bootstrap returns scans newest-first (06 §3.1). |
| Idempotency | mutating POSTs accept `Idempotency-Key`; the server replays the original response for 24 h, including the original status. |
| Concurrency | mutable resources return `updatedAt` and accept `If-Match: "<updatedAt>"`; mismatch → `409 conflict.stale_resource`. Coverage: project → EP-31; scan job → EP-34/EP-35; finding → EP-36; remediation → EP-39/EP-40. Target carries `updatedAt` for future revocation; reports are immutable once published; user/membership writes are guarded by last-owner/last-admin rules instead of `If-Match`. |
| Caching | authenticated responses `Cache-Control: no-store`; `GET /bootstrap` returns an `ETag` and supports `If-None-Match` → `304`. |
| Body limits | JSON ≤ 64 KiB for normal requests; evidence uploads are a separate mechanism (not in v1). |
| Timeouts | server request budget 15 s (scan run creation returns immediately); adapter polling budget in 06 §5. |

### 1.3 Bootstrap and revisions

`GET /bootstrap` returns the whole demo-scale graph in one response so the adapter can satisfy the
frontend's `snapshot()` without fan-out (01 §7.3). It is explicitly a **bounded compatibility
projection**: findings are capped at 2,000 and audit events at 1,000 (the response flags
`truncated: { findings?: true, audit?: true }`). Beyond that, clients must use the collection
endpoints; the demo scale assumption is A-03. Collection order mirrors the in-memory repository for
created rows (newest-first by creation); the **four** seed targets keep their seed order (they have
no timestamps in the prototype), and the seed `scans` array is explicitly returned newest-first
because it is unsorted in memory (06 §3.1).

`revision` is an opaque token derived from the maximum `updated_at` across mutable tables plus
row-count components; it is used for `If-None-Match` only. It is not a concurrency token for
writes.

---

## 2. Endpoint catalogue

Auth column: **P** = public (loopback/ops only), **A** = authenticated, **M** = member of the
referenced project, **W** = member with write role (OWNER/ANALYST), **ADM** = platform admin.

| Id | Method | Path | Purpose | Auth | Success |
|---|---|---|---|---|---|
| EP-01 | GET | `/bootstrap` | Whole-graph compatibility projection | A | 200 |
| EP-02 | GET | `/me` | Current actor + roles | A | 200 |
| EP-03 | GET | `/projects` | List/filter/search projects | A* | 200 paged |
| EP-04 | GET | `/projects/{projectId}` | Project detail | M | 200 |
| EP-05 | GET | `/targets` | List targets (`?projectId=`) | A* | 200 paged |
| EP-06 | GET | `/scan-jobs` | List jobs (`?projectId=&targetId=&status=`) | A* | 200 paged |
| EP-07 | GET | `/scan-jobs/{jobId}` | Job with latest run projection | M | 200 |
| EP-08 | GET | `/scan-jobs/{jobId}/runs` | Attempt history | M | 200 paged |
| EP-09 | GET | `/scan-runs/{runId}` | One run's live status | M | 200 |
| EP-10 | GET | `/findings` | List findings (`?projectId=&jobId=&severity=&status=&q=`) | A* | 200 paged |
| EP-11 | GET | `/findings/{findingId}` | Finding detail | M | 200 |
| EP-12 | GET | `/findings/{findingId}/evidence` | Evidence items (metadata + inline text) | M | 200 |
| EP-13 | GET | `/findings/{findingId}/analyses` | Analysis history (0–1 live) | M | 200 |
| EP-14 | GET | `/findings/{findingId}/remediations` | Remediation tasks + verifications | M | 200 |
| EP-15 | GET | `/remediations/{remediationId}` | One remediation | M | 200 |
| EP-16 | GET | `/reports` | List reports (`?projectId=`) | A* | 200 paged |
| EP-17 | GET | `/reports/{reportId}` | Report + snapshot metadata | M | 200 |
| EP-18 | GET | `/reports/{reportId}/export.csv` | CSV export (exact layout below) | M | 200 `text/csv` |
| EP-19 | GET | `/models` | Model registry | A | 200 |
| EP-20 | GET | `/models/{modelId}/versions` | Versions + stages/metrics | A | 200 |
| EP-21 | GET | `/datasets` | Dataset versions | A | 200 |
| EP-22 | GET | `/evaluations` | Evaluation runs (`?modelVersionId=`) | A | 200 paged |
| EP-23 | GET | `/audit-events` | Audit query | M/ADM | 200 paged |
| EP-24 | GET | `/scan-profiles` | Active profiles (form options) | A | 200 |
| EP-25 | GET | `/healthz` | Liveness | P | 200 |
| EP-26 | GET | `/readyz` | DB + adapter readiness | P | 200/503 |
| EP-27 | GET | `/users` | Active users for assignee/owner selection (`?q=`) | A* | 200 paged |
| EP-28 | GET | `/projects/{projectId}/members` | List project memberships | M | 200 |
| EP-29 | POST | `/projects/{projectId}/members` | Grant membership (user + project role) | W (owner) | 201 |
| EP-30 | POST | `/projects` | Create project | A | 201 |
| EP-31 | POST | `/projects/{projectId}/archive` | Archive project | W (owner) | 200 |
| EP-32 | POST | `/projects/{projectId}/targets` | Record authorized target (attestation required) | W | 201 |
| EP-33 | POST | `/scan-jobs` | Queue scan | W | 201 |
| EP-34 | POST | `/scan-jobs/{jobId}/runs` | Start / retry a run | W | 202 |
| EP-35 | POST | `/scan-jobs/{jobId}/cancel` | Cancel job and active run | W | 200 |
| EP-36 | POST | `/findings/{findingId}/transitions` | Explicit status transition | W | 200 |
| EP-37 | POST | `/findings/{findingId}/analyses` | Request analysis (idempotent) | W | 201 / 200 existing |
| EP-38 | POST | `/findings/{findingId}/remediations` | Create remediation task | W | 201 |
| EP-39 | PATCH | `/remediations/{remediationId}` | Change task status only (never the finding) | W | 200 |
| EP-40 | POST | `/remediations/{remediationId}/verifications` | Record verification → updates finding | W | 201 |
| EP-41 | POST | `/reports` | Generate report snapshot | W | 201 |
| EP-42 | POST | `/reports/{reportId}/publish` | Publish draft | W | 200 |
| EP-46 | POST | `/findings/{findingId}/verifications` | Record independent verification (rescan/manual) → updates finding | W | 201 |
| EP-47 | PATCH | `/projects/{projectId}/members/{userId}` | Change a member's project role | W (owner) | 200 |
| EP-48 | DELETE | `/projects/{projectId}/members/{userId}` | Remove a member (last-owner guard) | W (owner) | 204 |
| EP-50 | POST | `/auth/session` | Sign in (mechanism per D-02) | P | 204 |
| EP-51 | DELETE | `/auth/session` | Sign out | A | 204 |
| EP-52 | POST | `/users` | Provision a user (ADMIN; password field only if D-02 local auth) | ADM | 201 |
| EP-53 | PATCH | `/users/{userId}` | Update display name/role/active flag (last-admin guard) | ADM | 200 |

`A*` = authenticated; the response is filtered to projects the actor can read (a non-member sees
nothing for another project, and a non-member reading a specific resource gets `404`, per §6).
The catalogue has **49 operations** (EP-01…EP-29, EP-30…EP-42, EP-46…EP-48, EP-50…EP-53; EP-43,
EP-44 and EP-45 are intentionally unused IDs).

---

## 3. Resource representations

Codes are canonical. Examples are the v1 wire shapes; the adapter adds the legacy display strings
(03 §3) and the legacy field names where 01 §2 differs.

### 3.1 Project

```json
{
  "id": "project-atlas",
  "name": "Atlas Commerce",
  "owner": { "id": "user-maya", "displayName": "Maya Chen" },
  "scope": "Public web application and authenticated API",
  "status": "ACTIVE",
  "createdAt": "2026-10-12",
  "archivedAt": null,
  "counts": { "targets": 2, "scanJobs": 2, "findings": 2, "openFindings": 2 },
  "updatedAt": "2026-10-18T03:00:00Z"
}
```

`counts` is read-only convenience for the dashboard/project modal; it must agree with the
collection endpoints. `owner` is the only nested actor object; legacy snapshots use
`owner: "Maya Chen"`.

### 3.2 Target

```json
{
  "id": "target-atlas-api",
  "projectId": "project-atlas",
  "name": "api.atlas.example",
  "type": "API",
  "scope": "https://api.atlas.example/v2/*",
  "authorized": true,
  "status": "MONITORED",
  "updatedAt": "2026-10-12T09:00:00Z",
  "authorization": {
    "attestedBy": { "id": "user-maya", "displayName": "Maya Chen" },
    "attestedAt": "2026-10-12T09:00:00Z",
    "statement": "I confirm I have authorization to assess this configured scope.",
    "scopeSnapshot": "https://api.atlas.example/v2/*"
  }
}
```

`authorized`/`status` are derived from the active attestation (03 §4.2), never written directly.
The in-memory target objects have no timestamp today, so the adapter omits `createdAt` in the
legacy snapshot while the API stores one for ordering.

### 3.3 Scan job

```json
{
  "id": "scan-atlas",
  "projectId": "project-atlas",
  "targetId": "target-atlas-api",
  "name": "External perimeter review",
  "profile": { "id": "external_attack_surface", "name": "External attack surface" },
  "status": "COMPLETED",
  "progress": 100,
  "createdAt": "2026-10-18T02:20:00.000Z",
  "updatedAt": "2026-10-18T02:43:00.000Z",
  "createdBy": { "id": "user-maya", "displayName": "Maya Chen" },
  "completedAt": "2026-10-18T02:43:00.000Z",
  "cancelledAt": null,
  "failureReason": null,
  "latestRun": {
    "id": "run_01JC…", "attempt": 1, "status": "SUCCEEDED", "progress": 100,
    "startedAt": "2026-10-18T02:20:04Z", "finishedAt": "2026-10-18T02:43:00Z"
  }
}
```

`progress` and `completedAt` are projections of the latest run: queued → `0`; running → run
progress; completed → `100` and run `finishedAt`; failed/cancelled → last known progress.
The UI's legacy `status` strings are produced by the adapter (03 §3).

### 3.4 Scan run

```json
{
  "id": "run_01JC…",
  "jobId": "scan-atlas",
  "attempt": 1,
  "status": "RUNNING",
  "progress": 78,
  "adapterCode": "demo",
  "workerId": "worker-1",
  "startedAt": "2026-10-18T02:20:04Z",
  "finishedAt": null,
  "heartbeatAt": "2026-10-18T02:38:12Z",
  "errorMessage": null,
  "stats": { "observations": 0, "findingsCreated": 0 }
}
```

Runs are read-only to clients; the worker owns them.

### 3.5 Finding

```json
{
  "id": "finding-bola",
  "projectId": "project-atlas",
  "targetId": "target-atlas-api",
  "jobId": "scan-atlas",
  "runId": "run_01JC…",
  "title": "Broken object-level authorization",
  "severity": "CRITICAL",
  "status": "CONFIRMED",
  "source": "SCANNER",
  "notes": "Validate ownership checks before remediation.",
  "evidence": "Illustrative evidence: simulated response showed a tenant mismatch during an authorized demo replay.",
  "evidenceItems": [ { "id": "ev_…", "kind": "TEXT", "title": "Demo replay excerpt", "sha256": null, "sizeBytes": null } ],
  "remediation": { "id": "task-bola", "status": "IN_PROGRESS", "verification": null },
  "createdAt": "2026-10-18T02:43:00.000Z",
  "updatedAt": "2026-10-18T03:00:00.000Z",
  "resolvedAt": null
}
```

`evidence` is the compatibility summary string (today's `finding.evidence`); `evidenceItems`
carries the structured rows. `remediation` is the latest task — the UI assumes one per finding
(01 §2.6, `app.js:65`).
A full detail response (`EP-11`) also includes `analysis` (latest live analysis or `null`),
`remediation.verification` and `statusHistory` (last 10 events).

### 3.6 Analysis

```json
{
  "id": "analysis-bola",
  "findingId": "finding-bola",
  "model": { "id": "model-risk", "name": "SENTRIX Risk Engine" },
  "version": "4.8.2",
  "promptTemplateVersionId": "ptv-risk-1",
  "promptTemplateHash": "sha256:…",
  "status": "COMPLETED",
  "confidence": 0.91,
  "summary": "High-confidence authorization defect. Business impact is elevated because the affected asset processes customer orders.",
  "limitations": "Mock inference for prototype demonstration only; not a scanner or trained-model result.",
  "simulated": true,
  "latencyMs": 420,
  "inputHash": "sha256:…",
  "promptTemplateHash": "sha256:…",
  "createdAt": "2026-10-18T02:45:00.000Z",
  "completedAt": "2026-10-18T02:45:00.000Z"
}
```

The adapter renders `confidence` as `Math.round(0.91 * 100) = 91` to keep `91%`.

### 3.7 Remediation and verification

```json
{
  "id": "task-bola",
  "findingId": "finding-bola",
  "assignee": { "id": "user-maya", "displayName": "Maya Chen" },
  "dueDate": "2026-10-24",
  "status": "IN_PROGRESS",
  "notes": "Implement object ownership authorization on order reads.",
  "verification": null,
  "createdAt": "2026-10-18T02:50:00Z",
  "updatedAt": "2026-10-18T02:50:00Z",
  "closedAt": null,
  "reopenedAt": null
}
```

```json
{
  "id": "ver_01JC…",
  "findingId": "finding-bola",
  "remediationId": "task-bola",
  "outcome": "VERIFIED",
  "method": "MANUAL_REVIEW",
  "verifier": { "id": "user-maya", "displayName": "Maya Chen" },
  "evidenceId": null,
  "notes": "Re-ran the demo replay; tenant mismatch no longer reproducible.",
  "verifiedAt": "2026-10-18T04:10:00Z"
}
```

### 3.8 Report

```json
{
  "id": "report-atlas",
  "projectId": "project-atlas",
  "jobId": "scan-atlas",
  "title": "Atlas Commerce — Security assessment",
  "status": "PUBLISHED",
  "createdAt": "2026-10-18T03:00:00.000Z",
  "publishedAt": "2026-10-18T03:00:00.000Z",
  "createdBy": { "id": "user-maya", "displayName": "Maya Chen" },
  "snapshotHash": "sha256:…",
  "itemCount": 2
}
```

### 3.9 Audit event

```json
{
  "id": "audit_01JC…",
  "occurredAt": "2026-10-18T03:00:00.000Z",
  "actor": { "id": "user-maya", "displayName": "Maya Chen" },
  "action": "report.published",
  "resource": { "type": "report", "id": "report-atlas", "name": "Atlas Commerce — Security assessment" },
  "outcome": "SUCCESS",
  "requestId": "req_01JC…",
  "metadata": { "from": "DRAFT", "to": "PUBLISHED" }
}
```

The legacy snapshot fields (`at`, `actor` as string, `action` prose, `resource` name, `outcome`
`Success|Simulated`) are produced by the adapter.

---

## 4. Endpoint details (request / response / rules)

Only endpoints with non-obvious payloads are expanded; the rest follow §2–§3 and share the error
model in §7.

### 4.1 EP-01 `GET /bootstrap`

`200` body:

```json
{
  "serverTime": "2026-10-18T09:00:00Z",
  "revision": "r-8f3c…",
  "user": { "id": "user-maya", "displayName": "Maya Chen", "role": "ANALYST" },
  "users": [ { "id": "user-maya", "displayName": "Maya Chen" }, { "id": "user-jon", "displayName": "Jon Bell" } ],
  "projects": [], "targets": [], "scanJobs": [], "findings": [], "analyses": [],
  "remediations": [], "reports": [], "audit": [], "models": [], "datasets": [],
  "scanProfiles": [ { "id": "external_attack_surface", "name": "External attack surface" } ],
  "truncated": {}
}
```

`audit` returns newest-first (the UI renders the whole list). `304` when `If-None-Match` matches.

### 4.2 EP-30 `POST /projects`

```json
{ "name": "Atlas Commerce", "ownerId": "user-maya", "scope": "Public web application and authenticated API" }
```

- `201` returns the project (§3.1).
- `ownerId` optional in the demo (defaults to the actor); the current form always sends
  `owner: "Maya Chen"` and the adapter maps it (06 §5).
- Validation: name 1–80 chars after trim; scope ≤ 2048 chars, default `Not configured` when
  blank (matches `domain.js:64`); duplicate name case-insensitive → `409`.
- Side effects: project + OWNER membership + audit `project.created`.

### 4.3 EP-31 `POST /projects/{projectId}/archive`

Empty body. `200` project with `status: ARCHIVED`, `archivedAt` set. Already archived → `200`
(idempotent, matching `archiveProject`). `404` unknown project. `403` non-owner/non-admin.
Audit `project.archived` with previous status.

### 4.4 EP-32 `POST /projects/{projectId}/targets`

```json
{
  "name": "api.atlas.example",
  "type": "API",
  "scope": "https://api.atlas.example/v2/*",
  "authorization": { "confirmed": true }
}
```

- `201` returns the target (§3.2) with a derived `authorized: true`, `status: MONITORED`, and
  an active attestation row.
- Required `authorization.confirmed === true`; otherwise `422 authorization.confirmation_required`
  with the frozen sentence `Explicit authorization confirmation is required before a target can be used.`
  (today's checkbox is a UI-only guard; the server must own it).
- The attestation statement text is server-defined (the exact sentence from `app.js:58`) and is
  stored with the attested scope; optional `authorization.statement` only appends a note.
- Validation: project must exist and be `ACTIVE` (`409 Select an active project.`); name 1–255;
  scope 1–2048; type one of `WEB|API|CLOUD` (default `WEB`). Scope is **not** URL-parsed for
  correctness, but it is parsed for the egress allowlist when a real scanner is used (02 §7 B4).
- Side effects: target + attestation + audit `target.created` (+ `target.authorized`).

### 4.5 EP-33 `POST /scan-jobs`

```json
{ "targetId": "target-atlas-web", "name": "Web configuration review", "profileId": "external_attack_surface" }
```

- `201` job (§3.3) with `status: QUEUED`, `progress: 0`, no run yet.
- `projectId` is derived from the target (as today, `domain.js:82`); a client-supplied
  `projectId` is ignored/rejected if inconsistent.
- Guards (same messages as today): target exists (`404`); target authorized and scoped
  (`409 This target is blocked: configure and explicitly authorize its scope first.`); project
  `ACTIVE` (`409 Select an active project.`); name required (`422`), ≤ 120; profile active
  (`422`).
- Audit `scan_job.queued` with outcome `SIMULATED` when the demo adapter will run it.

### 4.6 EP-34 `POST /scan-jobs/{jobId}/runs`

Empty body (optional `Idempotency-Key`). `202`:

```json
{
  "run": { "id": "run_01JC…", "jobId": "scan-atlas-web", "attempt": 1, "status": "PENDING", "progress": 0 },
  "job": { "id": "scan-atlas-web", "status": "QUEUED", "progress": 0 }
}
```

- Allowed only when the job is `QUEUED` or `FAILED` → else `409 Only queued or failed scans can be started.`
  (matches `domain.js:87`); an existing active run → `409 Run already in progress.`
- Concurrency: `If-Match: "<job.updatedAt>"` is accepted; a mismatch or stale job state →
  `409 conflict.stale_resource`. Every successful start/retry bumps `scan_job.updated_at`.
- Transaction: insert run (attempt = max+1), one-active-run index protects concurrency, leave the
  job `QUEUED` (the worker moves it to `RUNNING` when it claims the run — 05 §2.1 J2); audit
  `scan_run.queued`.
- The adapter polls `EP-09` until a terminal state (06 §5). The demo worker completes
  deterministically; the UI's post-click toast requires the adapter to wait for terminal state
  within its polling budget.

### 4.7 EP-35 `POST /scan-jobs/{jobId}/cancel`

`200` job. Allowed when job is `QUEUED` or `RUNNING` → else `409 Only active scans can be cancelled.`
(matches `domain.js:95`). `If-Match: "<job.updatedAt>"` is honoured (`409 conflict.stale_resource`
on mismatch). Cancels the active run, sets `job.status = CANCELLED`, `cancelledAt` and bumps
`updated_at`; audit `scan_job.cancelled`. Cancelling a completed job is a `409`, not a silent
no-op.

### 4.8 EP-36 `POST /findings/{findingId}/transitions`

```json
{ "to": "CONFIRMED", "reason": "Validated against source evidence.", "expectedStatus": "NEW" }
```

- `200` `{ "finding": {...} }`.
- The body's `to` must be an allowed transition of the 05 §4.1 table **other than `RESOLVED`**.
  Invalid → `409 Finding cannot move from New to Resolved.` (`error.code = finding.invalid_transition`).
- **`to = RESOLVED` is not accepted here at all.** Resolution happens only as the side effect of a
  `VERIFIED` verification (`EP-40` or `EP-46`); this endpoint returns
  `409 finding.verification_required` with
  `A finding can only be resolved by a recorded verification.` This is the API-level anchor for
  the Phase 2 rule, and it means there is exactly one resolution path.
- `to ∈ {ACCEPTED_RISK, FALSE_POSITIVE}` requires a non-empty `reason` (≤ 1 000 chars); manual
  `REOPENED` from `RESOLVED`/`IN_PROGRESS` requires a reason too. Missing → `422`.
- `expectedStatus` (optional optimistic check) and `If-Match: "<finding.updatedAt>"` guard against
  concurrent edits; mismatch → `409 conflict.stale_resource`.
- Side effects (single transaction): finding status, `finding_status_event` row, audit
  `finding.transitioned` with `metadata: {from, to, reason}`.
- **Compatibility note:** today the UI's “Update status” cycle button eventually attempts
  `IN_PROGRESS → RESOLVED` with no verification and receives `409`; the cycle button therefore
  needs a frontend follow-up (deferred, 06 §5). No automated browser check clicks that button
  (`scripts/browser-check.mjs` contains no `cycle-finding` click), so the existing verification
  flow stays green.

### 4.9 EP-37 `POST /findings/{findingId}/analyses`

Empty body or `{ "modelVersionId": "modelversion-risk-4.8.2", "promptTemplateVersionId": "ptv-risk-1" }`.

- If a live analysis exists for the finding (`QUEUED|RUNNING|COMPLETED`), return `200` with it
  (idempotent, matching `domain.js:99`); otherwise queue one and return `201`.
- Model version: an explicit id must exist and be `PRODUCTION`; otherwise `422 validation.failed`
  with `details: [{field: "modelVersionId", issue: "not a production model version"}]` (no analysis
  row is created). If no production version is configured at all → `503 inference_unavailable`.
- Prompt template: `promptTemplateVersionId` is optional; when omitted the service pins the active
  version of the configured template. An explicit id must exist and belong to an active template,
  else `422 validation.failed`. The analysis stores the pinned version id and the API returns its
  `content_hash` as `promptTemplateHash`; a response hash that differs from the stored template
  hash is rejected (I-11).
- Execution failures (timeout, adapter error, malformed result) create/keep an analysis row with
  `status: FAILED` and a sanitized reason, never a fabricated result; a retry is allowed once the
  previous row is terminal (`FAILED`), matching C-07.
- Side effects: analysis row (`QUEUED`), a job for the worker/inference call, audit
  `analysis.requested` (outcome `SIMULATED` in demo mode).
- The demo mock adapter returns confidence `0.91` for `CRITICAL` findings and `0.76` otherwise,
  `latencyMs: 420` (derived from the seed model's `"Sample 420 ms"` display string), `simulated:
  true` — matching the current deterministic analysis output. Mock analyses always reference a
  mock model version (`is_mock=true`) and a seeded prompt-template version.

### 4.10 EP-38/39/40/46 remediation, closure, verification

Create (EP-38):

```json
{ "assigneeId": "user-maya", "dueDate": "2026-10-25", "notes": "Demo remediation task" }
```

- `201` task (`IN_PROGRESS`), and the finding moves to `IN_PROGRESS` **only from**
  `NEW`/`CONFIRMED`/`REOPENED`; from `RESOLVED`/`FALSE_POSITIVE`/`ACCEPTED_RISK` → `409` (Q2; must
  reopen with a reason first). Optional `If-Match` on the finding's `updatedAt` is honoured.
  Expected audit set for this one request:
  `remediation.created` **and** `finding.transitioned` (one per changed resource, 03 I-08).
- `assigneeId` required (`422 Assignee is required.`); unknown/inactive user → `422`; `dueDate`
  `YYYY-MM-DD` or omitted; notes ≤ 4 000.
- The UI sends `assignee: "Maya Chen"`; the adapter resolves it against `EP-27 /users` (also
  included in `/bootstrap`, §1.3).

Update task status only (EP-39):

```json
{ "to": "COMPLETED", "notes": "Fix deployed." }
```

- `200` task. Allowed: `IN_PROGRESS → COMPLETED|CANCELLED`, `REOPENED → IN_PROGRESS`,
  `COMPLETED → REOPENED` (with reason). **Never changes `finding.status`.** This is the
  “closed task does not resolve a finding” guarantee at the API surface.
  `If-Match: "<remediation.updatedAt>"` is honoured; a successful change bumps `updated_at`.
- Audit `remediation.updated` with `{from, to}`.

Record verification (EP-40, remediation-linked; EP-46, independent):

```json
{ "outcome": "VERIFIED", "method": "MANUAL_REVIEW", "notes": "Re-ran the replay; no mismatch." }
```

- EP-40 is `POST /remediations/{remediationId}/verifications` → `201`
  `{ "verification": {...}, "finding": {...}, "remediation": {...} }`.
- EP-46 is `POST /findings/{findingId}/verifications` with optional `"remediationId"` → `201`
  `{ "verification": {...}, "finding": {...} }`. It exists for rescan/manual verification without
  a task; both endpoints share the same service rules.
- `outcome` required (`VERIFIED|REJECTED`); `method` required
  (`RESCAN|AUTOMATED_TEST|MANUAL_REVIEW`); `evidenceId` must reference evidence of the same
  finding (`409 evidence.mismatch`); if absent, `notes` is required (C-12). A verification against
  a `CANCELLED` task → `409 verification.finding_state`.
- `VERIFIED`: inserts verification, sets a linked task `COMPLETED` (if not already), moves the
  finding `IN_PROGRESS → RESOLVED` or `REOPENED → RESOLVED`, sets `resolved_at`, writes
  `finding_status_event` with `verification_id`; otherwise `409 verification.finding_state`.
- `REJECTED`: inserts verification, sets a linked task `REOPENED`, and moves `IN_PROGRESS`/
  `RESOLVED` to `REOPENED` with the verification id. Against an already-`REOPENED` finding it
  records the verification and writes **no** status event (state unchanged).
- Expected audit set for one verification request: `verification.recorded` plus
  `finding.transitioned` when the status actually changes.
- The legacy UI sends the string `"Verified"` and expects the toast
  `Simulated verification recorded; finding resolved.`; the adapter maps it to
  `{outcome: "VERIFIED", method: "MANUAL_REVIEW", notes: "Recorded from demo UI."}` and keeps the
  toast client-side. It performs **one** call, not a task-close plus a resolution.

### 4.11 EP-41/42/18 reports

Create (EP-41):

```json
{ "projectId": "project-atlas", "title": "Atlas Commerce — Security assessment", "jobId": "scan-atlas" }
```

- `201` report `DRAFT`; `title` optional (defaults to `<project> — Security assessment`, matching
  `domain.js:105`); `jobId` optional but must belong to the project (`422`). Project must be
  `ACTIVE` (`409` — tightening Q6). Snapshot is captured at creation: all project findings in
  `created_at DESC` order, copied into `report_finding` rows with `position = 1..n`;
  `snapshotHash` computed over those rows. Export replays rows by `position`.
- `jobId` is stored for provenance; it does **not** filter the snapshot. This resolves today's
  ambiguity (Q5): the current export ignores `scanId`, so preserving observed behaviour means the
  snapshot contains all project findings. If the supervisor wants scan-scoped reports, that is
  decision D-09.
- Publish (EP-42): `DRAFT → PUBLISHED`, sets `publishedAt`, immutable afterwards (re-publish →
  `409`); audit `report.published`.
- Export (EP-18): `200 text/csv; charset=utf-8`, `Content-Disposition: attachment; filename="sentrix-report.csv"`,
  body byte-identical to the layout in 01 §5.1 (every cell quoted, `"` doubled, `\n` line ends,
  rows from the snapshot). Missing report → `404`; unpublished draft is exportable (today's UI
  exports drafts), publish status is not enforced on export.

### 4.12 EP-19/20/21/22 models, datasets, evaluations

Read-only; no UI mutation exists. `GET /bootstrap` keeps the compatibility display fields the UI
prints (`name`, `version`, `status`, `precision`, `recall`, `f1`, `inference` as display strings)
because the adapter consumes them; all other endpoints (and every status field) use canonical
codes/structured values. `/models` and `/evaluations` expose `metrics` and per-version data:

```json
{
  "id": "model-risk", "name": "SENTRIX Risk Engine", "providerType": "MOCK",
  "versions": [ {
    "id": "modelversion-risk-4.8.2", "version": "4.8.2", "stage": "PRODUCTION",
    "isMock": true, "metrics": { "precision": 0.91, "recall": 0.88, "f1": 0.89, "inferenceMs": 420 },
    "artifactSha256": null, "trainingDatasetVersionId": null, "createdAt": "2026-10-01T00:00:00Z"
  } ]
}
```

The adapter formats mock metrics as `"Sample 0.91"` / `"Sample 420 ms"` **only when
`isMock=true`**; real model versions are rendered from structured metrics (the current DOM change
is deferred, 06 §5.4). `/evaluations` returns:

```json
{
  "id": "eval_01JC…", "modelVersionId": "modelversion-risk-4.8.2",
  "datasetVersionId": "datasetversion-demo-2026.09",
  "status": "COMPLETED", "dataOrigin": "MEASURED",
  "metrics": { "precision": 0.87, "recall": 0.83, "f1": 0.85, "samples": 1280 },
  "seed": 20261018, "environment": { "imageDigest": "sha256:…", "cpu": "…" },
  "startedAt": "…", "finishedAt": "…"
}
```

`dataOrigin` is mandatory in every response. `SIMULATED` runs are demo placeholders: consumers
must label them and must not treat their metrics as measurements. `MEASURED` runs require a seed,
`finished_at` and non-empty metrics (C-17). M7 reproducibility (06 AT-7.2) applies **only** to
`MEASURED` rows; the demo seed contains **zero** evaluation runs (06 §3.4).

`/bootstrap` exposes `isMock` on each model version so the adapter can format “Sample …” strings
only for mock data even though the rest of the bootstrap model fields stay in the legacy display
format; `dataOrigin` is returned by `/evaluations` (bootstrap carries no evaluation rows).

### 4.13 EP-23 audit

`GET /audit-events?limit=100&cursor=…&resourceType=finding&resourceId=…&actorId=…&action=…&since=…&until=…`

- Project members see events for their projects; `ADMIN` sees all. An event whose resource is not
  readable by the caller is omitted (no existence leak).
- Response items per §3.9, newest-first. The demo seed supplies the two current rows with
  `outcome` `SUCCESS`/`SIMULATED`.

### 4.14 EP-02/24/25/26/27/28/29/47/48/50/51/52/53 identity, membership, auth and health

- `GET /me`: `{ "id", "displayName", "email", "role", "projectRoles": [{ "projectId", "role" }] }`.
- `GET /users`: paged `{ items: [{ "id", "displayName", "role", "isActive" }], nextCursor }`,
  filtered to active users; used by the adapter to resolve `owner`/`assignee` display names to ids
  and by any future assignee picker. Any authenticated actor may read it (names are already shown
  in the UI); email is not returned.
- `GET /scan-profiles`: `[{ "id", "name" }]` — the three active profiles, in the current form order.
- `GET /healthz`: `{ "status": "ok" }`, no auth, loopback.
- `GET /readyz`: `{ "status": "ok|degraded", "checks": { "db": "ok", "scannerAdapter": "ok", "inferenceAdapter": "ok" } }`,
  `503` when a required dependency is down.
- `POST /auth/session` / `DELETE /auth/session`: only if local credentials are chosen (D-02);
  otherwise the reverse proxy/OIDC layer owns these and the API exposes `/me` only. CSRF token is
  issued with the session (04 §1.1). The demo mode auto-login is a M2 deliverable (06 M2).
- `GET /projects/{projectId}/members`: `200` list of `{ userId, displayName, role, createdAt }`;
  any project member may read.
- `POST /projects/{projectId}/members` `{ "userId": "user-jon", "role": "ANALYST" }` → `201`
  membership; caller must be project `OWNER` or `ADMIN`; duplicate → `409 membership.exists`.
- `PATCH /projects/{projectId}/members/{userId}` `{ "role": "OWNER" }` → `200`; demoting the last
  `OWNER` → `409 membership.last_owner`. `DELETE …/members/{userId}` → `204`; removing the last
  `OWNER` → `409 membership.last_owner`.
- `POST /users` (ADMIN) `{ "displayName": "…", "email": "…", "role": "ANALYST" }` → `201`;
  duplicate email → `409 user.email_conflict`. With local auth (D-02) the request also carries
  `password` and the server stores an Argon2/bcrypt hash (password policy is decision X-05 and is
  **pending**; until decided, the seeded demo accounts have `password_hash = NULL` and cannot log
  in, while demo mode uses the dev session).
- `PATCH /users/{userId}` (ADMIN) `{ "isActive": false }` or `{ "role": … }` → `200`; deactivating
  or demoting the last active `ADMIN` → `409 user.last_admin`; users are never deleted (audit/FK
  integrity).

---

## 5. Validation rules

“Current” describes today's behaviour; “v1” is the proposed server rule.

| Entity.field | Current behaviour | v1 rule | Error |
|---|---|---|---|
| `project.name` | required; trimmed; global case-insensitive unique; no max in domain (form 80) | 1–80 chars, unique case-insensitive | `422` / `409` |
| `project.scope` | optional, defaults `Not configured`; no max | ≤ 2 048, control chars rejected | `422` |
| `project.ownerId` | free-text name; blank → `Maya Chen` | existing active user; default actor | `422` |
| `target.name` | required, trimmed, no format check | 1–255, control chars rejected | `422` |
| `target.type` | form offers Web/API/Cloud; domain defaults Web | enum `WEB|API|CLOUD` | `422` |
| `target.scope` | required on create; free text | 1–2 048; parsed for egress allowlist when executed | `422` |
| `target.authorization.confirmed` | UI checkbox only; domain requires truthy | must be exactly `true`; attestation stored | `422` + frozen sentence |
| `scanJob.name` | required | 1–120 | `422` |
| `scanJob.profileId` | free text, default External attack surface | active profile id | `422` |
| start run | `Queued|Failed` only | same, plus no active run | `409` |
| cancel | `Queued|Running` only | same | `409` |
| `finding.severity` | free string (seed values only) | enum, no client-set on scanner findings (manual creation is out of scope) | — |
| transition `to` | any string accepted | transition table 05 §4 | `409` |
| transition `reason` | none | required for `ACCEPTED_RISK`, `FALSE_POSITIVE`, manual `REOPENED`; ≤ 1 000 | `422` |
| `to = RESOLVED` | implicitly allowed | **not accepted by this endpoint**; resolution only via `EP-40`/`EP-46` verification | `409 finding.verification_required` |
| `modelVersionId` (analysis) | none | must exist and be `PRODUCTION`; otherwise `422 validation.failed` (no row created); no production version at all → `503 inference_unavailable` | `422` / `503` |
| `promptTemplateVersionId` (analysis) | none | optional; default = active version; explicit id must exist and belong to an active template | `422` |
| membership `role` | n/a | `OWNER|ANALYST|VIEWER` | `422` |
| membership target | n/a | user must exist and be active; duplicate → `409`; last OWNER cannot be demoted/removed | `409` |
| user provisioning | n/a | `displayName` 1–120, unique email, role enum; password required only with local auth (X-05) | `422`/`409` |
| remediation `assigneeId` | required name string | existing active user | `422` |
| `remediation.dueDate` | free string, may be `""` | `YYYY-MM-DD` or omitted; `""` → omitted | `422` |
| verification `outcome` | any string; only `"Verified"` succeeds | `VERIFIED|REJECTED` | `422` |
| verification `method` | none | `RESCAN|AUTOMATED_TEST|MANUAL_REVIEW` | `422` |
| verification evidence | none | `evidenceId` of the same finding, or non-empty notes | `422`/`409` |
| report `title` | form-required; repo defaults | optional; ≤ 160; default from project name | `422` |
| report `jobId` | not validated | must belong to `projectId` | `422` |
| pagination `limit` | n/a | 1–200, default 50 | `422` |
| request bodies | n/a | JSON schema, unknown fields rejected for writes | `422` |

---

## 6. Authorization requirements

Platform role → project role default: `ADMIN` can act on any project as `OWNER`; `ANALYST` may be
an `OWNER`/`ANALYST` member; `VIEWER` reads only. Membership is required for every project-scoped
resource (EP-04…EP-18, EP-23 project filter, EP-28…EP-29, EP-30…EP-42, EP-46…EP-48). The `A*` list
endpoints (EP-03/05/06/10/16, EP-27) require authentication and return only rows from projects the
actor can read. Creating a project is allowed for `ANALYST`/`ADMIN` and makes the creator `OWNER`;
`VIEWER` cannot create projects.

| Operation | VIEWER | ANALYST | ADMIN | Extra rule |
|---|---|---|---|---|
| Read projects/targets/jobs/findings/analyses/remediations/reports | ✅ member | ✅ member | ✅ all | non-member → 404 |
| Read audit events | ✅ project-scoped | ✅ project-scoped | ✅ all | unreadable resource omitted |
| Read models/datasets/evaluations/profiles | ✅ | ✅ | ✅ | read-only |
| Read user directory (names only) | ✅ | ✅ | ✅ | never returns emails |
| Read project memberships | ✅ member | ✅ member | ✅ all | |
| Manage project memberships | ❌ | ✅ only if OWNER | ✅ | last OWNER protected |
| Provision/deactivate users | ❌ | ❌ | ✅ | last active ADMIN protected; password policy pending X-05 |
| Create project | ❌ | ✅ | ✅ | becomes OWNER |
| Archive project | ❌ | ✅ only if OWNER | ✅ | archived → writes 409 |
| Create target (attestation) | ❌ | ✅ member | ✅ | active project only |
| Create/cancel scan job, start run | ❌ | ✅ member | ✅ | target authorized + active project |
| Transition finding | ❌ | ✅ member | ✅ | transition table |
| Request analysis | ❌ | ✅ member | ✅ | idempotent |
| Create/update remediation | ❌ | ✅ member | ✅ | assignee may be any active user |
| Record verification | ❌ | ✅ member | ✅ | verifier = actor |
| Create/publish report, export | ❌ | ✅ member | ✅ | export requires read |
| Settings (future SSO/notifications) | ❌ | ❌ | ✅ | not implemented |
| Bootstrap | ✅ | ✅ | ✅ | filtered to readable projects |
| Health endpoints | public (loopback) | — | — | no auth |

CSRF applies to every unsafe method using cookie auth; bearer-token tooling is exempt.

---

## 7. Errors

### 7.1 Envelope

```json
{
  "error": {
    "code": "finding.invalid_transition",
    "message": "Finding cannot move from Resolved to In Progress.",
    "details": [ { "field": "to", "issue": "not allowed from RESOLVED" } ],
    "requestId": "req_01JC…"
  }
}
```

`details` is present only for validation errors. `message` is user-presentable and, for the
situations that exist today, **must equal the frozen sentence** in 01 §4.1 so the adapter can show
it in the unchanged toast.

### 7.2 Status codes and codes

| HTTP | `error.code` | When | Frozen/example message |
|---|---|---|---|
| 400 | `request.malformed` | invalid JSON, bad query syntax | `Malformed request.` |
| 401 | `auth.unauthenticated` | no/invalid session | `Authentication required.` |
| 403 | `auth.forbidden` | authenticated, insufficient role | `You do not have permission to perform this action.` |
| 403 | `auth.csrf_failed` | missing/mismatched CSRF | `CSRF check failed.` |
| 404 | `resource.not_found` | unknown or unreadable resource | `Project not found.` / `Scan not found.` / `Finding not found.` / `Remediation task not found.` / `Report not found.` |
| 409 | `project.name_conflict` | duplicate name (case-insensitive) | `A project with this name already exists.` |
| 409 | `project.archived` | write on archived project | `Select an active project.` |
| 409 | `target.blocked` | scan job on unauthorized/unscoped target | `This target is blocked: configure and explicitly authorize its scope first.` |
| 409 | `scan.invalid_state` | start/cancel in wrong state | `Only queued or failed scans can be started.` / `Only active scans can be cancelled.` |
| 409 | `scan.run_active` | a run is already active | `Run already in progress.` |
| 409 | `finding.invalid_transition` | transition not in table | `Finding cannot move from Resolved to In Progress.` |
| 409 | `finding.verification_required` | `to = RESOLVED` through the transition endpoint | `A finding can only be resolved by a recorded verification.` |
| 409 | `verification.finding_state` | verification against a non-verifiable finding or a cancelled task | `This finding cannot be verified in its current state.` |
| 409 | `evidence.mismatch` | verification evidence belongs to another finding | `Evidence does not belong to this finding.` |
| 409 | `remediation.finding_state` | creating work for a finding in a state that forbids it | `This finding cannot receive remediation in its current state.` |
| 409 | `report.already_published` | re-publish | `Report is already published.` |
| 409 | `membership.exists` | duplicate membership | `This user is already a member of the project.` |
| 409 | `membership.last_owner` | demote/remove the last project OWNER | `A project must keep at least one owner.` |
| 409 | `user.email_conflict` | duplicate user email | `A user with this email already exists.` |
| 409 | `user.last_admin` | deactivate/demote the last active ADMIN | `At least one active administrator is required.` |
| 409 | `conflict.stale_resource` | `If-Match`/`expectedStatus` mismatch | `The record changed since you loaded it.` |
| 422 | `validation.failed` | field validation | exact field-specific sentence from 01 §4.1 where it exists |
| 422 | `authorization.confirmation_required` | target without confirmation | `Explicit authorization confirmation is required before a target can be used.` |
| 429 | `rate.limited` | per-actor/IP limit | `Too many requests. Try again shortly.` |
| 500 | `internal.error` | unexpected | `Something went wrong.` (no internals) |
| 503 | `inference_unavailable` | no usable model version | `AI inference is temporarily unavailable.` |
| 503 | `service.unavailable` | DB/adapter down | `Service is not ready.` |

### 7.3 Error responses the parity adapter relies on

- The HTTP status **and** the message matter: the UI shows `error.message` verbatim.
- The adapter must reject the repository-method promise with an `Error` whose `message` is the
  server's `error.message`, so `safely()`/`notify()` behave exactly as today (`app.js:69`).
- Toasts that today are produced by the view after a successful call (`Project created.`,
  `Simulated scan queued. Run demo when ready.`, `Deterministic demo scan completed; illustrative
  finding recorded.`, `Scan cancelled.`, `Project archived.`, `Authorized target recorded.`,
  `Mock analysis attached to finding.`, `Remediation task created. Verification is required to
  resolve.`, `Simulated verification recorded; finding resolved.`, `Report draft generated from
  current records.`, `Report published.`, `CSV report export downloaded.`) stay in the adapter or
  view, not in API responses — the API must not introduce new visible text on success.

---

## 8. Example sequences

**Scan from queue to completion (demo adapter):**

1. `POST /scan-jobs` → `201 {status: QUEUED}` (project derived from target).
2. Adapter calls `POST /scan-jobs/{id}/runs` → `202 {run: PENDING, job: QUEUED}` (the worker
   moves the job to `RUNNING` when it claims the run).
3. Adapter polls `GET /scan-runs/{runId}` every 150 ms (max 10 s) until `SUCCEEDED`.
4. Adapter fetches `GET /scan-jobs/{id}` → `COMPLETED`, `progress: 100`.
5. Adapter fetches `GET /bootstrap` (or patches its cache) and returns the job to the view;
   the view shows the toast and re-renders with the new finding.

**Remediation + verification (strict semantics):**

1. `POST /findings/{id}/remediations` → `201` task `IN_PROGRESS`; finding `NEW→IN_PROGRESS`;
   audit `remediation.created` + `finding.transitioned`.
2. `PATCH /remediations/{taskId}` `{to: COMPLETED}` → `200` task `COMPLETED`; **finding unchanged**;
   audit `remediation.updated`.
3. `POST /remediations/{taskId}/verifications` `{outcome: VERIFIED, method: MANUAL_REVIEW, notes}`
   → `201` verification; finding `IN_PROGRESS→RESOLVED`; audit `verification.recorded` +
   `finding.transitioned` with the verification id.
4. A future analyst can reopen: `POST /findings/{id}/transitions {to: REOPENED, reason}`.

**Report export:**

1. `POST /reports` (snapshot captured, `snapshotHash`).
2. `POST /reports/{id}/publish` (optional).
3. `GET /reports/{id}/export.csv` → exact CSV (01 §5.1).

**Demo identity and provisioning (M2/M3):**

1. `POST /auth/session` (or dev auto-login in demo mode) → `204` + session cookie/CSRF token.
2. `GET /me` → actor + platform role + project roles.
3. ADMIN provisions a user: `POST /users` → `201`.
4. Project OWNER grants access: `POST /projects/{id}/members` `{userId, role: "ANALYST"}` → `201`.
5. Removing/demoting the last OWNER or last ADMIN → `409` with the codes above.

---

## 9. API open questions

| # | Question | Assumption in this contract |
|---|---|---|
| P-01 | Session cookie vs OIDC | cookie session + seeded demo user (D-02); contract only depends on “an actor” |
| P-02 | Should the API expose codes or legacy display strings? | codes; adapter maps (03 §3), with the `/bootstrap` metrics/audit compatibility exception (§4.12) |
| P-03 | Is `GET /bootstrap` acceptable operationally, or must the UI be changed to per-collection reads? | bootstrap is a bounded demo projection; per-collection endpoints exist for growth |
| P-04 | Should analysis be synchronous in the request or worker-driven? | worker/inference service asynchronous with polling; mock adapter is fast |
| P-05 | Is the frontend allowed to change in Phase E (one-line import + cycle-button behaviour)? | **requested, not approved**: needs supervisor sign-off (X-01). Phase 2 makes no frontend change; M5 is gated on X-01 |
| P-06 | Are evidence artifacts served by the API or a separate download origin? | separate authenticated path/origin in Phase M6 (02 §7 B5); v1 only returns metadata/inline text |
| P-07 | Does the MVP need a membership-management UI? | no; API endpoints EP-28/29/47/48 exist and are exercised by tests/CLI, the current UI has no member screen (06 M3) |
| P-08 | Is prompt-template content editable through the API? | no; templates are seeded/code-defined immutable versions in the MVP; admin editing is deferred (03 M-07) |
