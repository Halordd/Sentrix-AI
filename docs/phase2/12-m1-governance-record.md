# SENTRIX M1 — Local Governance & Acceptance Record

| Field | Value |
|---|---|
| Document ID | `SENTRIX-M1-GOV-001` |
| Version | 1.0 |
| Date | 2026-10-23 (Asia/Saigon) |
| Scope | Five local VMware VMs only |
| Decision | **ACCEPTED — LOCAL DEMO ONLY** |
| Production use | **NOT APPROVED** |
| External targets | **NOT APPROVED** |
| Decision owner | SENTRIX project owner (local operator) |

## 1. Scope of this acceptance

This record accepts M1 as a **local, simulated demonstrations system**. It does
not authorize production deployment, external scanning, real client data, or
live exploit activity.

The five-VM topology:

| VM | Role | Address |
|---|---|---|
| VM01 | app, UI, API, Nginx | `10.20.10.10` |
| VM02 | PostgreSQL | `10.20.10.20` |
| VM03 | AI mock service | `10.20.10.30` |
| VM04 | worker | `10.20.10.40` / LAB `10.20.20.10` |
| VM05 | isolated lab | `10.20.20.20` |

VM05 has no NAT or default route; lab access is restricted to VM04 LAB and the
administrative host.

## 2. Evidence

| Check | Result | Evidence |
|---|---|---|
| API health | 200 | `/health`, `/health/db` |
| Bootstrap | 200 | 3 projects, 3 findings, 3 scans, 1 report |
| Seed oracle | **51 rows** | `backend/tests/test_seed_oracle.py` |
| Pytest suite | **7 passed** | `backend/tests/` |
| UI navigation | **8 views passed** | `scripts/ui-smoke.mjs` |
| AI-backed analysis | **201** | model `sentrix-ai-mock`, confidence 91 |
| Worker | active | completed a queued scan end-to-end |
| Lab | 200 | Juice Shop from VM04 and Windows |
| Acceptance script | **PASSED** | `scripts/m1/acceptance.py` |

## 3. Decisions

1. **M1 is accepted for local demo use.**
2. **No production or external-scope use is approved.**
3. AI analysis is a deterministic mock; no trained model is claimed.
4. Worker output is simulated; no scanner has contacted any target.
5. The seed is a fixed 51-row fixture and is the parity oracle.
6. Write endpoints are local-demo operations without authentication; they must
   not be exposed beyond the local APP network.
7. SSH password rotation and removal of the exposed credential remain
   operational follow-ups.

## 4. Known risks and limitations

- No authentication or authorization in the API/UI.
- Mock AI and placeholder worker behavior; not production evidence.
- Docker/UEFI and UFW interactions were resolved with host networking for the
  lab; this is a local-lab choice, not a production pattern.
- No formal external sign-off; this is a local project-owner acceptance.
- Backup/restore and disaster recovery are not yet exercised.
- pytest currently covers seed/API contracts, not every mutation endpoint.

## 5. Follow-ups

- Add mutation tests for target, scan, run, status, analysis, remediation,
  verification, report, and publish.
- Exercise backup/restore and VM02 snapshot.
- Rotate SSH credentials and review UFW rules.
- Add authentication before any shared or remote deployment.
- Record the M2 entry decision.

## 6. Approval

The project owner requested and accepted the local M1 demo after reviewing the
evidence above. This approval is limited to the local simulation environment.
