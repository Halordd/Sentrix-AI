# SENTRIX M2 — Local Governance & Acceptance Record

| Field | Value |
|---|---|
| Document ID | `SENTRIX-M2-GOV-001` |
| Version | 1.0 |
| Date | 2026-10-23 (Asia/Saigon) |
| Scope | Five local VMware VMs only |
| Decision | **ACCEPTED — LOCAL DEMO ONLY** |
| Production use | **NOT APPROVED** |
| External targets | **NOT APPROVED** |
| Decision owner | SENTRIX project owner (local operator) |

## 1. Accepted scope

M2 adds a local authentication boundary, role gating, a mutation test suite,
database backup, and a verified restore drill. It does not authorize production
use, external scanning, or shared multi-user deployment.

## 2. Evidence

| Check | Result | Evidence |
|---|---|---|
| Login | **200** | `maya@sentrix.local` → bearer token |
| No-token API access | **401** | `/api/v1/bootstrap` |
| Role gate | Implemented | `VIEWER` cannot POST/PATCH |
| UI smoke | **9 checks passed** | overview + 8 views |
| Pytest | **9 passed** | seed, contract, auth, full mutation workflow |
| Backup | **passed** | custom dump, 25 tables, SHA-256 |
| Restore drill | **passed** | `sentrix_restore_test`: 5 users, 3 findings; database dropped |
| Worker auth | **passed** | authenticated as `maya@sentrix.local` |
| Acceptance script | **PASSED** | authenticated run |

## 3. Conditions

M2 is accepted for local demo only.

1. **SSH password exposure:** the project owner explicitly accepted this risk
   for the local-only demo on 2026-10-23. Rotation remains recommended before
   any shared or remote use.
2. ~~Remove the duplicate `sentrix_migrator` HBA rules on VM02.~~ **Resolved
   2026-10-23:** duplicate removed; one rule remains and VM01 connectivity is
   verified.
3. Do not expose the API or UI beyond the local APP network.
4. Add auth-event audit, rate limiting, and token revocation before shared use.
5. Add TLS before any remote access.
6. Repeat the restore drill after schema or seed changes.
7. Replace the local demo password before any non-demo use.

## 4. Residual risks

- The demo password is shared in local documentation.
- Bearer tokens are stored in browser localStorage.
- Tokens expire but cannot be revoked individually.
- No MFA, SSO, rate limiting, or auth audit.
- HTTP only on the local APP network.
- Backup is manual; no schedule or retention policy.
- The worker uses the demo analyst account.

## 5. Approval

The project owner requested and reviewed M2 evidence. Acceptance is limited to
the local demo environment and is conditional on the items in section 3.
