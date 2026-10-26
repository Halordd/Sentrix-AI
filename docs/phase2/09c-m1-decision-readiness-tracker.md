# SENTRIX M1 — Decision & Readiness Tracker

| Field | Value |
|---|---|
| Document ID | `SENTRIX-M1-TRACKER-001` |
| Version | 1.35 |
| Basis | `SENTRIX-M1-ASR-001` v1.3 |
| Status | `ACCEPTED — LOCAL DEMO ONLY` |
| Execution authorization | **LOCAL DEMO ONLY — NO PRODUCTION / EXTERNAL SCOPE** |
| Formal approvals | **Local project-owner acceptance recorded in `SENTRIX-M1-GOV-001`** |
| Infrastructure/database changes | **M1 local acceptance; AI path verified; pytest 7 passed; UI smoke 8 views passed** |
| Evidence collected for this update | **AI-backed analysis 201; pytest 7 passed; UI_SMOKE_PASSED; acceptance PASSED; worker real active** |
| Date prepared | 2026-10-23 (Asia/Saigon) |
| Revision | 1.35 — M1 local acceptance recorded; production/external use remains not approved |

> **Revision note v1.34 → v1.35:** AI path verified through production API: `POST /api/v1/findings/finding-bucket/analyses` returned 201 with model `sentrix-ai-mock` and its summary. UI smoke passed overview/projects/scans/findings/intelligence/attack/reports/models/settings. `pytest` 7 passed (seed oracle + API contract). `scripts/m1/acceptance.py` passed again. Worker `sentrix-worker-real` is active and the placeholder is inactive. Local M1 acceptance recorded in `docs/phase2/12-m1-governance-record.md`; production/external use remains not approved.
>
> **Revision note v1.33 → v1.34:** added `ai_service/main.py` with `/health` and `/v1/analyze`; backend `create_analysis` calls it with a 3s timeout and falls back to deterministic output. Local `/v1/analyze` returned 200; from VM01 it timed out until UFW allows `8001`, and the fallback path still returned 201. `scripts/m1/acceptance.py` passed health/db, bootstrap counts, scan profiles, UI 200, and VM03 existing `/health`.
>
> **Revision note v1.32 → v1.33:** added `api.js` methods for remediation, verification, report, and publish. Added `worker/real_worker.py`; it runs on VM04, polls `/api/v1/bootstrap`, claims a `Queued` scan, and calls `/scans/{id}/run`. End-to-end test completed `scan-fda6bdc6d02d` and created `finding-47bbbfe9d20f`; tracer scan/run/finding/evidence/event removed. Seed counts restored to scan_job 3, scan_run 3, finding 3, evidence 3, event 3.
>
> **Revision note v1.31 → v1.32:** added `POST /api/v1/findings/{id}/remediations`, `POST /api/v1/remediations/{id}/verify`, `POST /api/v1/reports`, and `POST /api/v1/reports/{id}/publish`. Verification closes the remediation and moves the finding to `RESOLVED` with a status event. Tracer remediation, verification, status event, and report were removed; seed counts are remediation 1, verification 0, event 3, report 1.
>
> **Revision note v1.30 → v1.31:** added `PATCH /api/v1/findings/{id}/status` (updates finding, appends one `finding_status_event`) and `POST /api/v1/findings/{id}/analyses` (fixed mock model/prompt). Status test `CONFIRMED → IN_PROGRESS` returned 200 and was reverted; tracer event removed with the append-only trigger temporarily disabled. Analysis test returned 201 on `finding-bucket`; tracer analysis removed. Workspace board: `.scratch/sentrix-writeflow/README.md`.
>
> **Revision note v1.29 → v1.30:** added `POST /api/v1/targets`, `POST /api/v1/scans`, and `POST /api/v1/scans/{id}/run`. The run path inserts a scan run, finding, inline evidence, and status event in one transaction. Tracer target/scan/finding rows were removed by temporarily disabling append-only triggers as the table owner; counts reverted to target 4, scan_job 3, scan_run 3, finding 3, evidence 3, status event 3.
>
> **Revision note v1.28 → v1.29:** the UI now fetches `/api/v1/bootstrap` (verified by Nginx access log) and renders PostgreSQL seed data; `api.js` supplies the adapter. `POST /api/v1/projects` returns 201 and persisted a tracer project (deleted afterward; project count remains 3). Other UI mutations remain read-only. Headless Edge captured `ui-check.png`.
>
> **Revision note v1.27 → v1.28:** Juice Shop was recreated with `--network host`, removing the Docker NAT/UFW forward-chain conflict. It listens on `*:3000`; UFW allows LAB `.10` and host `.1`. Verification: `HTTP 200` from VM04 and from Windows `http://10.20.20.20:3000/`. All five VM services are now operational locally.
>
> **Revision note v1.26 → v1.27:** production API was restarted and returns seeded `/api/v1/projects`, `/api/v1/findings`, and `/api/v1/reports`. VM04 already had an active `sentrix-worker.service` placeholder at `/opt/sentrix-worker/worker.py` with idle heartbeats; no new worker service was installed. VM05 Juice Shop container is up on `10.20.20.20:3000`, but HTTP from VM04/VM05 is blocked by UFW pending a worker-source allow rule.
>
> **Revision note v1.25 → v1.26:** `backend/app/seed_demo.py` was run as `sentrix_migrator`; all 25 table counts sum to **51**. A temporary API on `127.0.0.1:8001` returned seeded `/api/v1/projects`, `/api/v1/findings`, and `/api/v1/reports` data. The production `sentrix-api` systemd service still runs the previous code until restarted. No worker or lab firewall rule yet.
>
> **Revision note v1.24 → v1.25:** `sentrix-api.service` is enabled and active; `/health` returns 200. From Windows, `http://10.20.10.10/` returns 200 and `http://10.20.10.10/api/v1/scan-profiles` returns 200 with the three scan profiles. VM01 app stack is working end-to-end at the infrastructure layer. No seed data, VM04 worker, or VM05 lab firewall rule yet.
>
> **Revision note v1.23 → v1.24:** system Nginx site is live on port 80. `http://10.20.10.10/` serves the SENTRIX UI and `http://10.20.10.10/api/v1/scan-profiles` returns HTTP 200 with the three scan profiles. The temporary port-3000 static server and port-8080 user Nginx were stopped. The nohup API process was stopped so the staged `sentrix-api.service` can bind port 8000; API is offline until the systemd unit is installed. No seed data yet.
>
> **Revision note v1.22 → v1.23:** backend FastAPI was started on VM01 at `127.0.0.1:8000`; `/health`, `/health/db`, and `/api/v1/scan-profiles` pass. A user-level Nginx reverse proxy was started on VM01 `10.20.10.10:8080` and returns UI 200 plus proxied API 200. System Nginx on port 80 still serves its default page; the SENTRIX site config is staged but not installed (sudo required). VM05 Juice Shop container is running, but lab HTTP is blocked pending firewall rules. No seed data yet.
>
> **Revision note v1.21 → v1.22:** schema and grant checks remain green. A temporary static frontend server was started on VM01 at `10.20.10.10:3000`; direct Windows access is blocked by UFW, but an SSH local tunnel returned HTTP 200. VM03 AI service responds on `/health` and `/docs` from VM01. VM05 listens on LAB `10.20.20.20:3000` but HTTP timed out locally; Docker access is denied without sudo. VM04 has no worker service. No seed data or backend code yet.
>
> **Revision note v1.20 → v1.21:** migrator access was established and `schema.sql` was applied to `sentrix` as `sentrix_migrator`. Verification: 25 public tables, 18 enums, 3 non-internal triggers, owner `sentrix_migrator`, 3 seeded `scan_profile` rows from the schema, app SELECT works, and app `UPDATE audit_event` is denied after grant hardening. No application seed data yet.
>
> **Revision note v1.19 → v1.20:** migrator HBA rules are present (rules 8 and 9, currently duplicated) and match `sentrix_migrator` from VM01; `psql -w` returns `no password supplied`, not an HBA error. The VM01 `.pgpass` entry for migrator is missing, so schema application is waiting on that local credential setup. No schema/data changes.
>
> **Revision note v1.18 → v1.19:** verified from VM01 with the per-VM key: `sentrix_app` connects to `10.20.10.20:5432/sentrix` and `SELECT 1` returns `1`. `\dt` reports no relations, so schema has not been applied. `sentrix_migrator` from VM01 is denied by HBA (no migrator rule), so schema application needs a migrator HBA/password or a privileged postgres run on VM02.
>
> **Revision note v1.17 → v1.18:** HBA rule corrected from `sentix` to `sentrix`; `pg_hba_file_rules` now reports database `{sentrix}`. Loopback `psql -d sentrix` returned `1`. From VM01 `.10`, `psql -w` returned `no password supplied`, proving the corrected rule matches; only the password prompt remains. No schema/data changes.
>
> **Revision note v1.16 → v1.17:** root cause identified: the actual database is `sentrix`, but the HBA rule and several commands used `sentix` (missing `r`). The loopback rule matches any database, so authentication proceeded and then reported `database "sentix" does not exist`. Correct the HBA rule to `sentrix` and test from VM01. Earlier notes in this tracker that used `sentix` were typographical; the intended and actual database is `sentrix`.
>
> **Revision note v1.15 → v1.16:** `sentrix_app` password was set with `\password` on VM02. The loopback connection proceeded past authentication, but PostgreSQL returned `database "sentrix" does not exist`. A single postmaster (PID 11406, cluster 16/main) owns both listeners, so this is not a different instance; the database list must be rechecked.
>
> **Revision note v1.14 → v1.15:** `listen_addresses` now includes `127.0.0.1`; `127.0.0.1:5432` and `10.20.10.20:5432` are listening. `psql -h 127.0.0.1 -U sentrix_app -d sentrix -w` returns `no password supplied`, proving the loopback HBA rule matches. The `.10` rule still does not match live; loopback + SSH tunnel is the working path. No schema/data changes.
>
> **Revision note v1.13 → v1.14:** PostgreSQL was restarted at 13:40 UTC and is active. The app connection from `.10` still fails with the same HBA error. A single SSH key installed on both VMs is intentional and is not the cause; SSH key login succeeds on both. The remaining fault is PostgreSQL HBA matching, not SSH.
>
> **Revision note v1.12 → v1.13:** TLS handshake to `10.20.10.20:5432` succeeds (TLS 1.3, self-signed `CN=sentrix-data`). `127.0.0.1:5432` is refused because `listen_addresses` is only `10.20.10.20`. The `.10` HBA rule in file is still not matching live; a controlled restart is the next diagnostic after snapshot.
>
> **Revision note v1.11 → v1.12:** the operator ran `pg_reload_conf()`, which returned true. The app connection from VM01 `.10` still fails with “no pg_hba.conf entry” for both SSL and non-SSL. The file rule and active behavior remain inconsistent; HBA diagnostics are required before any DB target work.
>
> **Revision note v1.10 → v1.11:** operator-supplied privileged output verifies PostgreSQL 16.15, `sentrix_app`/`sentrix_migrator` as non-superuser login roles, `sentrix` owned by `sentrix_migrator`, zero user tables, UFW 22 from APP and 5432 from `.10`, and HBA rule 8 (`hostssl sentrix sentrix_app 10.20.10.10`). The live app connection from `.10` still failed, so the active HBA state must be reloaded/verified before use.
>
> **Revision note v1.9 → v1.10:** read `postgresql.conf` (`listen_addresses = '10.20.10.20'`, port `5432`, `ssl = on`, snakeoil cert/key, `include_dir = 'conf.d'`). `pg_hba.conf` is unreadable by `sentrixadmin` (`postgres:postgres`, `0640`), so HBA inspection requires privileged access. No database was changed.
>
> **Revision note v1.8 → v1.9:** SSH key login verified to VM01 and VM02. `sudo -n` requires a password on both. Current HBA denied `sentrix_app` from `10.20.10.10` and from `10.20.10.20` to database `sentrix` on both SSL and non-SSL attempts. Phase 1 is blocked pending a privileged DB path and a current HBA review.
>
> **Revision note v1.7 → v1.8:** generated a dedicated local ED25519 SSH key for M1; the public key is not yet installed on any VM. Phase 0 remains incomplete. No password was used and no secret is stored.
>
> **Revision note v1.6 → v1.7:** operator-supplied inventory from VM02–VM05 confirms `.20`, `.30`, `.40`/`.10`, and LAB `.20`; VM03 NAT is `192.168.213.132`, which explains the earlier mistaken APP `.132` report. Listener observations are recorded; authentication, firewall and PostgreSQL settings remain unverified.
>
> **Revision note v1.5 → v1.6:** operator-supplied VM01 output verified `10.20.10.10/24` on `ens34` and `192.168.213.130/24` on `ens33`; the earlier `.132` APP report is treated as incorrect. VM02 and VM03–VM05 remain unverified. No credentials are recorded.
>
> **Revision note v1.4 → v1.5:** added ARP/VMnet evidence from the Windows host. The evidence suggests VM01’s APP address is `10.20.10.10` on VMnet9 and that `10.20.10.132` is not present on VMnet9, but this remains unresolved until confirmed inside VM01. No credentials were used.
>
> **Revision note v1.3 → v1.4:** added limited read-only TCP reachability results from Windows. These results are reachability only; they do not verify host identity, authentication or current service state. VM01’s address remains unresolved because the old `.10` and reported `.132` results conflict.
>
> **Revision note v1.2 → v1.3:** recorded user-reported VM01 APP/NAT addresses and SSH status, flagged the conflict with the earlier `10.20.10.10` record, and added a credential-handling warning. No password or other secret is stored in this repository.
>
> **Revision note v1.1 → v1.2:** corrected the M1 decision IDs to `ASR-D-xx` to avoid collision with the Phase 2 project decisions `D-01…D-18`; recorded the known repository path; corrected the interpretation of the user's “full authority” statement; confirmed the local memo/decision-record files exist; and kept all unresolved target/evidence fields explicit.

---

## 1. Executive status

| Area | Current status | Notes |
|---|---|---|
| Overall M1 | `NO-GO / HOLD` | No execution authorized |
| `ASR-D-01` | `PROVISIONAL — USER INSTRUCTION RECORDED` | Option A is the provisional direction; formal owner approval is not recorded |
| `ASR-D-02` | `UNRESOLVED` | Existing PostgreSQL endpoint is verified as listening but is not the approved disposable M1 target; target identifiers remain unresolved |
| VM inventory | `VERIFIED — read-only operator-supplied inventory` | All five VM addresses/interfaces/confirmed listeners recorded; authentication and firewall not verified |
| VM02 PostgreSQL | `ENDPOINT VERIFIED — target not approved` | `10.20.10.20:5432` listening; TLS/role/HBA evidence not freshly verified |
| DB access | `BLOCKED` | Current HBA denies `sentrix_app` from `.10` and `.20`; `sudo -n` unavailable to the agent |
| Artifact baseline | `PARTIAL — VCS BASELINE UNRESOLVED` | Repository path known; branch/commit and canonical artifacts not recorded |
| Backup/restore | `UNVERIFIED` | No restore evidence supplied |
| Gates/acceptance tests | `NOT VERIFIED` | No new evidence; no PASS assigned |

---

## 2. Decision register

> M1 decisions use `ASR-D-01…ASR-D-10`. They are distinct from the Phase 2 project decisions `D-01…D-18` in [`07-risks-assumptions-decisions.md`](07-risks-assumptions-decisions.md).

| ID | Decision | Status | Required next action |
|---|---|---|---|
| `ASR-D-01` | M1 scope and PostgreSQL isolation boundary | `PROVISIONAL` | Complete the formal decision record with the authorized decision-maker’s identity/role, explicit choice, ticket and timestamp/timezone |
| `ASR-D-02` | PostgreSQL target identity | `UNRESOLVED` | Identify the disposable target host, instance/cluster, port, database, account/privileges, backup/restore evidence and change ticket |
| `ASR-D-03` | Database role and privilege model | `UNRESOLVED` | Record ownership, grants, memberships, `PUBLIC`, `SET ROLE`, `TRUNCATE` and relevant bypass controls |
| `ASR-D-04` | TLS and server identity verification | `UNRESOLVED` | Record CA, certificate SAN and verification policy for the selected target |
| `ASR-D-05` | Backup, restore, RPO and RTO | `UNRESOLVED` | Identify the approved recovery method and evidence of a successful isolated restore |
| `ASR-D-06` | VM05/LAB isolation | `UNRESOLVED` | Revalidate routing, NAT, forwarding, Docker networking and permitted reachability |
| `ASR-D-07` | SSH/UFW management path | `UNRESOLVED` | Confirm authorized management sources, console access and rollback path |
| `ASR-D-08` | VM snapshot and database recovery consistency | `UNRESOLVED` | Document snapshot consistency and distinguish VM snapshot recovery from PostgreSQL backup/restore |
| `ASR-D-09` | Acceptance criteria and evidence review | `UNRESOLVED` | Confirm test criteria, evidence requirements, independent reviewer and residual-risk approval |
| `ASR-D-10` | Execution sequence and change window | `UNRESOLVED` | Record accountable owners, change ticket, approved sequence and execution window |

**Authority note:** The user’s statement granting the agent “full authority” is recorded as a **user-provided instruction for documentation work**. It is **not** evidence of approval by the Supervisor, Infrastructure Owner or Database/Security Owner, and it does not complete `ASR-D-01` formal approval.

### 2.1 Credential handling alert — 2026-10-22

- An SSH password was supplied in the review conversation. It is **not recorded in this repository** and must be treated as exposed.
- Rotate the password and prefer SSH key-based authentication before any further access.
- Do not paste credentials into documents, tickets, logs or evidence.
- No login or credential validation was attempted by this update.

---

## 3. Existing five-VM inventory

**All five VMs were inventoried read-only by the operator on 2026-10-22.** The values below are operator-supplied command output; the agent did not independently log in. Authentication, firewall and PostgreSQL privilege state remain unverified.

| VM | Intended role | Observed APP/LAB address (operator-supplied) | Current evidence status |
|---|---|---|---|
| VM01 `sentrix-app` | Application | APP `10.20.10.10/24` on `ens34`; NAT `192.168.213.130/24` on `ens33` | **Verified by operator output.** `sentrixadmin` session observed; default route via NAT; no failed units. |
| VM02 `sentrix-data` | PostgreSQL | APP `10.20.10.20/24` on `ens34`; NAT `192.168.213.131/24` on `ens33` | **Verified by operator output.** SSH/22 and PostgreSQL `10.20.10.20:5432` listening; no failed units. Endpoint is not an approved M1 target. |
| VM03 `sentrix-ai` | AI/model service | APP `10.20.10.30/24` on `ens34`; NAT `192.168.213.132/24` on `ens33` | **Verified by operator output.** SSH/22 and AI service `10.20.10.30:8000` listening; no failed units. The NAT `.132` explains the earlier `.132` APP confusion. |
| VM04 `sentrix-worker` | Worker/job execution | APP `10.20.10.40/24` on `ens34`; LAB `10.20.20.10/24` on `ens35`; NAT `192.168.213.133/24` on `ens33` | **Verified by operator output.** SSH/22 listening; no worker/application listener observed; default route via NAT. |
| VM05 `sentrix-lab` | Authorized test lab | LAB `10.20.20.20/24` on `ens34`; no NAT interface observed | **Verified by operator output.** SSH/22 and Docker-published `10.20.20.20:3000` listening; no default route; `docker0`/veth present. |

**VM01 resolution note:** operator-supplied output confirms `10.20.10.10/24` on `ens34` and `192.168.213.130/24` on `ens33`, with MACs `00:0c:29:21:e6:5c` and `00:0c:29:21:e6:52`. The earlier `.132` APP report is treated as incorrect. The `sentrixadmin` session on VM01 was observed; no password is recorded.

**VM02 credential status:** the SSH username `sentrixadmin` was mentioned and a password was supplied; the operator demonstrated a VM02 session in the supplied output. The agent did not log in or validate credentials. The secret is not recorded here and must be rotated.

### 3.1 Read-only TCP reachability check — 2026-10-22

Performed from the Windows host with a TCP connection test only. No credentials were sent, no login was attempted and no service state was changed.

| Target | TCP result | Interpretation |
|---|---|---|
| `10.20.10.10:22` (VM01 old APP) | **reachable** | A service accepted TCP; host identity and account are **not** verified |
| `10.20.10.132:22` (VM01 reported APP) | **not reachable** | Could be wrong address, firewall, or host down; not proof of absence |
| `10.20.10.20:22` (VM02 SSH) | **reachable** | SSH path exists; identity/authentication not verified |
| `10.20.10.20:5432` (VM02 PostgreSQL) | **not reachable** | Direct DB path from Windows not confirmed; UFW/firewall may explain |

**Conclusion:** the VM01 address is now resolved by operator-supplied output: `10.20.10.10/24` on `ens34`. The `.132` APP report was incorrect. TCP reachability alone did not establish identity; the host output does.

### 3.2 ARP / VMnet observation — 2026-10-22

The Windows host has VMnet9 at `10.20.10.1/24` and VMnet8 at `192.168.213.1/24`. `arp -a` showed:

| Interface | Observed entry | Interpretation |
|---|---|---|
| VMnet9 `10.20.10.1` | `10.20.10.10` → `00-0c-29-21-e6-5c` | A VMware NIC is present at `.10` |
| VMnet9 `10.20.10.1` | `10.20.10.20` → `00-0c-29-15-ec-71` | A VMware NIC is present at `.20` |
| VMnet9 `10.20.10.1` | no entry for `10.20.10.132` | `.132` was not observed on the APP VMnet |
| VMnet8 `192.168.213.1` | `192.168.213.130`, `.132`, `.133` | NAT-side addresses; `.132` there is a NAT address, not `10.20.10.132` |

This ARP evidence is consistent with the subsequent VM01 output: `10.20.10.10` is VM01’s APP address; `10.20.10.132` was not on VMnet9. The NAT-side `192.168.213.132` is VM03’s NAT address, not `10.20.10.132`. No login was attempted by the agent.

### 3.3 Verified listener summary — operator-supplied, 2026-10-22

| VM | APP/LAB address | Confirmed listeners | Notes |
|---|---|---|---|
| VM01 | APP `10.20.10.10` | SSH/22 confirmed earlier from Windows; `hostnamectl`/`ip` output provided | no failed units |
| VM02 | APP `10.20.10.20` | SSH/22 (`0.0.0.0`), PostgreSQL `10.20.10.20:5432` | no failed units; direct `5432` from Windows still not reachable |
| VM03 | APP `10.20.10.30` | SSH/22, AI service `10.20.10.30:8000` | no failed units |
| VM04 | APP `10.20.10.40`; LAB `10.20.20.10` | SSH/22 | no worker listener observed; no failed units |
| VM05 | LAB `10.20.20.20` | SSH/22, Docker-published `10.20.20.20:3000` | no default route; `docker0`/veth present; no failed units |

**Limits:** listeners do not prove authentication, TLS, firewall policy, PostgreSQL privileges or application correctness. VM03 `:8000` and VM05 `:3000` were not accessed by the agent.

### 3.4 Phase 0 progress — SSH and DB access

| Item | Status |
|---|---|
| Dedicated SSH key | Generated locally: `C:\Users\Halord\.ssh\sentrix_m1_ed25519` |
| Public key fingerprint | `SHA256:1o+I53U+nL7UCfoziYYbwJ3uM4sXVpiYc7SituMGSiw` |
| Installed on VM01/VM02 | **YES — key login verified to both hosts** |
| Password used by agent | **NO** |
| Password rotation | **PENDING** |
| `sudo -n` on VM01/VM02 | **PASSWORD REQUIRED** |
| VM02 snapshot | **NOT CONFIRMED** |
| `sentrix_dev` target | **NOT CREATED** |
| HBA for `sentrix_app` from `.10` | **FILE RULE PRESENT; RELOAD RETURNED TRUE; LIVE CONNECTION STILL DENIED** |
| HBA for `sentrix_app` from `.20` | **DENIED** — file has no matching rule |
| HBA file rules | local peer for postgres/all; host 127.0.0.1/::1 scram; `hostssl sentrix sentrix_app 10.20.10.10 scram-sha-256` |
| Roles | `sentrix_app` and `sentrix_migrator`: login, non-superuser, no createdb/createrole |
| Databases | `sentrix` owned by `sentrix_migrator`; zero user tables; no `sentrix_dev` |
| UFW | active; default deny incoming; SSH from `10.20.10.0/24`; PostgreSQL from `10.20.10.10` |
| PostgreSQL | 16.15; `ssl=on`; snakeoil cert; `password_encryption=scram-sha-256` |
| `postgresql.conf` readable | **YES** — `listen_addresses='10.20.10.20'`, port `5432`, `ssl=on`, snakeoil cert/key, `include_dir='conf.d'` |
| `pg_hba.conf` readable | **NO** — `postgres:postgres`, `0640`; privileged read required |

The private key must not be committed, printed, or copied into project documents.

### 3.5 Database-name typo and HBA evidence — 2026-10-22

**Root cause found:** the actual database is `sentrix`, but the HBA rule and several earlier commands used `sentix` (missing `r`).

Evidence:

| Check | Observed |
|---|---|
| `pg_database` | `sentrix`, owner `sentrix_migrator` |
| HBA file rule 8 before fix | `hostssl sentix sentrix_app 10.20.10.10/32 scram-sha-256` — database name typo |
| HBA file rule 8 after fix | `hostssl sentrix sentrix_app 10.20.10.10/32 scram-sha-256` |
| Loopback test with `-d sentrix` | **PASS** — returned `1` |
| `.10` test with `-d sentrix -w` | **`no password supplied`** — HBA matches; password prompt expected |

The database-name typo was the root cause of the earlier `.10` mismatch. After correcting the HBA rule to `sentrix`, the `.10` path matches at HBA level.

**Implications:**

- Use database **`sentrix`** (empty, owner `sentrix_migrator`); no `sentrix_dev` is needed.
- The password is set; VM01 can connect with the `sentrix_app` password.
- Schema/seed still require a privileged/migration path because `sentrix_app` has no DDL rights.
- No HBA rule exists for a future `sentrix_dev`; if used, target that exact name.
- The `sentrix` database has no user tables yet; schema application is the next step.
- PostgreSQL admin commands must run on **VM02**; VM01 has no OS `postgres` user.

### Verified network layout — operator-supplied, 2026-10-22

- APP subnet: `10.20.10.0/24`; Windows host `10.20.10.1`; VM01 `.10`, VM02 `.20`, VM03 `.30`, VM04 `.40`.
- LAB subnet: `10.20.20.0/24`; Windows host `10.20.20.1`; VM04 `.10`, VM05 `.20`.
- NAT subnet: `192.168.213.0/24`; VM01 `.130`, VM02 `.131`, VM03 `.132`, VM04 `.133`; default route via `192.168.213.2`.
- VM01/VM02: `ens33` = NAT; `ens34` = APP.
- VM03: `ens33` = NAT; `ens34` = APP.
- VM04: `ens33` = NAT; `ens34` = APP; `ens35` = LAB.
- VM05: `ens34` = LAB; no NAT interface and no default route.
- APP/LAB separation still requires firewall/forwarding verification; the addresses alone do not prove isolation.

No new CPU, RAM or disk values are inferred for VMs where those values have not been supplied or verified.

---

## 4. VM02 — PostgreSQL configuration (mixed verification)

The hostname, APP address, SSH listener, PostgreSQL listener and failed-unit state were verified by operator-supplied output on 2026-10-22. PostgreSQL version, TLS, HBA, UFW, roles, grants and data state remain historical/unverified.

| Field | Recorded value | Status |
|---|---|---|
| VM hostname | `sentrix-data` | **Verified by operator output** |
| APP address | `10.20.10.20/24` (`ens34`) | **Verified by operator output** |
| NAT address | `192.168.213.131/24` (`ens33`) | **Verified by operator output** |
| PostgreSQL port | `5432`; listener `10.20.10.20:5432` | **Verified listener; authentication/TLS not verified** |
| SSH | listener `0.0.0.0:22` | **Verified listener; authentication not verified** |
| Failed systemd units | none | **Verified by operator output** |
| PostgreSQL version | `16` | Historical/user-supplied |
| Operating system | Ubuntu Server `24.04.5` | **Verified by operator output** |
| Kernel | `6.8.0-147-generic` | **Verified by operator output** |
| RAM | Approximately `3.8 GiB` | User-supplied historical; time-sensitive |
| Root filesystem | `33 GiB`, approximately `24 GiB` free at the time | User-supplied historical; time-sensitive |
| Existing database | `sentrix` | Existing; **outside M1 scope** unless separately authorized |
| Recorded database owner | `sentrix_migrator` | Historical; current grants/membership not revalidated |
| Encoding | UTF-8 | Historical/user-supplied |
| PostgreSQL SSL | Enabled; TLS 1.2 and SCRAM noted | Historical; end-to-end certificate validation not established |
| Certificate | Snakeoil certificate noted | Historical; not evidence of trusted server identity |
| UFW | Active; SSH rule for `10.20.10.0/24` and PostgreSQL rule from `10.20.10.10` noted | Historical; current rules not revalidated |
| User tables/sequences | None reported at the recorded inspection | Historical observation only |

### Target boundary

The existing endpoint `10.20.10.20:5432` is **not automatically the approved M1 target**.

`ASR-D-01` provisionally selects Option A: an isolated, disposable PostgreSQL instance/cluster. Option B is the fallback if A is not feasible. Option C is not to be used for M1 role/privilege tests.

A separate database on a shared PostgreSQL cluster does not, by itself, satisfy the isolation requirement for cluster-level operations. The existing `sentrix` database must not be used for migration or role/privilege testing under this tracker.

---

## 5. `ASR-D-02` target register

| Field | Recorded value | Classification |
|---|---|---|
| Existing PostgreSQL host | `sentrix-data` | **Verified hostname/address; not an approved target** |
| Existing endpoint | `10.20.10.20:5432` | **Listener verified; file HBA rule exists for `sentrix` from `.10`; live connection denied pending reload; not an approved target** |
| Existing `sentrix` database | Empty; owner `sentrix_migrator`; 0 user tables | **Verified; out of scope unless explicitly approved** |
| Existing roles | `sentrix_app`, `sentrix_migrator` — login, non-superuser, no createdb/createrole | **Verified roles; passwords not verified** |
| `sentrix_dev` database | Not present | `UNRESOLVED — not created` |
| Target instance/cluster for M1 | Not identified | `UNRESOLVED` |
| Disposable test database | Not identified | `UNRESOLVED` |
| Authorized target account | Not identified | `UNRESOLVED` |
| Account privileges and role membership | Not established | `UNRESOLVED` |
| Backup/restore method | Not established | `UNVERIFIED` |
| Change ticket | Not supplied | `UNRESOLVED` |
| Target approval | Not recorded | `UNRESOLVED` |

---

## 6. Artifact and source-of-truth register

| Artifact | Status | Next action |
|---|---|---|
| Repository location | `D:\My Project\AI pentest` | Known working directory; confirm canonical location |
| Branch | `UNRESOLVED` | Record the intended branch if VCS exists |
| Canonical commit hash | `UNRESOLVED` | Record exact baseline commit if VCS exists; do not claim a baseline without evidence |
| Migration files/tool configuration | `NOT INVENTORIED` | Inventory without executing migrations |
| Schema and models | `NOT INVENTORIED` | Identify canonical versions and discrepancies |
| Seed scripts and manifest | `NOT INVENTORIED` | Inventory and record manifest version/hash |
| Role/grant documentation | `NOT INVENTORIED` | Inventory role and privilege definitions |
| Test suite and existing results | `NOT INVENTORIED` | Record available tests and actual results |
| Existing ASR/memo files | `PRESENT` | Review actual contents before changing repository contents |

Previously supplied document paths:

- [`09b-asr-d-01-d-02-decision-record.md`](09b-asr-d-01-d-02-decision-record.md) — present locally.
- [`09-decision-memo-001-m1-target-environment.md`](09-decision-memo-001-m1-target-environment.md) — present locally.
- [`09a-decision-memo-001-transmittal.md`](09a-decision-memo-001-transmittal.md) — present locally; NOT SENT.

`SENTRIX-M1-ASR-001` v1.3 is supplied in the review conversation and is **not yet committed as a separate repository file**.

---

## 7. Readiness checklist

| ID | Readiness condition | Status |
|---|---|---|
| R-01 | Formal M1 scope and isolation decision | `BLOCKED` |
| R-02 | Approved disposable PostgreSQL target identified | `BLOCKED` |
| R-03 | Repository, commit and canonical artifacts inventoried | `NOT ASSESSED` |
| R-04 | Role/privilege model approved and documented | `BLOCKED` |
| R-05 | TLS and server identity requirements established | `BLOCKED` |
| R-06 | Recovery method and restore evidence verified | `BLOCKED` |
| R-07 | LAB isolation and permitted reachability verified | `BLOCKED` |
| R-08 | Authorized management and rollback path verified | `BLOCKED` |
| R-09 | Acceptance criteria and independent evidence review defined | `BLOCKED` |
| R-10 | Execution owners, change ticket and window recorded | `BLOCKED` |

---

## 8. Next actions, in order

1. Rotate the exposed SSH password; disable password login only after key access is proven.
2. With an authorized privileged path, reload PostgreSQL HBA and re-test `sentrix_app` from VM01 `.10`; record whether the file rule becomes active.
3. Decide the M1 database target: existing empty `sentrix` (HBA file rule exists) or new `sentrix_dev` (requires a minimal HBA rule).
4. Confirm/take a VM02 snapshot before any database creation or schema application.
5. Create the approved database/role grants and verify least privilege.
6. Complete the `ASR-D-01` decision record without inventing owner identities, ticket numbers or timestamps.
7. Inventory the repository, branch/commit if applicable, migration/schema/seed artifacts and tests in read-only mode.
8. Complete `ASR-D-02` using verified target details and recovery evidence.
9. Resolve `ASR-D-03` through `ASR-D-10` and the readiness blockers.
10. Reassess gates only when traceable evidence exists and required review is recorded.

---

## 9. Execution guardrails

Until required decisions, target identity and evidence are complete:

- Overall status remains `NO-GO / HOLD`.
- Do not execute migrations or modify roles, grants, schemas or databases.
- Do not use the existing `sentrix` database as the test target.
- Do not change VM networking, UFW, SSH, ACLs or recovery artifacts.
- Do not mark gates or acceptance tests `PASS` without evidence.
- Keep proposed, historical, user-provided and freshly verified values explicitly distinguished.
- Do not treat this tracker, a login, a catalog view or a verbal statement as approval.

**Disposition:** `NO-GO / HOLD — TARGET AND FORMAL READINESS EVIDENCE INCOMPLETE`.
