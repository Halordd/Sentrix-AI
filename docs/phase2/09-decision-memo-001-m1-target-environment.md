# SENTRIX — Decision Memo 001: M1 Target Environment

| Field | Value |
|---|---|
| Document ID | `SENTRIX-M1-DM-001` |
| Version | 0.2 — Draft for Decision |
| Status | **DRAFT — NOT AUTHORIZED FOR EXECUTION** |
| Decision status | **NOT RECORDED** |
| Overall project status | **NO-GO / HOLD** |
| Related ASR | `SENTRIX-M1-ASR-001` v1.3 |
| Related decisions | **ASR-D-01**, **ASR-D-02** |
| Date prepared | 2026-10-19 (Asia/Saigon); approval timestamps **NOT RECORDED** |
| Prepared by | **NOT PROVIDED** |
| Decision owners | Supervisor + Infrastructure owner (ASR-D-01); Database owner + Infrastructure owner (ASR-D-02) |
| Revision | 0.2 — added explicit recommendation hierarchy: A primary, B fallback, C not recommended, D defer |

> **ID note:** `ASR-D-01` … `ASR-D-10` are the M1 authorization decisions. They are distinct from the Phase 2 project decisions `D-01` … `D-18` in [`07-risks-assumptions-decisions.md`](07-risks-assumptions-decisions.md). Where older text says “D-01”, it means `ASR-D-01` in this context.

---

## 1. Purpose

This memo requests two decisions needed before SENTRIX M1 can be planned and reviewed for approval:

1. **ASR-D-01 — M1 target model and resource boundary.** Which kind of disposable environment may M1 use, and what exactly does that approval cover?
2. **ASR-D-02 — Exact target environment and connection path.** Which cluster/instance, host, database, accounts and path are authorised, once ASR-D-01 is selected?

This is a **decision request**, not a decision record and not an execution authorization. No target, account, credential or approval is invented here.

The existing `sentrix` database remains **out of scope**. A disposable database on the shared PostgreSQL cluster does **not** isolate cluster-level changes such as roles, HBA, TLS or service configuration.

---

## 2. Evidence status

| Class | Content |
|---|---|
| **Historical (H)** | PostgreSQL 16 was previously observed on VM02; `sentrix` and roles `sentrix_app`/`sentrix_migrator` were previously observed; a snakeoil certificate and restricted firewall were previously observed. These are not current verified facts. |
| **Runbook (R)** | A separate deployment runbook proposes the five-VM environment and service deployment. It is not authorization. |
| **Inference (I)** | Risks from shared-cluster roles, TLS trust, firewall lockout, Docker/UFW behaviour and snapshot/backup confusion. |
| **Unresolved (U)** | ASR-D-01, ASR-D-02, target identifiers, migration revisions, seed manifest hash/rows, role matrix, TLS identity, backup/restore evidence and approvals. |
| **Fresh verified (V)** | **None in this memo.** No evidence was collected by this task. |

---

## 3. Why a decision is needed

The current ASR package is **NO-GO / HOLD — INSUFFICIENT INFORMATION**. M1 cannot start because:

- no disposable environment has been identified;
- no decision selects whether M1 may use an isolated cluster/instance or only a database inside the existing cluster;
- cluster-level operations (roles, HBA, TLS, service configuration) are not isolated by a “disposable database” alone;
- no target owner, account, connection path, change ticket or approval is recorded.

These are governance decisions, not implementation details. Selecting a model determines what must be separately approved.

---

## 4. Decision ASR-D-01 — M1 target model and resource boundary

### 4.1 Options

| Option | Description | Security / operational implications | Status |
|---|---|---|---|
| **A — Isolated disposable PostgreSQL instance/cluster** | A separate PostgreSQL instance/cluster dedicated to M1, not the shared `sentrix-data` cluster. Roles, HBA, TLS, schema and seed tests can be confined to that instance. | Strongest isolation from `sentrix`; still requires host/VM authorization, backup/restore and a separate environment change record. | **Primary recommendation — NOT SELECTED** |
| **B — Separate cluster/instance on VM02** | A new cluster or instance on VM02 with a distinct data directory/port, separate from the existing cluster. | Isolates the existing cluster’s data, but remains an OS/cluster change on VM02; snapshot/console and infrastructure approval required. Weaker than A because it shares VM02, storage and OS. | **Fallback recommendation — NOT SELECTED** |
| **C — Disposable database inside the existing shared cluster** | Only a database inside the existing PostgreSQL cluster; no cluster-level changes under this option. | DB-local schema/seed may be possible, but roles, HBA, TLS, service restart and cluster backup are **cluster-level** and must be separately approved. Not suitable for M1 role/privilege testing without that separate approval. | **Not recommended for M1 role/privilege tests** |
| **D — Defer** | Make no target-model decision now. | M1 remains blocked; no M1 evidence can be collected. | Not selected |

**Recommendation hierarchy:**

1. **Option A — primary.** Choose A if a separate disposable VM or PostgreSQL instance can be dedicated to M1. It gives the cleanest separation between M1 and the existing `sentrix` database.
2. **Option B — fallback.** Choose B only if a separate disposable instance cannot be provided. It isolates M1 from the existing cluster’s data, but still requires a separate OS/cluster change record for VM02, snapshot/console access and explicit infrastructure approval.
3. **Option C — not recommended for M1 role/privilege tests.** It is acceptable only for DB-local schema/seed exploration with a separate cluster-level approval for roles/HBA/TLS; it does not provide the isolation M1 needs.
4. **Option D — defer.** M1 stays blocked.

This is a recommendation only; the decision owner has not selected any option. Option B does not authorize VM02 changes by itself; Option C does not authorize cluster-level changes.

### 4.2 What ASR-D-01 would approve if Option A or B is selected

- Permission to **identify and propose** a disposable PostgreSQL instance/cluster dedicated to M1.
- Permission to treat schema, seed, roles, grants and tests inside that disposable instance as M1 scope, subject to the separate change record and approvals.
- Explicit exclusion of the existing `sentrix` database and shared cluster resources.
- No permission to modify VM02, firewall, SSH, HBA, TLS or services merely because the instance is “disposable”.

### 4.3 What ASR-D-01 would approve if Option C is selected

- Only **DB-local** work inside a disposable database: schema, data, DB-level grants and tests.
- Explicit exclusion of roles, role membership, `CREATE DATABASE`, HBA, TLS, service configuration and cluster-level backup/restore.
- A separate change record for any cluster-level operation.

### 4.4 What ASR-D-01 does not decide

- ASR-D-03: role/ownership/grant/append-only/worker split.
- ASR-D-04: TLS identity/CA/verify-full.
- ASR-D-05: backup/restore/RPO/RTO.
- ASR-D-06–ASR-D-10: VM05 isolation, firewall/SSH, snapshots, acceptance, sequencing.

Approval of ASR-D-01 does not approve ASR-D-02 through ASR-D-10.

---

## 5. Decision ASR-D-02 — Exact target environment and connection path

Once ASR-D-01 is selected, ASR-D-02 must record the exact environment. Until then, every field below is **UNRESOLVED**.

| Field | Required value | Current status |
|---|---|---|
| Environment model | Option A, B or C from §4.1 | **UNRESOLVED** |
| Host / VM | Named VM or physical host | **UNRESOLVED — REQUIRES OWNER CONFIRMATION** |
| PostgreSQL instance/cluster | Name and version | **UNRESOLVED** |
| Port | Explicit port | **UNRESOLVED** |
| Disposable database | Exact database name | **UNRESOLVED** |
| Database owner | Role that owns the disposable DB | **UNRESOLVED** |
| Migration executor | Account/role and host from which migrations run | **UNRESOLVED** |
| Test/read-only account | Account used for tests | **UNRESOLVED** |
| Connection path | Local socket or host:port; TLS mode; DNS/hostname | **UNRESOLVED** |
| Network source | Source IP/VM for remote connections, if any | **UNRESOLVED** |
| Backup/restore scope | Method and isolated restore target | **UNRESOLVED** |
| Snapshot/console | VM snapshot and console access | **UNRESOLVED** |
| Change ticket | Traceable ticket reference | **UNRESOLVED** |
| Environment owner | Person/role accountable for the host | **NOT PROVIDED** |

**Rule:** A target is not approved because it is listed in a runbook, reached over SSH, or visible in a PostgreSQL catalog. It is approved only when ASR-D-02 records the values and the required owners approve them.

---

## 6. Resource boundaries

| Class | Examples | M1 treatment |
|---|---|---|
| **DB-local** | Schema, tables, indexes, triggers, data, DB-level grants inside the disposable database | Allowed only in the approved disposable target |
| **Cluster-level** | Roles, memberships, `CREATE DATABASE`, HBA, TLS, `listen_addresses`, service configuration, cluster backup | **Separate approval required**, even when the database is disposable |
| **OS/network** | Packages, services, firewall, SSH, NICs, Netplan, VMware, snapshots | **Out of M1; separate authorization** |
| **Read-only** | Inventory/catalog observation without state change | Only within approved read-only scope |
| **Shared/production** | `sentrix` or shared cluster resources | **Excluded; separate change record and restore evidence** |

**Important:** If Option A or B is selected, cluster-level operations may be confined to the disposable instance, but they still require explicit authorization for that instance. If Option C is selected, cluster-level operations are outside the option entirely.

---

## 7. Preconditions for any later M1 work

Even after ASR-D-01 and ASR-D-02 are recorded:

1. A written M1 scope approval must exist.
2. ASR-D-03 (role/privilege/append-only) must be decided.
3. ASR-D-04 (TLS/CA/verify-full) and ASR-D-05 (backup/restore) must be decided.
4. A change ticket and named implementer must exist.
5. Read-only scope, accounts and evidence handling must be approved before inventory.
6. A pre-change recovery point, console access, rollback plan and stop conditions must exist.
7. No `sentrix` database change may occur under this memo.

---

## 8. Required authorization and owners

| Decision | Required owner | Approval evidence |
|---|---|---|
| ASR-D-01 | Supervisor + Infrastructure owner | Written decision with selected option, scope, exclusions and conditions |
| ASR-D-02 | Database owner + Infrastructure owner | Written target record with host/DB/account/path and change ticket |
| Technical input | Technical owner | Documented architecture/acceptance input |
| Independent review | Independent reviewer | Review record and conflict-of-interest check |
| Database/security review | Database/security owner | Role/TLS/backup review, where applicable |

All names are **NOT PROVIDED**. No approval is implied.

---

## 9. Decision record

| Field | Value |
|---|---|
| Decision ID | `ASR-D-01` / `ASR-D-02` |
| Status | **UNRESOLVED — NOT APPROVED** |
| Selected option | **NOT SELECTED** |
| Rationale | **NOT RECORDED** |
| Decision owner | **NOT PROVIDED** |
| Decision timestamp | **NOT RECORDED** |
| Review/expiry | **UNRESOLVED** |
| Approval reference | **NOT RECORDED** |

No signature, date or ticket is invented.

---

## 10. Recommendation

1. **Select Option A as primary** for ASR-D-01: an isolated disposable PostgreSQL instance/cluster, not the shared `sentrix-data` cluster.
2. **If A is not feasible, select Option B as fallback**: a separate cluster/instance on VM02. Do not select C for M1 role/privilege tests; C requires separate cluster-level approval and cannot isolate roles/HBA/TLS.
3. Record ASR-D-02 with exact host, instance, port, database, accounts, connection path, change ticket and owner — or leave it explicitly `UNRESOLVED` and keep M1 blocked.
4. Keep `sentrix` out of scope.
5. Keep ASR-D-03 through ASR-D-10 unresolved; do not let this memo imply approval.
6. Only after ASR-D-01 and ASR-D-02 are recorded should the ASR package advance from `NO-GO / HOLD — INSUFFICIENT INFORMATION`.

This recommendation is **NOT SELECTED** and does not authorize any change.

---

## 11. Final status

**DRAFT — NOT AUTHORIZED FOR EXECUTION.**
**Decision status: NOT RECORDED.**
**Overall: NO-GO / HOLD — INSUFFICIENT INFORMATION.**

No infrastructure, database, network, firewall, SSH, PostgreSQL, role, grant or data change was performed. No command was executed and no evidence was collected.

---

## 12. References

- `SENTRIX-M1-ASR-001` v1.3 — related authorization package supplied in the review conversation; not yet committed as a separate file.
- [`09b-asr-d-01-d-02-decision-record.md`](09b-asr-d-01-d-02-decision-record.md) — provisional direction record; formal approval still not recorded.
- [`07-risks-assumptions-decisions.md`](07-risks-assumptions-decisions.md) — Phase 2 project decisions `D-01…D-18`; distinct from `ASR-D-01…ASR-D-10`.
- [`06-migration-and-acceptance.md`](06-migration-and-acceptance.md) — M1 ticket and acceptance tests.
- [`schema.sql`](../../database/schema.sql) — design artifact; not executed.
- [`seed-manifest.json`](../../database/seed-manifest.json) — seed manifest; exact hash/rows require owner confirmation.
