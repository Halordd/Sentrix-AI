# SENTRIX L3-C workspace

Goal: conditional automation with signed scope, policy, approval and a
read-only sandbox executor. No arbitrary exploitation code.

| Ticket | Scope | Status |
|---|---|---|
| L3-01 | Signed scope manifest + HMAC verification | **done** |
| L3-02 | Action catalog with R0–R3 tiers | **done** |
| L3-03 | Policy engine: scope/tier/budget/expiry/snapshot | **done** |
| L3-04 | Admin API: actions/check/candidates/requests | **done** |
| L3-05 | Manifest CLI | **done** |
| L3-06 | R0 read-only sandbox executor | **done — R1 not implemented** |
| L3-07 | R2 approval workflow | **done** |
| L3-08 | VM05 snapshot/rollback scripts | **done — snapshot tested** |
| L3-09 | GNN candidate ranking → queue | **interface ready; model pending** |
| L3-10 | L2 vs L3-C evaluation | **policy simulation done** |

## Evidence

- Backend suite: **59 passed**
- R0 executor tests: local server, redirects disabled, host allowlist
- R2 test: candidate → PENDING → approval → APPROVED
- VM05 snapshot: `lab-check` image + metadata created
- L2/L3 simulation: 20 candidates → 17 auto, 2 approval, 1 denied
- Backup: **30 tables**, verification passed

## Not yet implemented

- R1 safe-PoC executor
- live GNN scores (queue accepts `score`; no model artifact yet)
- kill-switch UI
- live execution of approved R2 actions

See [`docs/phase2/26-l3-conditional-automation.md`](../../docs/phase2/26-l3-conditional-automation.md).
