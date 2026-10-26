# SENTRIX — Phase 2 · Remediation Change Log and Validation Report

| | |
|---|---|
| Status | Documentation-only remediation round. No backend, frontend, dependency, ACL, permission or recovery artifact was changed; `schema.sql` was not executed. |
| Inputs | Decision-Gate Review findings C1–C12, duplicate D-06/D-11, missing X-01–X-06, and the M1 gate recommendations. |
| Outputs | Updated `docs/phase2/` package, this change log, remaining supervisor decisions, revised M1 ticket + exact seed manifest, validation report. |

---

## 1. Change log — every gap from the gate review

`C*` = finding IDs from the Decision-Gate Review; `O*` = objectives from the remediation brief.

| # | Gap | Resolution | Files / sections |
|---|---|---|---|
| C1 / O2 | D-06 and D-11 were the same decision | D-11 marked **MERGED → D-06** and reserved (not reused); D-06 now covers “scan execution **and** queue model”. | 07 §4.1; 02 §9 |
| C2 / O3 | Register did not classify decisions and lacked X-01–X-06 | Register now has Class (S/D/X), Status (PENDING/RECORDED/MERGED), Blocks, Recommendation, Gate; X-01–X-06 registered with owner, dependencies and gates; no approval invented. | 07 §4.1–§4.5 |
| C3 / O10 | “EP-30…EP-46” implied non-existent EP-43/44/45 | Catalogue explicitly lists the 49 defined ids and states EP-43/44/45 are intentionally unused; ranges removed from normative text. | 04 §2, §6 |
| C4 / O9 | AT-1.8 (“demo graph matches 01 §2”) was not measurable | Replaced with manifest-equality AT-1.8 (51 rows, ids, counts, key fields, ordering, exceptions), plus AT-1.15 forbidden-empty sets. | 06 M1; `seed-manifest.json` |
| C5 / O4 | Seed mapping ambiguities (profile, observations, evaluation rows, status history) | Mapping table now defines every case; `scan_observation = 0`, `evaluation_run = 0`, exactly 3 creation events; `profile` → `profile_id`; legacy inconsistencies documented as expected exceptions. | 06 §3, §3.4; 05 §4.4; 01 Q21/Q22 |
| C6 / O5 | `evaluation_run` could be mistaken for a real measurement | Added `data_origin` enum (`SIMULATED`/`MEASURED`) with CHECK requiring seed/finished/metrics for MEASURED; `/evaluations` always returns `dataOrigin`; seed has zero evaluation runs; M7 accepts only MEASURED. | `schema.sql`; 03 §4.5/§6; 04 §4.12; 06 M7; 02 B12; gate G8 |
| C7 / O6 | Prompt hash stored but no template version record | Added immutable `prompt_template` + `prompt_template_version` tables (content + hash); analysis pins `prompt_template_version_id`; adapter receives the id and hash must match (I-11). | `schema.sql`; 03 §4.5/§6; 02 §4.2; 04 §4.9; 06 AT-4.7/AT-7.8 |
| C8 / O7 | Concurrency rule did not cover scan jobs/targets | `scan_job.updated_at` added; target representation exposes `updatedAt`; If-Match coverage table per endpoint; AT-1.12/AT-3.18. | `schema.sql`; 04 §1.2, §3.2–§3.3, §4.6–§4.10; 03 I-13; 06 M3 |
| C9 / O8 | Auth endpoints absent from M2 plan | M2 deliverables + AT-2.9/2.10 add EP-50/51, CSRF, session, `/me`; demo auto-login explicitly conditional on pending D-02. | 06 M2; 04 §4.14 |
| C10 / O8 | No user/membership provisioning anywhere | Added EP-28/29/47/48 (membership) and EP-52/53 (ADMIN user provisioning), guards (last owner/last admin), errors, authz rows, M3 tests AT-3.16/3.17. | 04 §2/§4.14/§5/§6/§7; 06 M2/M3; 07 X-06 |
| C11 / O4/O9 | AT-7.2 contradicted sample seed metrics; no exact fixture | AT-7.2 now applies only to `MEASURED` runs starting from an empty evaluation table; seed manifest removes evaluation rows; AT-7.7/7.9 enforce separation and dataset/licence decisions. | 06 M7; seed manifest; 07 X-03/X-04 |
| C12 / O3 | Reproducibility target and dataset not registered | X-03 (dataset/licence/provenance) and X-04 (metric/tolerance) registered as supervisor decisions gating M7. | 07 §4.2, §4.3 |
| O1 | C1–C12 resolution | All twelve addressed above; no remaining unresolved contradiction known at suite level. | this document §1 |
| O10 | Links / refs / consistency | Re-validated all internal links, endpoint ids, schema counts, decision ids, AT ids and manifest counts; results in §5. | §5 |

**Supporting additions made in the same round**

- D-01…D-18 statuses and gate mapping (07 §4.3), plus “remaining supervisor decisions” (07 §4.4).
- M0/M1–M7 milestone plans updated: M1 measurable manifest oracle, M2 identity, M3 membership and
  provisioning, M5 gated on X-01, M7 measured-only evaluation.
- P-05 wording corrected: frontend change is **requested, not approved** (X-01).
- README counts/scope updated (25 tables, 18 enums, 49 operations, 51 seed rows).

---

## 2. Decision register after remediation

- **Core decisions:** D-01…D-18 all have Class, Status, Blocks and Gate. D-11 is MERGED into D-06
  and reserved. Developer defaults are RECORDED (D-04, D-05, D-06, D-07, D-10, D-12, D-13, D-15,
  D-18) and revocable by updating the documents; supervisor items are PENDING.
- **Registered missing decisions:** X-01 frontend approval (S, M5), X-02 real-scanner scope (S,
  M4/M6), X-03 dataset/licence/provenance (S, M7), X-04 reproducibility target (S, M7), X-05
  credential policy (S, M2/M3 if local auth), X-06 membership surface (D, recorded: API only, M3).
- **No approvals invented:** every supervisor item is marked PENDING; provisional defaults are
  explicitly labelled planning defaults and may not be treated as sign-off.

---

## 3. Remaining supervisor decisions (all pending)

| Decision | Why it gates | What is needed |
|---|---|---|
| D-01 ACL meaning | M1 sign-off / constraint interpretation | written confirmation that static-path policy + domain guards are the intended “ACL” |
| D-02 authentication | M2/M6 and M5 demo login | session-cookie vs OIDC vs demo-only, and demo auto-login acceptance |
| D-03 role model | M1 enums + seed memberships | confirm ADMIN/ANALYST/VIEWER + project OWNER/ANALYST/VIEWER or a reduced set |
| D-08 verification evidence | M3 (schema CHECK if stricter) | confirm “evidence or notes” default or require evidence row |
| D-09 report scope | M3 (+ seed report rows if changed) | confirm all-project-findings snapshot default |
| D-14 retention/erasure | M6/M7 before storing evidence | retention policy for evidence/audit |
| D-16 uploads | scope | confirm source-code uploads are out of thesis scope |
| D-17 authorization evidence | M3/compliance | attestation-only vs uploaded authorization document |
| X-01 frontend change | M5 | written approval for the Phase E `app.js` change |
| X-02 real scanner | M4/M6 scope | demo-adapter-only or a real scanner (with B4/B5 controls) |
| X-03 dataset/licence | M7 | named dataset + licence + provenance |
| X-04 reproducibility target | M7 | primary metric, seed and tolerance |
| X-05 credential policy | M2/M3 if local auth | password policy/hashing if D-02 chooses local credentials |

---

## 4. Revised M1 ticket

**Title:** M1 — Database, migrations, seed manifest and least-privilege roles.
**Goal:** a reproducible PostgreSQL schema and demo fixture, with no API/frontend code.
**Entry:** D-01 signed; D-03 answered; D-07/D-18 recorded; Docker + PostgreSQL installed;
`git init` + baseline commit; seed manifest approved. **No supervisor approval is assumed.**
**Deliverables:** Alembic baseline; `schema.sql` applied; `app.seed_demo` driven by
`seed-manifest.json`; `--verify` mode; roles `sentrix_app`, migration role, `sentrix_readonly`,
`sentrix_eval`; compose `db`; schema-drift check.

**Exact seed fixture (oracle):** [`seed-manifest.json`](../../database/seed-manifest.json) — **51 rows**:
3 profiles (reference), 5 users (3 analysts + 1 admin + inactive `user-system`), 3 projects,
3 memberships, 4 targets, 3 attestations, 3 jobs, 3 runs, **0 observations**, 3 findings,
3 evidence rows, 3 creation status events, 1 analysis, 1 prompt template + 1 version, 2 models +
2 versions, 1 dataset + 1 version, **0 evaluation runs**, 1 remediation, **0 verifications**,
1 report + 2 snapshot rows, 2 audit events. Fixed ids, fixed UTC timestamps, deterministic order,
idempotent upsert; two legacy quirks are explicitly expected (bola Confirmed vs task In Progress;
debug job/target mismatch).

**Acceptance (all measurable):** AT-1.1–AT-1.15 in
[06 §6](06-migration-and-acceptance.md#6-milestones-and-acceptance-tests): 25 tables / 18 enums /
3 triggers; upgrade/downgrade round-trip; FK/unique/CHECK/trigger constraints; manifest equality
and idempotent re-run; one production model version; prompt-version immutability; evaluation
provenance CHECK; concurrency columns; schema drift; least-privilege roles; forbidden-empty seed
sets. **Exit:** every AT-1.x green, existing 27 Node tests unchanged (26 pass/1 skip/0 fail), no
source file modified.

---

## 5. Validation report

**Method:** static/document checks only — no database, Docker, backend, scanner or inference
service was started (they remain uninstalled/unverified). Source hashes and the Node suite were
re-checked.

| Check | Result |
|---|---|
| Baseline source files changed | **0** of 15 (SHA-256 prefixes in 01 §1.1 re-checked) |
| Node suite (`node --test --test-isolation=none`) | 27 tests, 26 pass, 1 skip (`EPERM` symlink), 0 fail |
| Schema definition | 25 `CREATE TABLE`, 18 `CREATE TYPE`, 3 `CREATE TRIGGER` |
| API catalogue | 49 operations defined (EP-01…EP-29, EP-30…EP-42, EP-46…EP-48, EP-50…EP-53); EP-43/44/45 reserved by design |
| Undefined endpoint references | none (EP-43/44/45 appear only as declared reserved ids) |
| Decision register | 18 D ids + 6 X ids defined; every D/X reference resolves; D-11 merged, not reused |
| Seed manifest | valid JSON; 26 count entries; sum of rows = 51 = declared total; ids length = count for every table |
| Acceptance tests | 81 table-defined + 3 M0 text-defined = 84; no duplicated AT ids; no undefined AT references |
| Internal links | all markdown links resolve; anchors checked against current headings |
| Cross-document consistency | status enums, resolution path, audit sets, prompt pinning, concurrency fields, evaluation provenance and milestone gates verified as described below |
| Environment | Docker/PostgreSQL/psql absent; git installed but repo absent; PostgreSQL, Docker, backend, scanners and AI inference are **not operational** |

**Consistency spot checks**

| Pair | Result |
|---|---|
| schema ↔ API | prompt template id/hash, `evaluation_run.dataOrigin`, `scan_job.updatedAt`, target `updatedAt`, report `position`, users/membership fields all present in both |
| schema ↔ states | verification-backed resolution, one active run, one live analysis, remediation transitions, state enums unchanged/consistent |
| API ↔ states | EP-36 rejects `RESOLVED`; EP-40/EP-46 are the only resolution path; If-Match coverage matches the updated resources |
| tests ↔ contract | AT-2.9/2.10 auth, AT-3.16/3.17 provisioning, AT-3.18 concurrency, AT-4.7 prompt, AT-7.2/7.7 measured-only all correspond to defined endpoints/rules |
| milestone dependencies | M1 entry conditions, M2 auth, M3 membership/provisioning, M5 X-01 gate, M7 X-03/X-04 gate mapped in 07 §4.3 |

**Limitations:** `schema.sql` was not executed (no PostgreSQL); the browser check was not run (no
server/Edge in this environment); the seed manifest is a design oracle, not a verified database
state; PostgreSQL/Docker/backend/scanner/inference operationality is **not claimed**.

**Residual items:** supervisor decisions listed in §3 remain PENDING; EP-43/44/45 are intentionally
reserved; the two legacy seed quirks are expected fixtures; schema execution and all runtime tests
belong to M1 and are unverified here.

---

## 6. Validation evidence (commands used, read-only)

- `Get-FileHash` over the 15 baseline source files vs 01 §1.1 → 0 changes.
- `node --test --test-isolation=none` → 27/26/1/0.
- Node static validator over `docs/phase2`: markdown links/anchors, `EP-*` catalogue rows and
  references, `CREATE TABLE/TYPE/TRIGGER` counts, AT ids, D/X ids, JSON manifest parse and counts.
- Toolchain probe: `docker`, `docker-compose`, `psql`, `postgres` absent; `git` present; no `.git`.
- No database, migration, browser or server process was started; no dependency installed.
