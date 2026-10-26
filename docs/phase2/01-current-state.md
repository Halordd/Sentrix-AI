# SENTRIX — Phase 2 · Current-State Assessment

| | |
|---|---|
| Status | Planning artifact. No existing file, dependency or ACL was changed to produce it. |
| Scope | The repository as it exists today, described only from what is in it. |
| Evidence base | Full read of `app.js`, `domain.js`, `server.mjs`, `static.js`, `index.html`, `package.json`, `README.md`, `tests/*`, `scripts/*`; test suite executed on 2026-10-18. |
| Baseline | 27 Node tests: 26 pass, 1 skipped (file-symlink test, `EPERM` in this sandbox), 0 fail. Browser check: 13 flows, not run here (requires a local Edge/Chrome). |
| Companion docs | [02 architecture](02-architecture-and-security.md) · [03 data model](03-data-model.md) · [04 API contract](04-api-contract.md) · [05 state machines](05-state-transitions.md) · [06 migration & acceptance](06-migration-and-acceptance.md) · [07 risks & decisions](07-risks-assumptions-decisions.md) |

Everything marked **observed** is directly visible in the source. Anything else is marked
**inferred** or **missing** and is listed again in §10 and in the open-decisions register.

---

## 1. What the project is today

A frontend-only, in-memory demonstration of an authorized security-engagement workflow.

- **Runtime**: one Node HTTP process (`server.mjs`) serving static files from the project root.
- **Frontend**: two hand-written ES modules loaded directly by the browser — `app.js` (views,
  modals, render loop, event binding) and `domain.js` (seed data and the in-memory repository).
  No bundler, no framework, no TypeScript, no build step, no runtime dependencies
  (`package.json` declares none).
- **State**: browser memory only. Refresh resets everything (`README.md:71`).
- **Network**: the page makes no `fetch`/`XHR`/`WebSocket`/`EventSource`/beacon calls
  (`README.md:51-56`); the browser check asserts every request is same-origin
  (`scripts/browser-check.mjs:217-225`). Scans, AI analyses and audit entries are labelled
  simulated/sample.
- **Persistence**: none. No database, no migrations, no server-side state.

### 1.1 File inventory (SHA-256 prefix, first 16 hex chars, captured before this document set was written)

| File | Bytes | Lines | SHA-256 prefix | Role |
|---|---:|---:|---|---|
| `app.js` | 28,588 | 90 | `BDCE9F4027F6834A` | Views, modals, render loop, event binding, view/filter state |
| `domain.js` | 13,224 | 116 | `47BA98265C633A17` | Seed data + in-memory repository (the data seam) |
| `server.mjs` | 4,400 | 126 | `0CCE6D64A5EF7DDF` | Static file server (ACL: see §8) |
| `static.js` | 2,834 | 62 | `80F47C6E3C8F5335` | Pure path classification/containment helpers |
| `index.html` | 359 | 13 | `C2A2257DD3D45C66` | Loads `styles.css` and `app.js` only |
| `styles.css` | 16,407 | — | `E9AFDC7851EAAF6E` | Presentation only; no script hooks |
| `README.md` | 4,413 | 74 | `26074CE539FE9C8A` | Run/test/verify instructions, limitations |
| `package.json` | 311 | 13 | `A4D4469BAA918E7B` | `dev`, `start`, `test`, `verify:browser`, `verify` |
| `public/assets/sentrix-mark.svg` | 932 | — | `8A0C639F39669EAB` | Brand mark |
| `scripts/browser-check.mjs` | 18,810 | 432 | `3018FA5F73521232` | 13 CDP-driven UI checks, Node built-ins only |
| `scripts/verify-all.mjs` | 2,665 | 71 | `BF185903B71FB498` | Runs both verification steps, real exit codes |
| `tests/app.test.js` | 2,351 | 75 | `1E0267BFC2317D38` | 5 view/modal render tests with a DOM stub |
| `tests/domain.test.js` | 2,226 | 42 | `444DE59638D0950F` | 5 repository/business-rule tests |
| `tests/server.test.js` | 5,643 | 152 | `CB6AF294AB96F222` | 9 HTTP tests incl. junction/symlink escapes |
| `tests/static.test.js` | 2,211 | 54 | `02FD63AC73C385FB` | 8 path-classifier tests |

No `.git` directory exists and `git` is not tracking this tree; there is no commit hash to pin
the baseline to. The hashes above are the reproducibility anchor for “nothing existing changed”.

### 1.2 Verification semantics that later phases must keep working

- `npm test` (`package.json:9`) runs `node --test`. In a sandbox that blocks child-process
  spawning this fails with `EPERM`; `node --test --test-isolation=none` runs the same suite in
  one process (`README.md:21-25`). This environment hit exactly that, which is why the baseline
  above was produced with `--test-isolation=none`.
- `npm run verify:browser` (`scripts/browser-check.mjs`) drives real Edge/Chrome over CDP. Exit
  `0` = all checks pass, `1` = a check failed, `2` = no browser available. It explicitly asserts
  **zero off-origin requests** (`:217-225`) and **zero uncaught page errors** (`:409-415`).
- `npm run verify` (`scripts/verify-all.mjs`) reports `PASS` / `PARTIAL` / `FAIL`; a skipped
  browser check is never reported as a pass (`:67-71`).

These three facts constrain the backend design directly:

1. **No off-origin requests** means an API on a different origin breaks an existing passing
   check. The plan therefore puts the API behind the same origin at `/api/v1` (see
   [02 §6](02-architecture-and-security.md#6-same-origin-traffic-path-browser-check-compatibility)
   and [06 §5](06-migration-and-acceptance.md#5-frontend-adapter-and-traffic-path)).
2. **Browser checks and domain tests assert UI/error text** (`/Project created/`, `/Simulated scan
   queued/`, `/Deterministic demo scan completed/`, `/Explicit authorization confirmation is
   required/`, `/active project/`, `/Simulated verification recorded/`), so backend
   error/notification text cannot change silently.
3. **The demo must stay runnable without Docker.** `npm run dev` + the existing tests must keep
   working untouched; the backend is additive.

---

## 2. Entities — actual fields

All entities are plain JS objects. There is no schema, no validation layer beyond the
`requireValue` helper and a handful of guards inside repository methods (`domain.js:57`), and no
referential integrity beyond what the seed data happens to satisfy (and what the frontend joins
by lookup). `uid(prefix)` appends six base-36 characters (`domain.js:9`); ids are therefore not
cryptographically random and can collide in principle.

Legend: **Req** = required by the code that creates it; **Enum?** = values seen in seed/UI, not
enforced anywhere.

### 2.1 `projects` (`domain.js:13-15`)

| Field | Type (observed) | Notes |
|---|---|---|
| `id` | string, e.g. `project-atlas` | seed ids are readable slugs; created ids are `project-xxxxxx` |
| `name` | string | required, trimmed; globally unique case-insensitively (`domain.js:63`) |
| `owner` | string, person name | free text; defaults to hard-coded `"Maya Chen"` when blank (`domain.js:64`) |
| `status` | `"Active" \| "Archived"` | created as `Active`; only `archiveProject` changes it |
| `scope` | string | required on create? No — defaults to `"Not configured"` if blank (`domain.js:64`). Form marks it required (`app.js:57`) |
| `createdAt` | date-only string `YYYY-MM-DD` | `now().slice(0,10)` (`domain.js:64`); seed values are dates without time |

### 2.2 `targets` (`domain.js:17-22`)

| Field | Type (observed) | Notes |
|---|---|---|
| `id` | string, e.g. `target-atlas-api` | |
| `projectId` | string | must reference a project that is not archived (`domain.js:74`) |
| `name` | string | required, trimmed; hostname/URL, not parsed or validated as a URL |
| `type` | `"Web" \| "API" \| "Cloud"` | form default `Web`; `Cloud` exists only in the form (`app.js:58`) |
| `authorized` | boolean | only ever created as `true`; seed has one `false` (`target-northstar`) |
| `scope` | string | required on create; free text such as `https://api.atlas.example/v2/*`; never contacted |
| `status` | `"Monitored" \| "Blocked"` | seed sets `Blocked` exactly when `authorized:false`; not recomputed by code |
| `createdAt` | — | **missing** — targets have no timestamp at all |

### 2.3 `scans` (`domain.js:23-27`) — the UI's “assessment”; becomes `scan_job` + `scan_run`

| Field | Type (observed) | Notes |
|---|---|---|
| `id` | string, e.g. `scan-atlas` | |
| `projectId` | string | copied from the target, not taken from the form (`domain.js:82`) |
| `targetId` | string | required; target must be `authorized` and have non-empty `scope` (`domain.js:80`) |
| `name` | string | required, trimmed |
| `profile` | string | `External attack surface` (default) · `API authorization` · `Cloud configuration`; free text |
| `status` | `"Queued" \| "Running" \| "Completed" \| "Failed" \| "Cancelled"` | created `Queued`; `Running` appears only in seed data (nothing ever sets it); `Failed` is **never produced by any code path** — it is only accepted as a startable state and gets a “Run demo” button |
| `progress` | integer 0–100 | created `0`; set to `100` on completion; never advanced incrementally |
| `simulated` | boolean, always `true` | created at `domain.js:82`; not surfaced in the UI |
| `createdAt` | ISO-8601 UTC with `Z` | |
| `completedAt` | ISO-8601 UTC with `Z`, optional | set by `runSimulatedScan` for new scans; the two completed seed scans already carry it |

There is **no run history**: a scan is a single mutable row, so retries overwrite the only status
and timestamps. The lifecycle caption in the UI (`Draft → Queued → Running → Completed`,
`app.js:35`) includes a `Draft` state that no code ever creates — it is copy, not behaviour.

### 2.4 `findings` (`domain.js:28-32`)

| Field | Type (observed) | Notes |
|---|---|---|
| `id` | string | |
| `scanId` | string | provenance; the UI always has a non-null value for seed findings |
| `projectId`, `targetId` | string | denormalised copies; the UI joins through them |
| `title` | string | free text |
| `severity` | `"Critical" \| "High" \| "Medium" \| "Low"` | displayed directly; filter select omits `Low` (`app.js:42`) |
| `status` | `"New" \| "Confirmed" \| "In Progress" \| "Resolved" \| "Reopened" \| "Accepted Risk"` | the dashboard also excludes `"False Positive"` (`app.js:24`), a value nothing creates |
| `evidence` | string | **the evidence is a single free-text field**, not an entity |
| `createdAt` | ISO-8601 UTC | |
| `notes` | string | free text; accepted-risk rationale lives here in the seed |

### 2.5 `analyses` (`domain.js:33-35`)

| Field | Type (observed) | Notes |
|---|---|---|
| `id` | string | |
| `findingId` | string | one analysis per finding by convention, enforced only by the early return in `createAnalysis` (`domain.js:99`) |
| `model` | string | hard-coded `"SENTRIX Risk Engine"` |
| `version` | string | hard-coded `"4.8.2"` |
| `status` | `"Completed"` only | |
| `confidence` | integer percent | `91` for Critical findings, else `76` (`domain.js:100`); presented as `91%` |
| `summary` | string | templated text |
| `limitations` | string | fixed mock disclaimer |
| `createdAt` | ISO-8601 UTC | |
| `simulated` | boolean, always `true` | |

### 2.6 `remediations` (`domain.js:36-38`) — “remediation tasks” in the UI

| Field | Type (observed) | Notes |
|---|---|---|
| `id` | string, e.g. `task-bola` | `task-` prefix |
| `findingId` | string | |
| `assignee` | string, person name | required, trimmed; free text, no user record |
| `dueDate` | date-only string, may be `""` | form default `"2026-10-25"` (`app.js:85`); seed `"2026-10-24"` |
| `status` | `"In Progress" \| "Completed" \| "Reopened"` | created `In Progress`; only `verifyRemediation` changes it |
| `notes` | string | |
| `verification` | `null \| "Verified"` | **only ever set by the demo path**; UI sends only `"Verified"` (`app.js:85`); any other string is treated as failure (`domain.js:104`). Not a record: no verifier, no method, no timestamp, no evidence |
| `createdAt`/`updatedAt` | — | **missing** |

The UI assumes **one remediation task per finding** (`app.js:65` uses `find`, not `filter`);
`domain.js:103` does not enforce it.

### 2.7 `reports` (`domain.js:39-41`)

| Field | Type (observed) | Notes |
|---|---|---|
| `id` | string | |
| `projectId` | string | required; project must exist (`domain.js:105`) |
| `scanId` | string \| `null` | stored, but **ignored by CSV export** — export filters by `projectId` only (`domain.js:108`) and does not validate that the scan belongs to the project |
| `title` | string | defaults to `` `${project.name} — Security assessment` `` |
| `status` | `"Draft" \| "Published"` | created `Draft`; `publishReport` moves to `Published` with no validation/immutability |
| `createdAt` | ISO-8601 UTC | |

### 2.8 `audit` (`domain.js:42-45`)

| Field | Type (observed) | Notes |
|---|---|---|
| `id` | `audit-...` | |
| `at` | ISO-8601 UTC | |
| `actor` | string | events created through `event()` are hard-coded to `"Maya Chen"` (`domain.js:55`); the **seed** row for the AI analysis uses `"SENTRIX demo service"` (`domain.js:44`) |
| `action` | string | human sentence, e.g. `Created project` |
| `resource` | string | **human-readable name**, not a type+id pair |
| `outcome` | `"Success" \| "Simulated"` | two values observed; not enumerated |

The log is an in-memory array mutated by `unshift` and cloned by `snapshot()`: it is **not
append-only**, has no request correlation, no before/after values, and is lost on refresh.

### 2.9 `models` and `datasets` (read-only demo inventory)

`models` (`domain.js:46-49`): `id`, `name`, `version`, `status` (`"Production"`), and
`precision`/`recall`/`f1`/`inference` as **display strings** with a literal `Sample ` prefix
(e.g. `"Sample 0.91"`, `"Sample 420 ms"`). There is no artifact, dataset link, training record or
evaluation record.

`datasets` (`domain.js:50`): `id`, `name`, `version`, `samples` (number), `provenance` string,
and `labels` as a display string (`"Critical 12% · High 28% · Medium 40% · Low 20%"`). No
dataset content, hash, license or evaluation linkage exists.

---

## 3. Relationships (as observed)

```
projects 1 ── N targets        (target.projectId)
projects 1 ── N scans          (scan.projectId, copied from target)
projects 1 ── N findings       (finding.projectId, denormalised)
projects 1 ── N reports        (report.projectId)
targets  1 ── N scans          (scan.targetId)
targets  1 ── N findings       (finding.targetId, denormalised)
scans    1 ── N findings       (finding.scanId)
findings 1 ── 0..1 analyses    (analysis.findingId; convention only)
findings 1 ── 0..N remediations (remediation.findingId; UI assumes 1)
findings 1 ── 1 evidence       (finding.evidence, an inline string)
reports  N ── 1 projects       (report.projectId, required)
reports  N ── 0..1 scans       (report.scanId, optional, not validated, ignored on export)
audit    —  standalone         (no resource ids; not linkable)
models, datasets — standalone  (not connected to findings or analyses)
```

No foreign key is enforced. The seed happens to be consistent; the repository never checks that
a finding's `projectId`/`targetId` match its scan, that an analysis references a live finding, or
that a report's `scanId` belongs to its `projectId`. Whole-graph joins are done in the frontend on
every access via `data()` → `repo.snapshot()` (`app.js:14`).

---

## 4. Repository interface and methods (`domain.js:53-115`)

`createSentrixRepository(seed = initialData())` deep-clones the seed (`structuredClone`,
`domain.js:54`) and returns a frozen-in-spirit object of functions. The frontend calls it once at
module load (`app.js:3`) and reads through `repo.snapshot()`.

Every method returns a `structuredClone` of the affected record or of the whole state; every
mutation appends an audit entry through the local `event()` helper. **No method takes an actor, so
every event created at runtime says `Maya Chen`; the seed's second audit row is the exception
(`SENTRIX demo service`).** Errors are plain `Error` with user-facing sentences; the UI catches
them and shows `error.message` as a toast (`app.js:69`).

| # | Method (signature as used) | Validation / guards | Effect | Audit action | Notes |
|---|---|---|---|---|---|
| 1 | `snapshot()` | — | clone of all collections | — | called on every `data()` access; ~10+ times per render |
| 2 | `createProject({name, owner, scope})` | name required; name unique case-insensitively | prepends project (`status:"Active"`, `owner` default `Maya Chen`, `scope` default `Not configured`, `createdAt` date-only) | `Created project` | no Archived-name reuse rule beyond global uniqueness |
| 3 | `archiveProject(projectId)` | project must exist | sets `status:"Archived"` | `Archived project` | idempotent (re-archives); no un-archive |
| 4 | `createTarget({projectId, name, type, scope, authorizationConfirmed})` | name, projectId, scope required; `authorizationConfirmed === true` **must** be truthy; project must exist and not be archived | prepends target (`authorized:true`, `status:"Monitored"`) | `Configured authorized target` | the checkbox is the only authorization evidence; the literal statement is in the form, not stored |
| 5 | `createScan({name, targetId, profile})` | name required; target exists; target `authorized` and `scope` non-empty; project not archived | prepends scan (`status:"Queued"`, `progress:0`, `simulated:true`, `projectId` from target) | `Queued simulated scan` (outcome `Simulated`) | no method to move Queued→Running; no run record |
| 6 | `runSimulatedScan(scanId)` | scan exists; current status must be `Queued` or `Failed` | sets `status:"Completed"`, `progress:100`, `completedAt`; creates **at most one** finding for the scan (`Demo configuration exposure`, `Low`, `New`, illustrative evidence) | `Completed simulated scan` + `Recorded demo finding` (both `Simulated`) | deterministic; never contacts a target; re-running cannot add a second finding |
| 7 | `cancelScan(scanId)` | status must be `Queued` or `Running` | sets `status:"Cancelled"` | `Cancelled scan` | timer/progress untouched |
| 8 | `updateFindingStatus(findingId, status)` | finding must exist | **assigns any string** as status | `Updated finding status` | no transition validation, no reason, no actor; the only status guard is the UI's cycle map (`app.js:85`) |
| 9 | `createAnalysis(findingId)` | finding must exist | if an analysis for the finding exists, returns it unchanged; else creates hard-coded mock analysis | `Completed AI analysis` (outcome `Simulated`) | idempotent-by-early-return; ignores any requested model |
| 10 | `createRemediation({findingId, assignee, dueDate, notes})` | finding exists; assignee required | prepends task (`status:"In Progress"`, `verification:null`) and **unconditionally sets the finding to `In Progress`** | `Created remediation task` | regresses `Resolved`, `Accepted Risk`, `False Positive` findings |
| 11 | `verifyRemediation(taskId, outcome)` | task exists | `task.verification = outcome`; task `Completed` iff outcome is exactly `"Verified"`, else `Reopened`; finding `Resolved` iff `Verified`, else `Reopened` | `Recorded verification outcome` (`Simulated` when verified) | **task closure and finding resolution are one atomic call**; no verifier, method, evidence or timestamp; any string works |
| 12 | `createReport({projectId, title, scanId})` | projectId required; project exists | prepends report (`status:"Draft"`) | `Generated report draft` | no scan↔project check; archived projects allowed |
| 13 | `publishReport(reportId)` | report exists | `status:"Published"` | `Published report` | no draft validation, no immutability, re-publish allowed |
| 14 | `exportReportCsv(reportId)` | report exists | returns CSV string | `Exported report CSV` | reads **live** project findings (ignores `scanId`); every cell quoted, escaped by doubling quotes (`domain.js:109-112`); exact row layout in §5.1 |

### 4.1 Error messages that are part of the current behaviour

These sentences are wire-level behaviour for the migration. The browser check asserts the
authorization sentence (`scripts/browser-check.mjs:265`) and the domain suite asserts
`/active project/` (`tests/domain.test.js:41`); the rest are the UI's user-visible errors today.

| Situation | Message |
|---|---|
| Project name missing | `Project name is required.` |
| Duplicate project name | `A project with this name already exists.` |
| Project not found | `Project not found.` |
| Archived/invalid project on target/scan create | `Select an active project.` |
| Target hostname missing | `Target hostname or URL is required.` |
| Target project missing | `Select a project.` |
| Target scope missing | `Authorized scope is required.` |
| Authorization checkbox not ticked | `Explicit authorization confirmation is required before a target can be used.` |
| Scan target missing | `Select a target.` |
| Blocked target scan | `This target is blocked: configure and explicitly authorize its scope first.` |
| Scan start on wrong state | `Only queued or failed scans can be started.` |
| Scan cancel on wrong state | `Only active scans can be cancelled.` |
| Scan not found | `Scan not found.` |
| Finding not found (status/analysis/remediation, not verify) | `Finding not found.` |
| Remediation task not found | `Remediation task not found.` (a task whose finding is dangling throws a `TypeError` instead — `domain.js:104` does not look the finding up) |
| Assignee missing | `Assignee is required.` |
| Report project missing | `Select a project.` |
| Report not found | `Report not found.` |

---

## 5. Frontend workflows → backend operations they will require

The page never routes by URL; `state` holds `view`, `modal`, `selectedId`, `search`, `statusFilter`
(`app.js:7`). Every action calls a repository method and then re-renders (`app.js:67`). The table
maps each user-visible workflow to the repository call(s) it makes today and to the endpoint ids
defined in [04-api-contract.md](04-api-contract.md). Endpoint ids (`EP-xx`) and shapes there are
the contract; this table is the traceability matrix.

| # | Workflow (UI trigger) | Repository call(s) today | Future HTTP operation(s) | Notes / parity constraint |
|---|---|---|---|---|
| W1 | App load / any navigation (9 views) | `snapshot()` many times | `GET /api/v1/bootstrap` (EP-01) | frontend reads whole graph; bootstrap is the compatibility projection |
| W2 | Dashboard metrics (`app.js:23-25`) | `snapshot()` | EP-01 | derived client-side: active projects, scans, open findings (`status ∉ {Resolved, False Positive}`), resolved count |
| W3 | Project list + search + status filter (`app.js:28-30`) | `snapshot()` | EP-01 or EP-03 (EP-03 for paged/API-only case) | search is client-side over name/owner; filter over `Active`/`Archived` |
| W4 | Create project modal → submit (`app.js:57, 80`) | `createProject` | `POST /projects` (EP-30) | toast `Project created.`; navigates to Projects view |
| W5 | Project detail modal (`app.js:63`) | `snapshot()` + `byProject` | EP-04 (+EP-01) | counts targets/scans/findings, shows scope, Archive button, Add target |
| W6 | Archive project (`app.js:63, 85`) | `archiveProject` | `POST /projects/{id}/archive` (EP-31) | toast `Project archived.`; archived project's targets disappear from scan form |
| W7 | Attack-surface inventory (`app.js:46`) | `snapshot()` | EP-01 / EP-05 | authorized badge derived from `authorized`; related-finding counts joined client-side |
| W8 | Add authorized target modal → submit (`app.js:58, 81`) | `createTarget` | `POST /projects/{projectId}/targets` (EP-32) | form requires the authorization checkbox; backend must require an attestation payload with the same message; toast `Authorized target recorded.`; navigates to Attack Surface |
| W9 | Scan list + status segmented filter (`app.js:33-35`) | `snapshot()` | EP-06 | status filter shared with projects/findings state; reset on view change |
| W10 | Scan detail modal (`app.js:64`) | `snapshot()` + lookups | EP-07 (+EP-08) | shows profile, target scope, badge, progress; Run demo only for `Queued`/`Failed`; Cancel only for `Queued`/`Running` |
| W11 | Configure scan modal → submit (`app.js:59, 82`) | `createScan` | `POST /scan-jobs` (EP-33) | target options exclude archived projects; blocked targets are rendered but `disabled`; toast `Simulated scan queued. Run demo when ready.` |
| W12 | Run demo (scan row or detail) (`app.js:37, 64, 85`) | `runSimulatedScan` | `POST /scan-jobs/{id}/runs` (EP-34) + poll EP-09 | toast `Deterministic demo scan completed; illustrative finding recorded.`; row must show `Completed` immediately after the action |
| W13 | Cancel scan (`app.js:64, 85`) | `cancelScan` | `POST /scan-jobs/{id}/cancel` (EP-35) | toast `Scan cancelled.` |
| W14 | Finding list + search + filter (`app.js:39-42`) | `snapshot()` | EP-10 | filter matches severity **or** status; client-side search over title/severity/status/project name |
| W15 | Finding detail modal (`app.js:65`) | `snapshot()` joins | EP-11 (+EP-12, EP-13, EP-14) | shows project/target/source scan names, evidence text, optional analysis card, optional remediation card, gated buttons |
| W16 | Update finding status (cycle button) (`app.js:65, 85`) | `updateFindingStatus` | `POST /findings/{id}/transitions` (EP-36) | cycle map: `New→Confirmed→In Progress→Resolved→Reopened→Confirmed`, `Accepted Risk→Reopened`, default `→Confirmed`; strict backend will reject unverified `→Resolved` (see [05](05-state-transitions.md#4-finding-lifecycle)) |
| W17 | Run mock AI analysis (`app.js:65, 85`) | `createAnalysis` | `POST /findings/{id}/analyses` (EP-37) | toast `Mock analysis attached to finding.`; second request must return the existing analysis (no duplicate), matching `domain.js:99` |
| W18 | Create remediation task (`app.js:65, 85`) | `createRemediation` | `POST /findings/{id}/remediations` (EP-38) | toast `Remediation task created. Verification is required to resolve.`; assignee/dueDate are demo constants supplied by the UI |
| W19 | Record verification (`app.js:65, 85`) | `verifyRemediation` | `POST /remediations/{id}/verifications` (EP-40) | toast `Simulated verification recorded; finding resolved.`; the API call must create a verification record and then update the finding; task closure alone must not |
| W20 | AI Intelligence list (`app.js:45`) | `snapshot()` | EP-01 / EP-13 | joins analysis→finding title client-side |
| W21 | Report library (`app.js:47`) | `snapshot()` | EP-16 | shows source scan name or `Project findings` when `scanId` is null |
| W22 | Generate report modal → submit (`app.js:60, 83`) | `createReport` | `POST /reports` (EP-41) | title required by the form even though the repository defaults it; source scan optional |
| W23 | Publish report (`app.js:47, 85`) | `publishReport` | `POST /reports/{id}/publish` (EP-42) | toast `Report published.`; button hidden once published |
| W24 | Export report CSV (`app.js:47, 85`) | `exportReportCsv` | `GET /reports/{id}/export.csv` (EP-18) | today the browser builds the blob from the repository string; Phase E may keep client-side generation from the snapshot until server export is proven byte-equivalent |
| W25 | Models & Data views (`app.js:48`) | `snapshot()` | EP-19, EP-20, EP-21, EP-22 | read-only; metrics are display strings today — API must preserve or the adapter must format |
| W26 | Settings & audit (`app.js:49`) | `snapshot()` | EP-23 | audit rendered as `at · action · actor · resource · outcome`; SSO/notifications controls are disabled and have no behaviour |
| W27 | Global search trigger (`app.js:67, 85`) | none (state only) | — | switches to Projects, clears search+filter; no API |
| W28 | Escape key closes modal (`app.js:86`) | none (state only) | — | no API |
| W29 | View switch / filter change / search typing (`app.js:72-79`) | none (state only) | — | client-side; no URL, no deep link |
| W30 | Settings “Clear view filters” (`app.js:49`, `app.js:85`) | none (state only) | — | resets `search`/`statusFilter`; no API |
| W31 | Modal Cancel / close button (`app.js:53`, `app.js:85`) | none (state only) | — | sets `state.modal = null`; no API |

The gaps that matter for the API design are therefore: **one analysis per finding**, **one
remediation per finding in the UI**, **`updateFindingStatus` accepting anything**, **verification
being a single scalar**, and **snapshot-based reads**. Each is addressed explicitly in
[03](03-data-model.md), [04](04-api-contract.md) and [05](05-state-transitions.md).

### 5.1 Exact CSV contract (must be reproduced by the export endpoint)

Rows (`domain.js:110-112`), every cell wrapped in double quotes with `"` doubled inside:

```
"SENTRIX report","<report title>"
"Project","<project name>"
"Scope","<project scope>"
<blank line>
"Severity","Status","Finding","Target","Evidence"
"<severity>","<status>","<title>","<target name>","<finding.evidence>"
... one row per finding of the project, in current array order ...
```

Joined with `\n`. The report's `scanId` is **not applied**. Finding order is repository order
(newest-first for created rows because of `unshift`).

---

## 6. State transitions that exist today

These are the transitions the code actually permits, not a proposed design (the proposal is in
[05](05-state-transitions.md)).

### 6.1 Scan (`scans[].status`)

| From | To | Trigger | Guard |
|---|---|---|---|
| (new) | `Queued` | `createScan` | target authorized + scoped; project active |
| `Queued` | `Completed` | `runSimulatedScan` | status ∈ {Queued, Failed} |
| `Failed` | `Completed` | `runSimulatedScan` | same method |
| `Queued` | `Cancelled` | `cancelScan` | status ∈ {Queued, Running} |
| `Running` | `Cancelled` | `cancelScan` | same |
| `Queued` | `Running` | **no code path** | seed data only (`scan-atlas-running`) |
| `Running` | `Completed` | **no code path** | — |
| `Completed` | anything | **no code path** | terminal in practice |
| `Cancelled` | anything | **no code path** | terminal in practice |

`runSimulatedScan` jumps straight from `Queued`/`Failed` to `Completed` and sets progress 100; the
`Running` state is decorative. There are no runs, attempts, workers, timeouts or failure reasons.

### 6.2 Finding (`findings[].status`)

`updateFindingStatus` accepts **any string at all**; the only state machine is the UI cycle map
(`app.js:85`) and the two compound mutations:

| From | To | Trigger | Guard / side effect |
|---|---|---|---|
| (new seed) | `New` / `Confirmed` / `Accepted Risk` | seed data | — |
| `New` | `In Progress` | `createRemediation` | unconditional overwrite |
| `Confirmed` / `Resolved` / `Reopened` / `Accepted Risk` | `In Progress` | `createRemediation` | **unconditional** — `Resolved` is silently regressed |
| `In Progress` | `Resolved` | `verifyRemediation(→ Verified)` | no guard on the *source* status: `domain.js:104` assigns `Resolved` from any state, so a `Confirmed` finding also becomes `Resolved`; the UI also offers `updateFindingStatus` for any value |
| any | `Resolved` | `verifyRemediation(→ Verified)` | unconditional assignment — this is the Q3 conflation |
| any | `Reopened` | `verifyRemediation(→ anything but Verified)` | unconditional assignment |
| any | any | `updateFindingStatus` | no guard, no audit detail |

### 6.3 Remediation (`remediations[].status` / `.verification`)

| From | To | Trigger |
|---|---|---|
| (new) | `In Progress`, `verification:null` | `createRemediation` |
| `In Progress` | `Completed`, `verification:"Verified"` | `verifyRemediation` with exactly `Verified` |
| `In Progress` | `Reopened`, `verification:<other string>` | any other outcome string |

There is no “closed but unverified” state, so today the only way to close a task is also the only
way to resolve a finding. That is exactly the conflation the Phase 2 requirement forbids; the
proposed split is in [05 §3–§5](05-state-transitions.md#3-remediation-and-verification).

### 6.4 Report / project / target / analysis

- Report: `(new) Draft → Published` (`publishReport`), re-publish allowed, nothing terminal.
- Project: `Active → Archived` (`archiveProject`), no reverse.
- Target: created `authorized:true`/`Monitored`; the `Blocked` target exists only in seed; no
  re-authorize/revoke/update path.
- Analysis: created `Completed`; no failure/retry states.

---

## 7. What the frontend depends on (parity constraints for the backend)

1. **Snapshot shape and field names.** `app.js` reads `data().<collection>` and fields by the
   names listed in §2. The migration adapter must expose the same names and the same display
   strings (`"In Progress"`, `"Accepted Risk"`, …) or every view breaks.
2. **Synchronous-feeling mutations.** Every handler calls a method and immediately re-renders;
   there is no loading state, no spinner, no error boundary. Async backend calls must resolve
   (or the adapter must await/poll) before `render()`, and errors must reject with a message the
   toast can show (`app.js:69`).
3. **Whole-graph reads.** `snapshot()` is called many times per render; an API adapter needs a
   cache/bootstrap (see [06 §5](06-migration-and-acceptance.md#5-frontend-adapter-and-traffic-path)).
4. **Exact toasts** quoted in §5 and the error substrings in §4.1.
5. **Demo constants** supplied by the UI: assignee `Maya Chen`, due date `2026-10-25`, report title
   fallback, verification outcome `Verified`, analysis triggered per finding.
6. **No auth UI.** There is no login screen, no credentials, no role display. A backend with
   authentication must keep the demo usable without a login step (or add one later; the frontend
   change is **pending supervisor approval X-01**, 07 §4.2).
7. **No off-origin traffic** (browser check). Same-origin `/api/v1` is the only design that
   satisfies it without changing the check.
8. **Static ACL** (below) is imported directly by tests, so it must not be folded into the API
   server or replaced.

---

## 8. The “ACL” that must not change

The repository contains **no access-control list** in the application sense: there is no
authentication, no roles, no project permissions (`app.js:49`, `README.md:72`). The only access
control that exists is the demo static server's path policy, plus the domain guards above. The
plan treats **both of these as frozen**:

**Static file policy (frozen, tested):**

| Request | Result | Source |
|---|---|---|
| Any method other than GET/HEAD | `405` + `Allow: GET, HEAD` | `server.mjs:56-59` |
| Empty target, malformed percent-encoding, NUL, backslash separator | `400` | `static.js:36-49` |
| Dot-prefixed segment, `.`/`..`, escapes root | `403` | `static.js:52-59` |
| `.dsh-acl-recovery` and any dot-directory | `403`, body never leaked | `static.js:28-31`, `tests/server.test.js:58-64` |
| Missing file | `404` | `server.mjs:78-96` |
| Resolved real path outside real root (junction/symlink) | `403` | `server.mjs:74-84`, `tests/server.test.js:97-152` |
| Successful GET/HEAD | `200` + `X-Content-Type-Options: nosniff`, whole file | `server.mjs:98-114` |
| Binding | `127.0.0.1` by default; `HOST` is explicit opt-in | `server.mjs:120-125` |

The browser check additionally asserts the recovery artifacts are unreachable from the page
(`/.dsh-acl-recovery/`, its encoded form, and a traversal form all return `403`,
`scripts/browser-check.mjs:227-236`). The plan keeps `server.mjs`/`static.js` untouched and
serves `/api` on the same origin through a separate dev proxy
([06 §5](06-migration-and-acceptance.md#5-frontend-adapter-and-traffic-path)), so these tests keep
their meaning.

**Domain guards (must be re-implemented server-side, not weakened):**

- target creation requires the explicit authorization confirmation (`domain.js:73`);
- a blocked/unscoped target cannot be scanned (`domain.js:80`);
- archived projects cannot receive targets or scans (`domain.js:74, 81, 68`);
- duplicate project names rejected case-insensitively (`domain.js:63`);
- verification, not task completion, is the demo's stated resolution trigger
  (`tests/domain.test.js:22-28`, UI toast at `app.js:85`).

---

## 9. Observed inconsistencies and defects to resolve (not silently copy)

| # | Observation | Consequence for the backend |
|---|---|---|
| Q1 | `updateFindingStatus` accepts arbitrary strings (`domain.js:96`) | must become an explicit transition endpoint; reject invalid states |
| Q2 | `createRemediation` regresses `Resolved` findings to `In Progress` (`domain.js:103`) | server must reject or require explicit reopen first |
| Q3 | `verifyRemediation` closes the task and resolves the finding atomically; verification is one scalar with no verifier/method/evidence/time (`domain.js:104`) | must split into remediation status + immutable verification record; resolution only via verification |
| Q4 | One analysis per finding by early return; model/version hard-coded (`domain.js:99-101`) | idempotent create semantics + model registry lookup |
| Q5 | CSV export ignores `report.scanId` and reads live findings (`domain.js:108-112`) | decide snapshot vs live; document the scan filter as unused today |
| Q6 | `createReport` does not validate that `scanId` belongs to `projectId`, nor that the project is active (`domain.js:105`) | add validation (tightening; see D-09) |
| Q7 | `runSimulatedScan` creates at most one finding per scan (`domain.js:89`) | the demo adapter must stay deterministic; real adapters return observation sets |
| Q8 | `Running` scan state is unreachable; progress never advances (`domain.js:23-27, 82-94`) | new run model introduces real progress/heartbeat |
| Q9 | Duplicate project names are globally unique — no tenancy dimension (`domain.js:63`) | single-tenant assumption recorded; revisit if multi-tenant |
| Q10 | Audit actor is hard-coded `Maya Chen` for runtime events (seed row 2 is `SENTRIX demo service`); resource is a name string (`domain.js:44, 55`) | audit needs actor ids, resource type/id, request id |
| Q11 | Ids are `prefix + 6 base36` (`domain.js:9`) — collision-prone, not time-ordered | server-generated ids, opaque to the frontend |
| Q12 | Mixed timestamp formats: project/target dates are date-only, everything else ISO-8601 UTC | per-field API contract must keep the existing formats for parity |
| Q13 | Severity/status strings are both data and presentation; `tone()` maps them to CSS (`app.js:9`) | adapter maps canonical codes to legacy display labels |
| Q14 | Status filter state is shared across three views and reset on navigation (`app.js:72`) | purely client-side; no API implication |
| Q15 | The UI shows `Accepted Risk`/`Confirmed` values but the finding filter select omits them (`app.js:42`); dashboard excludes `False Positive` although nothing creates it (`app.js:24`) | enum set is a superset of reachable UI values; keep all documented values, do not drop `False Positive` from the model |
| Q16 | No pagination, sorting, or deep links; ordering matters (created rows are `unshift`ed, but seed arrays are not uniformly sorted — the `scans` seed is not newest-first) | API v1 defines a deterministic order; the adapter can keep it (06 §3.1) |
| Q17 | `snapshot()` clones the whole graph on every accessor call (`app.js:14`) | adapter must cache; do not fan out per accessor |
| Q18 | Evidence is inline text and rendered with `esc()` inside `<code>` (`app.js:65`) | server stores evidence as rows/artifacts; UI keeps the rendered summary |
| Q19 | Targets have no timestamps; remediations have no timestamps | additive fields; do not require them in v1 responses |
| Q20 | `verifyRemediation` treats any outcome other than `Verified` as failure (`domain.js:104`) | explicit `VERIFIED`/`REJECTED` enum replaces implicit string logic |
| Q21 | Seed inconsistency: `finding-bola` is `Confirmed` while its remediation `task-bola` is `In Progress` (`domain.js:29,37`) | preserved as a legacy import exception in the seed manifest (06 §3.4); API mutations obey the state machine |
| Q22 | Seed inconsistency: `finding-debug` has `scanId: scan-atlas` (whose target is `target-atlas-api`) but `targetId: target-atlas-web` (`domain.js:31` vs `:24,19`) | preserved as a legacy import exception; the schema only enforces project-level target/job agreement |

---

## 10. Facts vs. assumptions (uncertainties)

**Facts established from the repository** — everything in §1–§9, incl. the 27-test baseline and
the 13 browser checks.

**Assumptions needed to plan (each is an open decision in [07](07-risks-assumptions-decisions.md)):**

- **A-01 “ACL”** means the static-file path policy in §8 plus the domain guards, not a
  configuration file elsewhere in the tree. No ACL file exists in this repository.
- **A-02 No upload feature exists today**, so the source-code-upload boundary is a forward-looking
  design requirement, not a migration of existing behaviour.
- **A-03 The deployment is single-tenant and demo-scale** (≤ a few dozen projects, ≤ ~10³
  findings). Anything larger needs pagination everywhere and likely partitioning; not planned now.
- **A-04 Users exist externally.** The UI hard-codes owners/assignees (`Maya Chen`, `Jon Bell`,
  `Priya Nair`) and the footer says `Maya Chen · Demo analyst` (`app.js:67`), but the app has no
  user entity, credentials or claims. Role/auth model must be decided (D-02, D-03).
- **A-05 “Authorized target”** currently means a ticked checkbox with no stored statement. Whether
  real engagements need an uploaded authorization document is undecided (D-17).
- **A-06 Docker/PostgreSQL are available at implementation time.** Neither is installed in this
  environment (`docker` and `psql` are absent), so schema/DDL cannot be executed here; the SQL is
  a reviewed design artifact, not a verified deployment.
- **A-07 The demo seed stays the demo seed.** Existing readable ids (`project-atlas`, …) and the
  fixed dataset may be kept in a demo seed for parity; production rows use new ids.
- **A-08 Loopback-only development** as today (`127.0.0.1`), TLS terminated only if a real
  deployment happens.
- **A-09 Tests must run without external network access and without real scanners/models.**
- **A-10 Python 3.12+ and PostgreSQL 16+** are acceptable baselines; exact pins are chosen at
  implementation time for reproducibility.

**Missing entirely (so the backend must add them, not migrate them):** authentication and
identity; authorization/roles; persistence; scan execution (process, queue, worker, attempts);
real evidence storage; model registry/artifacts; evaluation records; dataset content; pagination;
IDs that survive concurrency; append-only audit; request correlation; rate limiting; TLS;
uploaded source-code handling; server-side report rendering (PDF); retry/idempotency semantics.
