# SENTRIX X-01 — Frontend Change Approval Request

| Field | Value |
|---|---|
| Document ID | `SENTRIX-X01-REQUEST-001` |
| Date | 2026-10-26 (Asia/Saigon) |
| Status | **APPROVED — LOCAL DEMO ONLY** |
| Decision owner | SENTRIX project owner (local operator) |
| Approved on | 2026-10-26 (Asia/Saigon) |
| Scope | Local demo frontend only |

## 1. What is being requested

Approval to formally start M5: replace the demo-only frontend adapter with a
repository interface and API-backed implementation, while preserving the
current UI behavior and error messages.

## 2. Current state

The local demo UI already contains changes made during M1–M6:

- `login.html` + token login.
- `api.js` API-backed adapter.
- Project/target/scan/run/status/analysis/remediation/report operations.
- Local demo labels (`API-BACKED`, `POSTGRESQL`).

Those changes were made to make the demo usable; they are **not** retroactive
X-01 approval.

## 3. Why the gate exists

The plan's M5 entry condition (X-01) exists to prevent unreviewed frontend
changes from being treated as approved product behavior. M5 will:

1. Reconcile the existing demo changes into a documented repository interface.
2. Move the transition UI from legacy `/status` to `/transitions`.
3. Add parity checks and browser verification.
4. Keep the in-memory demo path intact.

## 4. Risks of approving

- Browser workflows change from optimistic local mutation to API polling.
- Legacy `/status` can no longer be the only transition path.
- The demo UI may need a visible read-only/error state for API failures.

## 5. Risks of not approving

- The UI keeps using the legacy `/status` endpoint that bypasses the M3 matrix.
- M5 remains blocked; M6/M7 can continue but the frontend stays outside the
  formal migration plan.

## 6. Decision options

- **APPROVE X-01** — start M5 after recording the decision.
- **DEFER** — keep M5 blocked; continue M6/M7.
- **REJECT** — remove/keep the current demo UI changes and document the
  divergence.

## 7. Approval record

| Field | Value |
|---|---|
| Decision | **APPROVED** |
| Owner | SENTRIX project owner (local operator) |
| Date | 2026-10-26 (Asia/Saigon) |
| Scope | Local demo frontend only |
| Conditions | API/UI stays local; M5 parity tests required; no production/external use |

M5 may now proceed on the local demo. The approval does not cover production,
remote access, or external targets.
