# SENTRIX — ASR-D-01 / ASR-D-02 Decision Record

| Field | Value |
|---|---|
| Document ID | `SENTRIX-M1-DR-001` |
| Version | 0.1 — Draft |
| Status | **PROVISIONAL DIRECTION RECORDED — FORMAL APPROVAL NOT RECORDED** |
| Overall project status | **NO-GO / HOLD** |
| Related memo | `SENTRIX-M1-DM-001` v0.2 |
| Related ASR | `SENTRIX-M1-ASR-001` v1.3 |
| Date recorded | 2026-10-19 (Asia/Saigon) |
| Recorded by | **NOT PROVIDED** |
| Decision source | Direct user instruction in the review session: “bạn toàn quyền nên cứ làm đi” |
| Formal approvers | **NOT PROVIDED** |

> This record captures a **provisional direction** from the project user. It is not a substitute for the named approvals required by the ASR. It does not authorize execution.

---

## 1. ASR-D-01 — M1 target model

| Field | Value |
|---|---|
| Decision statement | Select the M1 target model and resource boundary |
| Recorded direction | **Option A — isolated disposable PostgreSQL instance/cluster** |
| Fallback | **Option B — separate cluster/instance on VM02**, only if A is not feasible |
| Not acceptable for M1 role/privilege tests | **Option C — disposable database inside the existing shared cluster** |
| Deferred | Option D |
| Direction status | **PROVISIONAL — USER INSTRUCTION RECORDED** |
| Formal approval | **NOT RECORDED** |
| Decision owner | **NOT PROVIDED** |
| Rationale | A separates M1 from the existing `sentrix` cluster and avoids conflating disposable-database approval with cluster-level changes |
| Conditions | A/B still require separate change records, environment approval, backup/restore and snapshot/console evidence; `sentrix` remains out of scope |
| Timestamp (UTC) | **NOT RECORDED** |

**Boundary:** This direction does not authorize creating a VM, PostgreSQL instance/cluster, role, HBA, TLS, firewall or SSH change. It only records which model should be pursued in the authorization package.

---

## 2. ASR-D-02 — Exact target environment

No target identifiers have been supplied. All fields remain unresolved.

| Field | Required value | Current status |
|---|---|---|
| Environment model | A or B | **A — provisional direction** |
| Host / VM | Named host | **UNRESOLVED — REQUIRES OWNER CONFIRMATION** |
| PostgreSQL instance/cluster | Name and version | **UNRESOLVED** |
| Port | Explicit port | **UNRESOLVED** |
| Disposable database | Exact database name | **UNRESOLVED** |
| Database owner | Role that owns the DB | **UNRESOLVED** |
| Migration executor | Account/role and host | **UNRESOLVED** |
| Test/read-only account | Account used for tests | **UNRESOLVED** |
| Connection path | Socket or host:port; TLS mode; DNS/hostname | **UNRESOLVED** |
| Network source | Source IP/VM if remote | **UNRESOLVED** |
| Backup/restore scope | Method and isolated restore target | **UNRESOLVED** |
| Snapshot/console | VM snapshot and console access | **UNRESOLVED** |
| Change ticket | Traceable reference | **UNRESOLVED** |
| Environment owner | Accountable person/role | **NOT PROVIDED** |

**Rule:** ASR-D-02 is not approved by this record. It requires the actual values and the named owners' written approval.

---

## 3. Resulting status

| Item | Status |
|---|---|
| ASR-D-01 direction | Provisional: Option A, fallback B |
| ASR-D-01 formal approval | **NOT RECORDED** |
| ASR-D-02 target | **UNRESOLVED** |
| M1 authorization | **NOT GRANTED** |
| M1 execution | **BLOCKED** |
| `sentrix` database | **OUT OF SCOPE** |
| Gates/tests PASS | **NONE** |

---

## 4. What this record permits

- It permits **documentation work** consistent with Option A as the proposed direction.
- It permits preparing a target-record template and a change-record outline.
- It does **not** permit creating infrastructure, connecting to hosts, collecting evidence, installing software, creating roles, changing HBA/TLS/firewall/SSH, running migrations or seeding data.

---

## 5. Required to move forward

1. A named Infrastructure Owner confirms whether an isolated disposable instance/cluster can be provided.
2. The Database Owner and Infrastructure Owner fill ASR-D-02 target fields and record a change ticket.
3. The Supervisor and required approvers record formal approval.
4. Only then may read-only inventory (G2/G4) begin, followed by disposable-environment tests.

Until items 1–3 exist, M1 remains **NO-GO / HOLD — INSUFFICIENT INFORMATION**.

---

## 6. Final statement

**PROVISIONAL DIRECTION: OPTION A.**
**FORMAL APPROVAL: NOT RECORDED.**
**ASR-D-02: UNRESOLVED.**
**M1: BLOCKED.**

No infrastructure, database, network, firewall, SSH, PostgreSQL, role, grant or data change was performed. No command was executed and no evidence was collected.
