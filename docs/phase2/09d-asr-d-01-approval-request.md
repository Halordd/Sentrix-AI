# SENTRIX M1 — ASR-D-01 Approval Request

| Field | Value |
|---|---|
| Document ID | `SENTRIX-M1-ASR-D-01-AR-001` |
| Version | 0.2 — Draft |
| Status | **DRAFT — NOT SENT** |
| Revision | 0.2 — added delivery handoff checklist; delivery status unchanged |
| Request type | Formal decision request for `ASR-D-01` |
| Related record | `docs/phase2/09b-asr-d-01-d-02-decision-record.md` |
| Related memo | `docs/phase2/09-decision-memo-001-m1-target-environment.md` |
| Related tracker | `docs/phase2/09c-m1-decision-readiness-tracker.md` |
| Date prepared | 2026-10-22 (Asia/Saigon) |
| Prepared by | **NOT PROVIDED** |
| Recipients | Supervisor; Infrastructure Owner |
| Recipient identities / channel | **NOT PROVIDED** |
| Approval evidence received | **NONE** |

> This is a **request**, not an approval, not a decision record, and not an execution authorization. It has not been sent. All proposed content remains subject to the named approvers' written decision.

---

## 1. Why this request exists

`ASR-D-01` is currently **`PROVISIONAL — FORMAL APPROVAL NOT RECORDED`**. The provisional direction is Option A, but the required Supervisor and Infrastructure Owner decisions, identity/role, ticket, timestamp and approval evidence are missing.

This request asks for the exact information needed to complete the formal decision record. It does not resolve `ASR-D-02`, which remains `UNRESOLVED`.

---

## 2. Proposed decision — not approved

| Item | Proposal |
|---|---|
| Model | **Option A** — isolated, disposable PostgreSQL instance/cluster dedicated to M1 |
| Fallback | **Option B** — separate cluster/instance on VM02, only if Option A is infeasible and explicitly approved with documented conditions |
| Excluded for M1 role/privilege tests | **Option C** — disposable database inside the existing shared cluster |
| Defer | **Option D** — no target decision; M1 remains blocked |
| Recommendation status | **PROPOSED — NOT SELECTED** |

### Proposed scope if Option A is approved

- M1 database foundation in the isolated disposable environment: schema, migrations, seed, roles/privileges and tests.
- `sentrix` database remains **out of scope**.
- Cluster-level operations inside the disposable instance still require explicit authorization and a separate change record.
- OS/network changes, provisioning, snapshots and service changes require separate infrastructure authorization.

### Proposed exclusions

Nginx/frontend; AI serving; worker/scanner; Docker/Juice Shop; VMware/NIC/Netplan; OS upgrades; PostgreSQL installation/reinstallation/restart; HBA; TLS; firewall/SSH; shared roles/grants; any `sentrix` change; migrations/seed in any shared database; production changes.

### Proposed conditions

1. Formal written approval from the Supervisor and Infrastructure Owner.
2. `ASR-D-02` target record completed before any target use.
3. `ASR-D-03` through `ASR-D-10` resolved as applicable to the requested operation.
4. Change ticket and named implementer recorded.
5. Read-only scope, accounts and evidence handling approved.
6. Snapshot/console, backup/restore and rollback evidence established before state changes.
7. No execution before approval and all preconditions are met.

### Rollback/recovery expectations

- Disposable environment: recreate/drop the isolated instance/database; this is not production recovery.
- VM snapshot: whole-VM recovery only; not a database backup.
- PostgreSQL backup/restore: requires a validated isolated restore test before reliance.
- Alembic downgrade: schema reversal only; not guaranteed data recovery.
- Configuration rollback: restores prior configuration; not data.
- No recovery claim is made in this request.

### Proposed validity/review

- Proposed validity: **30 days** — recommendation only, not effective.
- Start/expiry date: **UNRESOLVED**.
- Review triggers: material change to target, artifacts, network path, role model or risk profile.
- Review/expiry date must be recorded by the approver or marked `N/A` with rationale.

---

## 3. Required response fields

The approver must supply all of the following. Missing fields keep `ASR-D-01` provisional.

| # | Field | Response |
|---|---|---|
| 1 | Approver name | **REQUIRED** |
| 2 | Approver role (Supervisor / Infrastructure Owner / both with separation-of-duties exception) | **REQUIRED** |
| 3 | Explicit choice: Option A / B / C / D | **REQUIRED** |
| 4 | Rationale | **REQUIRED** |
| 5 | Scope, exclusions and conditions confirmed or amended | **REQUIRED** |
| 6 | Ticket/change-record reference, or documented `N/A` with reason | **REQUIRED** |
| 7 | Decision timestamp and timezone (UTC preferred) | **REQUIRED** |
| 8 | Approval/signature reference | **REQUIRED** |
| 9 | Review/expiry date, or documented `N/A` rationale | **REQUIRED** |

### Response form

```
ASR-D-01 formal decision

Approver name:
Approver role:
Selected option (A/B/C/D):
Rationale:
Scope/exclusions/conditions:
Ticket/change-record:
Timestamp (UTC):
Approval/signature reference:
Review/expiry date (or N/A rationale):
```

---

## 4. Separation of duties

- **Supervisor** and **Infrastructure Owner** are the required approvers per the existing memo.
- If one person holds both roles, the response must explicitly record the combined-role exception and compensating controls.
- A general instruction to continue, a documentation instruction, or a request to send this artifact is **not** approval.

---

## 5. Delivery status

| Field | Value |
|---|---|
| Sent? | **NO — DRAFT ONLY** |
| Delivery channel | **NOT PROVIDED** |
| Recipient addresses | **NOT PROVIDED** |
| Tool result | **N/A — no connected approval channel used** |
| Approval evidence received | **NONE** |

No email, ticket, message or external request was sent. This artifact is intended for manual delivery by the user after recipient details are confirmed.

---

## 6. Resulting status

| Item | Status |
|---|---|
| `ASR-D-01` | **PROVISIONAL — FORMAL APPROVAL NOT RECORDED** |
| `ASR-D-02` | **UNRESOLVED** |
| Execution authorization | **NOT ESTABLISHED** |
| Gates/tests PASS | **ZERO** |
| Overall | **NO-GO / HOLD** |

Until the required response is supplied and recorded, no target resolution, repository inventory, infrastructure change, database connection, migration, role change or acceptance test may begin.

---

## 7. Delivery handoff checklist

No verified recipient identity, contact channel, ticketing workflow or authorized delivery integration was found in the repository documentation. The user must supply the following before this request can be sent.

| # | Required input | Status |
|---|---|---|
| 1 | Supervisor name and approved contact/channel | **MISSING** |
| 2 | Infrastructure Owner name and approved contact/channel | **MISSING** |
| 3 | Ticket/change-record ID, or the approved process for obtaining one | **MISSING** |
| 4 | Delivery choice: manual send by the user, or a named authorized integration | **MISSING** |
| 5 | If one person holds both approver roles, the approved separation-of-duties exception and compensating controls | **MISSING** |
| 6 | Requested review/expiry date, or confirmed `N/A` rationale | **MISSING** |

After sending:

- retain the actual sent message and delivery evidence;
- do not mark this artifact `SENT` unless the delivery tool or sender confirms success;
- do not mark `ASR-D-01` approved unless a traceable approver response is received and recorded;
- update `09b`, `09`, and `09c` only from that response.

## 8. References

- [`09b-asr-d-01-d-02-decision-record.md`](09b-asr-d-01-d-02-decision-record.md)
- [`09-decision-memo-001-m1-target-environment.md`](09-decision-memo-001-m1-target-environment.md)
- [`09c-m1-decision-readiness-tracker.md`](09c-m1-decision-readiness-tracker.md)
- [`09a-decision-memo-001-transmittal.md`](09a-decision-memo-001-transmittal.md)
