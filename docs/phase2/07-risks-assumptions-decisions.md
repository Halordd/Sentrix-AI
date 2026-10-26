# SENTRIX — Phase 2 · Risks, Assumptions, Decisions and Traceability

| | |
|---|---|
| Status | Planning register. Not implemented; no existing file changed. |
| Purpose | Make every uncertain choice explicit before implementation, and prove that the brief's ten tasks and constraints are actually covered. |
| Related | All Phase 2 documents ([index](README.md)) |

---

## 1. Traceability: brief → deliverable

| Brief task | Where it is answered |
|---|---|
| 1. Inspect the repository; document entities, fields, relationships, state transitions, repository methods | [01 current state](01-current-state.md) §2 (fields), §3 (relationships), §4 (14 repo methods + errors), §6 (transitions that exist today) |
| 2. Map each frontend workflow to future backend operations | 01 §5 (W1…W31 → EP-xx endpoints) |
| 3. PostgreSQL ERD and schema for projects/targets, scan jobs/runs, findings/evidence, AI analyses/model versions, remediation/verification, reports/audit, dataset/evaluation metadata | [03 data model](03-data-model.md) §1 ERD, §4 data dictionary; [`schema.sql`](../../database/schema.sql) (25 tables, 18 enums, constraints, triggers) |
| 4. REST contracts with request/response examples, validation, error responses, authorization | [04 API contract](04-api-contract.md): §2 catalogue (49 operations), §3 representations, §4 detailed examples, §5 validation, §6 authz matrix, §7 error catalogue, §8 sequences |
| 5. Explicit scan-job and finding transitions; no resolution via remediation creation/closure | [05 state transitions](05-state-transitions.md) §2 jobs/runs, §3 remediation vs verification (forbidden sequence table), §4 finding machine + invariants; enforced in 04 §4.8/§4.10 and tested in [06](06-migration-and-acceptance.md) AT-3.4…AT-3.8 |
| 6. Scanner-result and AI-inference interfaces so the domain is independent of one scanner/model | [02 architecture](02-architecture-and-security.md) §4 ports/adapters (protocol sketches, normalized result, conformance suite, training/inference separation) |
| 7. Minimal FastAPI + PostgreSQL + Docker Compose dev environment; training separate from online inference | 02 §5 (compose sketch, service split, profiles, offline training) and §4.2 |
| 8. Security boundaries for uploads, untrusted scan inputs, artifacts, worker isolation, secrets, audit | 02 §7 (boundary map B1–B11, threat/control/test, upload decision status, worker isolation trade-off) |
| 9. Migration from in-memory repository without breaking the frontend | [06](06-migration-and-acceptance.md) §1–§5 (strangler phases, seed migration, parity harness, adapter diff, method→endpoint map) |
| 10. Acceptance criteria and tests per implementation phase | 06 §6 (M0–M7, AT-0.1 … AT-7.6, gates G1–G7), §7 test inventory |
| Constraint: no file/ACL changes now | 01 §1.1 baseline hashes; 02 §7.3/B9; 06 §1.1; verified again at the end of this document set |
| Constraint: no dependencies / no backend implementation | No source file, `package.json` or dependency was touched; the backend appears only as design (02–06, `schema.sql`) |
| Constraint: no assumed undocumented fields | 01 §2 is read from source; every new field is marked “—” or derived; 03 §5 maps each current field; assumptions are listed in §3 |
| Constraint: graduation-project scale + reproducible AI experiments | 02 §1/§4.2/§5 (dataset hashes, seeds, evaluation runs, offline training), 06 M7 |
| Constraint: no Kubernetes/microservices without a concrete requirement | 02 §1 “one host”, §9 rejected technologies table |

The brief's deliverables map 1:1 to the files: current-state assessment (01), architecture diagram
(02 §2), ERD + data dictionary (03), API contract (04), state-transition spec (05), milestones +
acceptance tests (06), risks/assumptions/decisions (07).

---

## 2. Risk register

Likelihood/impact are qualitative for a one-developer graduation project.

| Id | Risk | L | I | Mitigation | Phase |
|---|---|---|---|---|---|
| R-01 | Status-string drift: API codes or renamed labels change the DOM (badges, filters, toasts) | M | H | adapter maps codes→exact current strings (03 §3); golden snapshot equality (AT-2.1/AT-5.2); browser checks assert visible text | M5 |
| R-02 | Synchronous→asynchronous mutation breaks the click-to-render flow (no loading state in the UI) | H | H | adapter awaits and polls before returning; top-level `await` for bootstrap; documented minimal `app.js` diff; fallback to in-memory via flag | M5 |
| R-03 | Same-origin requirement overlooked → off-origin browser check fails | M | H | same-origin `/api` proxy; check asserted in AT-5.8 and G2 | M5 |
| R-04 | Scan execution becomes async and the “Run demo” row does not show `Completed` immediately | M | M | demo adapter polls with a bounded budget; worker claims quickly; AT-5.5 | M4/M5 |
| R-05 | Strict transitions block the UI cycle button (`→ Resolved` without verification) | H | M | intentional; `scripts/browser-check.mjs` contains no `cycle-finding` click; frontend follow-up scheduled (06 §5.4); 409 message is actionable | M3/M5 |
| R-06 | Auth/roles invented or too coarse, blocking demo feasibility | M | M | demo auto-login + seeded user; role matrix in 04 §6; decision D-02/D-03; no auth UI in v1 | M2/M6 |
| R-07 | Snapshot/bootstrap is not viable beyond demo scale | L | M | bounded projection with truncation flags; per-collection endpoints exist; scale assumption A-03 documented | M2 |
| R-08 | CSV export differs (ordering/quoting/snapshot vs live) | M | M | byte-equality test AT-3.13; snapshot ordering rule (03 §4.6); client-side first in M5 | M3/M5 |
| R-09 | Worker isolation is weaker than required (docker-socket = root) | M | H | execution port; baseline hardening in M6; explicit non-goal and trade-off; real-scanner phase gated on stronger isolation | M6 |
| R-10 | Untrusted scan output / uploaded artifacts become an injection or RCE vector | M | H | normalize+validate adapter output; no HTML inline; content-type/nosniff/attachment; quarantine; no execution; B5/B6 controls | M4/M6 |
| R-11 | Model “AI” claims overstate reality (mock) → academic integrity/validity risk | M | H | `simulated`/`is_mock` fields; explicit UI banner (already present); evaluation runs from real datasets only; no fabricated metrics | M4/M7 |
| R-12 | Reproducibility claims not backed by seeds/hashes/environment | M | M | dataset_version.content_hash, evaluation_run.seed/environment, pinned artifacts (03 §4.5); AT-7.1…7.3 | M7 |
| R-13 | Migration loses legacy states (e.g. `Resolved` without verification) | L | H | backfill synthetic verification (06 §3.2); invariant tests AT-3.4 | M1 |
| R-14 | Scope creep: real scanners, PDF reports, uploads, Kubernetes | H | M | explicit non-goals (02 §1, §9); upload deferred D-16; PDF not in current product | all |
| R-15 | No VCS/CI in the repository; baseline not pinned to a commit | H | M | hashes in 01 §1.1; recommendation to `git init` + CI (D-18); `npm run verify` reused | M0 |
| R-16 | PostgreSQL/Docker unavailable in the current environment → schema unexecuted | H | L | stated in 01 A-06; SQL reviewed as design; M1 executes it first | M1 |
| R-17 | Evidence size/cost and PII in evidence | M | M | size caps, inline-vs-artifact rule, retention decision D-14 | M6 |
| R-18 | Audit claim “tamper-proof” overstated without hash chain | M | L | append-only grants/triggers now; optional hash chain documented as extension | M6 |
| R-19 | Single-maintainer operational complexity (compose + worker + DB + proxy) | M | M | one-host compose, DB-backed queue (no broker), single command target; ops docs in M7 | M7 |
| R-20 | Adapter abstraction becomes ceremony with only one implementation | M | L | conformance suite forces the seam; mock + demo adapters exercise it; no speculative adapters built | M4 |
| R-21 | Simulated/demo AI numbers are mistaken for real measurements in the thesis | M | H | `evaluation_run.data_origin`, `model_version.is_mock`, `analysis.simulated`, zero simulated evaluation rows in the seed, `dataOrigin` in every API response, AT-7.2/AT-7.7 and gate G8 | M1/M4/M7 |
| R-22 | Prompt provenance lost, making analyses irreproducible | M | M | `prompt_template_version` table (immutable, hashed), analysis pins the version id, adapter hash check (I-11), AT-4.7/AT-7.8 | M1/M4/M7 |

---

## 3. Assumptions (and what breaks if wrong)

| Id | Assumption | If wrong |
|---|---|---|
| A-01 | “ACL” = the static-path policy in 01 §8 plus the domain guards; there is no ACL config file | If an external ACL exists, the threat model and frozen-behaviour scope must be extended; re-review 01 §8 |
| A-02 | No source-code upload exists today; uploads are forward-looking | If uploads exist elsewhere, B6 must become a migration task, not a design note |
| A-03 | Single-tenant, demo-scale (≤ ~10³ findings) | Multi-tenancy needs `organization` scoping, RLS, per-tenant bootstrap limits; pagination-first UI needed |
| A-04 | Users/identities exist outside this repo (names only) | If not, local credential management and password policy become required (D-02, X-05) |
| A-05 | “Authorized target” = ticked attestation, no uploaded document | Compliance may require document storage + verification workflow (D-17) |
| A-06 | Docker + PostgreSQL available at implementation time (not now) | M1 blocked; schema/DDL remain design-only until then |
| A-07 | The demo seed stays available for parity and offline demo | If the seed is removed, parity harness and browser checks need a different fixture source |
| A-08 | Development stays loopback-only; TLS only on real deployment | Public exposure requires proxy hardening, cookies `Secure`, HSTS, rate limits — M6 additions |
| A-09 | Tests must run without external network/scanners/models | Any network-dependent test must be mocked; egress tests are allowlist-unit-tests until a real adapter exists |
| A-10 | Python 3.12+/PostgreSQL 16+ acceptable; exact pins at implementation | If a fixed academic toolchain is mandated, pin earlier and document deviations |
| A-11 | Prompt templates are seeded/code-defined immutable versions in the MVP; no editing UI/API | If template editing is required, add an admin workflow and versioning tests before M4 |
| A-12 | The seed contains no evaluation runs; simulated demo metrics live only on `model_version.metrics` with `is_mock=true` | If simulated evaluation rows are added later, every consumer must filter/label `dataOrigin` and G8 must be extended |

---

## 4. Open decisions register

Status is explicit: **PENDING** = needs supervisor approval; **RECORDED** = developer default
recorded in this plan and revocable; **MERGED** = kept only for ID stability. No supervisor
approval is claimed anywhere in this package.

Class: **S** = supervisor approval required, **D** = developer can decide, **X** = safe to defer.
“Blocks” lists the milestone that cannot start/complete without it.

### 4.1 Core decisions (D-01 … D-18)

| Id | Decision | Class | Status | Blocks | Recommendation / default | Gate |
|---|---|---|---|---|---|---|
| D-01 | Meaning of “ACL” in the brief | S | PENDING | M1 sign-off (not schema) | static-path policy + domain guards (07 A-01) | M1-entry |
| D-02 | Authentication mechanism | S | PENDING | M2, M6 | session cookie + seeded demo user; OIDC later | M2-entry |
| D-03 | Platform/project role model | S | PENDING | **M1** (enums + seed memberships) | ADMIN/ANALYST/VIEWER + project OWNER/ANALYST/VIEWER | M1-entry |
| D-04 | ID strategy | D | RECORDED | M1 | prefixed ULID text ids; legacy ids only in the seed | — |
| D-05 | `DRAFT` scan-job state | D | RECORDED | — | omit; UI caption is copy | — |
| D-06 | Scan execution + queue model | D | RECORDED | M3/M4/M6 | DB-backed queue (`FOR UPDATE SKIP LOCKED`) + worker; no broker | M4-entry |
| D-07 | Seed `Running` scan with no live worker | D | RECORDED | **M1 seed fixture** | keep, `worker_id='seed'`, excluded from lease recovery | M1-entry |
| D-08 | Verification evidence strictness | S | PENDING | M3 (schema CHECK if stricter) | provisional default: evidence **or** notes (C-12) | M3-entry |
| D-09 | Report scope | S | PENDING | M3 (seed report rows if changed) | provisional default: snapshot all project findings | M3-entry |
| D-10 | Artifact storage | D | RECORDED | M6 | port + local volume; S3 later | M6-entry |
| D-11 | Queue technology | X | **MERGED → D-06** | — | do not reuse this ID; queue choice lives in D-06 | — |
| D-12 | Inference serving | D | RECORDED | M4/M7 | mock adapter now; HTTP container later | M4-entry |
| D-13 | Training location | D | RECORDED | M7 | `training/` subdirectory + compose profile | M7-entry |
| D-14 | Retention/erasure | S | PENDING | M6/M7 (before storing evidence) | decide policy before evidence exists | M6-entry |
| D-15 | API versioning | D | RECORDED | M2 | `/api/v1` path | M2-entry |
| D-16 | Source-code uploads | S | PENDING | Scope | out of scope; B6 design recorded | scope-now |
| D-17 | Target authorization evidence | S | PENDING | M3/compliance | provisional default: attestation only; documents later | M3-entry |
| D-18 | Version control / CI | D | RECORDED | M0/M1 process | `git init` + baseline commit + CI (`npm run verify`, `pytest`) | M1-entry |

### 4.2 Formally registered missing decisions (X-01 … X-06)

| Id | Decision | Class | Owner | Depends on | Blocks | Gate / evidence needed |
|---|---|---|---|---|---|---|
| X-01 | Frontend-change approval for Phase E (import switch, async handlers, cycle-button behaviour) | S | supervisor | D-02, D-03 | **M5** | written approval; until then the frontend stays untouched and M5 is planned only |
| X-02 | Is a real scanner in thesis scope? (vs demo adapter only) | S | supervisor | D-06, D-10 | M4/M6 scope | scope decision; if yes, B4 egress + B5 artifacts must be implemented before any scan |
| X-03 | Dataset source, licence and provenance for the real evaluation | S | supervisor | — | M7 | named dataset + licence text + provenance in `dataset` row (AT-7.1/7.9) |
| X-04 | Reproducibility target and metric (which number, tolerance, environment) | S | supervisor | X-03 | M7 | primary metric + seed + tolerance recorded (AT-7.2/7.9) |
| X-05 | User provisioning + password/credential policy (only if D-02 local auth) | S | supervisor | D-02 | M2/M3 | policy statement; until then seeded accounts have no password hash and demo mode is feature-flagged |
| X-06 | Project-membership management surface (API only vs UI later) | D | developer | D-03 | M3 | recorded here: API endpoints EP-28/29/47/48, no UI in MVP (04 P-07) |

### 4.3 Gate matrix (what must be true to start/close a milestone)

| Gate | Required decisions | Other entry conditions |
|---|---|---|
| M1-entry | D-01 (sign-off), D-03, D-07, D-18 | Docker + PostgreSQL installed; `git init` + baseline commit; seed manifest approved |
| M2-entry | D-02, D-15, X-05 (if local auth) | M1 green; auth feature flag documented |
| M3-entry | D-08, D-09, D-17, X-06 (recorded) | M2 green |
| M4-entry | D-06 (merged), D-12, X-02 (scope answer) | M3 green; adapter conformance suite defined |
| M5-entry | **X-01**, D-02, D-03 | M4 green; otherwise not started |
| M6-entry | D-10, D-14, X-02 (if real scanner) | M5 green or explicitly waived by supervisor |
| M7-entry | X-03, X-04, D-13 | M6 green; evaluation table still empty (no simulated rows) |

### 4.4 Remaining supervisor decisions (currently pending — no approvals implied)

D-01, D-02, D-03, D-08 (confirm provisional default), D-09 (confirm provisional default), D-14,
D-16, D-17, **X-01, X-02, X-03, X-04**, and X-05 if local auth is chosen. Everything else is a
developer default recorded above. M1 needs only D-01, D-03, D-07 and D-18 (plus environment);
D-02/D-08/D-09/D-17 and X-01 can safely remain pending until their gates, but must not be silently
assumed.

### 4.5 Developer-recorded defaults (revocable at any time)

Prefixed ULIDs (D-04); no DRAFT jobs (D-05); DB queue/worker (D-06, D-11 merged); seeded `Running`
scan exception (D-07); local artifact store (D-10); mock inference (D-12); `training/` subdirectory
(D-13); `/api/v1` (D-15); `git init` + CI (D-18); membership API only (X-06). Changing any of these
requires updating the affected documents + fixtures, not just a code change.

---

## 5. Questions that must be answered before their gates

| # | Question | Decision(s) | Gate |
|---|---|---|---|
| 1 | Does “current ACL must remain unchanged” refer only to the static-path policy (dot-segment denial incl. `.dsh-acl-recovery`, realpath containment, GET/HEAD-only, 400/403/404/405), or is there another access-control configuration outside this repository? | D-01 | M1-entry |
| 2 | Who are the users, where do they come from, what roles does the evaluation build need, and is demo-only identity acceptable? | D-02, D-03, X-05 | M1/M2-entry |
| 3 | Is the Phase E frontend change approved (repository switch, async handlers, cycle-button behaviour)? | X-01 | M5-entry |
| 4 | Preserve the demo `Running` scan and all-project-findings report semantics exactly, or accept cleaner behaviour? | D-07 (recorded), D-09 | M1/M3-entry |
| 5 | Which parts are actually in thesis scope: real scanner, uploads, training? | X-02, D-16, D-06 | M4/scope |
| 6 | What exactly must be reproducible — which dataset, licence, metric and tolerance? | X-03, X-04 | M7-entry |

Until answered, the provisional defaults in §4.1 are used for planning only; they are **not
approvals** and any change must update the documents, seed manifest and tests together.

---

## 6. Compliance statement for Phase 2

- **No frontend, dependency, ACL or recovery artifact changed:** baseline hashes are recorded in
  01 §1.1 and re-checked in 08 §3; `package.json` is unchanged; nothing under `node_modules`.
- **Documentation-only remediation:** this round changed only files under `docs/phase2/` (logged in
  [08](08-remediation-change-log.md)); `schema.sql` was not executed.
- **No supervisor approval invented:** every supervisor decision is marked PENDING in §4, and the
  provisional defaults are explicitly labelled as planning defaults.
- **No undocumented field assumed:** new fields are marked new/derived in 03 §4 and mapped in 03 §5;
  every claim about the current system cites a file/line in 01; uncertainties are listed in
  01 §10, 03 §8, 07 §3.
- **No Kubernetes/microservices:** rejected with reasons in 02 §9; one host, compose, modular
  monolith, one worker.
- **Graduation-project fit:** single-developer operations, deterministic demo, offline testability,
  model/dataset/prompt provenance, simulated-vs-measured separation, and a reproducible offline
  training path (02 §4.2, 06 M7).

---

## 7. Domain vocabulary (one page)

| Term | Meaning in SENTRIX | Not to be confused with |
|---|---|---|
| **Project** | An authorized engagement containing targets, scans, findings and reports | A Jira project |
| **Target** | One explicitly authorized asset (hostname/URL) with a declared scope | Any host the scanner can reach |
| **Authorization attestation** | The recorded “I have authorization” statement, actor, time and scope snapshot | An uploaded legal document (D-17) |
| **Scan profile** | A named configuration (external attack surface, API authorization, cloud configuration) that maps to an adapter config | A scanner binary |
| **Scan job** | The user's configured assessment (target + profile), with a lifecycle | A single execution |
| **Scan run** | One execution attempt of a job, with worker, progress, timing and outcome | The job itself |
| **Observation** | Adapter-normalized scanner output, before dedup/severity mapping | A finding |
| **Finding** | The domain record of a potential issue: severity, status, provenance, history | A scanner alert (may be a duplicate) |
| **Evidence** | Immutable support for a finding: text excerpt, HTTP exchange, config snippet, file, screenshot | A note or comment |
| **AI analysis** | A model-version-pinned, human-reviewable assessment of a finding | A finding, a verdict, a resolution |
| **Remediation task** | Assigned work to fix a finding | Proof the finding is fixed |
| **Verification** | Immutable record (outcome, method, verifier, evidence/notes) that can resolve or reject | A task status |
| **Report** | Snapshot of project findings at generation time, publishable and exportable | A live view |
| **Audit event** | Append-only record of who did what, when, with which request id and outcome | Application log |
| **Model version** | Immutable model artifact + stage + metrics + training dataset reference | A model name |
| **Dataset version** | Immutable dataset snapshot with content hash and label distribution | A spreadsheet export |
| **Evaluation run** | One model-version × dataset-version measurement with seed/environment | Training |
