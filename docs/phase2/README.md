# SENTRIX — Phase 2: Backend Architecture and Data Contract

Planning package plus implemented M1–M6 records for the SENTRIX local demo.
Canonical source now lives under [`frontend/`](../../frontend/README.md),
[`backend/`](../../backend/README.md), and [`database/`](../../database/README.md).

| | |
|---|---|
| Repository baseline | Local five-VM demo, implemented through M6 |
| Test baseline | Backend **49 passed**; frontend Node suite 31 pass, 1 skipped (EPERM symlink test in this sandbox), 0 fail |
| Source of truth | `frontend/` (UI/adapter), `backend/` (API/worker/AI/deploy), `database/` (schema/migrations/seed) |
| Scope | Architecture, data contract, security boundaries, migration plan, milestones and acceptance tests |
| Counts | **28 tables** (25 + `artifact` + shared auth state), 18 enums, 49 API operations, 51 seed rows, 13 frontend browser checks |
| Decisions | 18 core decisions (D-01…D-18; D-11 merged into D-06) + 6 registered missing decisions X-01…X-06; X-01 approved local demo, others recorded per milestone |

## Deliverables

| # | Deliverable | Document |
|---|---|---|
| 1 | Current-state assessment: files, entities, fields, relationships, state transitions, repository methods, frontend workflows | [01-current-state.md](01-current-state.md) |
| 2 | Architecture diagram, adapters/interfaces, dev environment, security boundaries | [02-architecture-and-security.md](02-architecture-and-security.md) |
| 3 | ERD, schema, data dictionary, migration mapping | [03-data-model.md](03-data-model.md) + [`database/schema.sql`](../../database/schema.sql) |
| 4 | REST API contract: endpoints, payloads, validation, errors, authorization, concurrency | [04-api-contract.md](04-api-contract.md) |
| 5 | Domain state-transition specification (scan jobs, findings, remediation, verification) | [05-state-transitions.md](05-state-transitions.md) |
| 6 | Migration plan, M1 ticket, exact seed manifest, milestones and acceptance tests | [06-migration-and-acceptance.md](06-migration-and-acceptance.md) + [`database/seed-manifest.json`](../../database/seed-manifest.json) |
| 7 | Risks, assumptions, decision register (D-01…D-18, X-01…X-06), traceability, glossary | [07-risks-assumptions-decisions.md](07-risks-assumptions-decisions.md) |
| 8 | Remediation change log (C1–C12), remaining supervisor decisions, validation report | [08-remediation-change-log.md](08-remediation-change-log.md) |

## Reading order

1. **01** — what exists today, with file/line evidence and the 14 repository methods.
2. **02** — what we are building and where the trust boundaries are.
3. **03 + `schema.sql`** — the system of record.
4. **04** — the HTTP contract the frontend adapter will speak.
5. **05** — the rules that must not be softened (especially: verification resolves a finding, not task closure).
6. **06** — how to get there phase by phase, with tests that prove it; §3.4 + `seed-manifest.json`
   are the M1 test oracle.
7. **07** — what is still undecided, who decides, and which milestone each decision gates.
8. **08** — what changed in this remediation round and how it was validated.

## The six decisions that shape everything

1. **Same origin.** The API lives under `/api/v1` behind a dev proxy on `:3000`; the static server
   (`server.mjs`/`static.js`) is unchanged and keeps its ACL. This preserves the browser check's
   “no off-origin requests” assertion.
2. **Scan job ≠ scan run.** Jobs are user-configured assessments; runs are execution attempts.
   The current single mutable `scans` row cannot represent retries, progress or workers.
3. **Verification is a record, not a task flag.** A finding reaches `RESOLVED` only through an
   immutable verification (`VERIFIED`); closing a remediation task never changes the finding.
4. **Evidence becomes rows/artifacts** with provenance, hashes and kinds instead of one text field.
5. **Model versions, prompt-template versions and dataset versions are first-class** so AI analyses
   and experiments are reproducible and training stays offline, away from online inference.
6. **Simulated ≠ measured.** `evaluation_run.data_origin`, `model_version.is_mock` and
   `analysis.simulated` keep demo numbers visibly separate from real experimental results; the seed
   contains zero evaluation runs.

## What is deliberately absent

No backend code, migrations, dependency, Docker file or CI config. `schema.sql` is a reviewed
design artifact that has not been executed (PostgreSQL is not installed in this environment). The
frontend remains untouched; the Phase E adapter diff is specified but not applied and is gated on
supervisor approval **X-01**. No supervisor approval is claimed anywhere; pending items are marked
PENDING in [07 §4](07-risks-assumptions-decisions.md#4-open-decisions-register).

## Baseline evidence

- Existing suite re-run for this package: `node --test --test-isolation=none` → 27 tests,
  26 pass, 1 skipped, 0 failed.
- File hashes (SHA-256, first 16 hex chars) captured before writing this package are in
  [01 §1.1](01-current-state.md#11-file-inventory-sha-256-prefix-first-16-hex-chars-captured-before-this-document-set-was-written);
  they are re-checked after the package is written to prove nothing existing changed.
- The 13 CDP browser checks and the assertions that matter for parity are summarised in
  [01 §1.2](01-current-state.md#12-verification-semantics-that-later-phases-must-keep-working);
  they are treated as acceptance tests for Phase E.

## Next step

Answer the six gated questions in [07 §5](07-risks-assumptions-decisions.md#5-questions-that-must-be-answered-before-their-gates)
(ACL meaning, identity/roles, frontend-change approval, demo scan/report semantics, thesis scope,
reproducibility target). Then close the M1-gating decisions (D-01, D-03, D-07, D-18), install the
toolchain, and run the M1 ticket in
[06 §6](06-migration-and-acceptance.md#6-milestones-and-acceptance-tests) with
[`seed-manifest.json`](../../database/seed-manifest.json) as the acceptance oracle. The full validation report and
change log are in [08](08-remediation-change-log.md).
