# SENTRIX — L3 conditional automation

| Field | Value |
|---|---|
| Document ID | `SENTRIX-AUTO-L3-001` |
| Date | 2026-10-26 |
| Status | Design proposal |
| Scope | Isolated lab, human-signed authorization |
| Autonomy | L3-C: conditional, non-destructive, pre-approved action classes |

## 1. Definition

L3 is **not** “the system authorizes itself”.

L3 means:

> A human signs the engagement scope and **pre-approves an action catalog**.
> The system may then execute only those pre-approved, non-destructive actions,
> within budget, against allowlisted lab targets, with rollback and audit.

Human remains:

- the authority that grants scope;
- the owner of high-impact decisions;
- on the loop, able to abort.

## 2. Non-negotiables

1. No self-granted authorization.
2. No target outside the signed scope.
3. No external network destination.
4. No persistence, evasion, credential theft, data exfiltration, or destructive
   payloads.
5. No arbitrary shell or arbitrary exploit code. Only catalogued actions.
6. Snapshot before action; rollback after.
7. Kill switch at orchestrator and executor.
8. Every action produces an append-only audit record.
9. High/critical findings require human review before resolution.
10. Model cannot verify, resolve, or expand scope.

## 3. Authorization envelope

The signed manifest should contain:

```json
{
  "engagementId": "...",
  "authorizedBy": "...",
  "validFrom": "...",
  "validUntil": "...",
  "targets": ["10.20.20.20"],
  "excludedTargets": [],
  "allowedActionClasses": ["READ_ONLY", "SAFE_POC"],
  "maxRiskTier": 1,
  "maxActions": 20,
  "maxDurationMinutes": 30,
  "snapshotRequired": true,
  "humanOnLoop": true
}
```

The manifest is signed and hashed. Every executor checks the hash.

## 4. Action tiers

| Tier | Examples | L3 behavior |
|---|---|---|
| R0 | read-only discovery, version check, evidence capture | auto |
| R1 | safe PoC, non-destructive validation | auto within budget |
| R2 | state-changing, auth bypass proof, write action | human approval |
| R3 | persistence, evasion, exfiltration, destructive | prohibited |

L3-C only auto-runs R0/R1. It never auto-runs R2/R3.

## 5. Policy decision

```text
candidate = GNN-ranked finding
action = catalog.match(candidate)
if action is None: reject
if action.tier > manifest.maxRiskTier: reject
if target not in manifest.targets: reject
if target in exclusions: reject
if budget exhausted: stop
if snapshot missing: stop
if action.tier >= 2: require human approval
else: execute
```

The GNN only changes the **order** of candidates. It cannot change the policy
result.

## 6. GNN integration

```text
finding / function
      ↓
GNN probability + explanation
      ↓
priority score
      ↓
candidate queue
      ↓
policy engine
      ↓
catalog action or reject
```

Rules:

- model uncertainty → abstain;
- low confidence → rank lower, do not auto-run;
- model output is an input to policy, never a policy decision;
- explanation is attached to audit.

## 7. Sandbox requirements

- VM05 only; no NAT/default route.
- Snapshot before run, rollback after.
- Allowlist destination `10.20.20.20:3000`.
- No host filesystem mount.
- CPU/memory/time limits.
- No outbound DNS beyond lab.
- Action runner has no credentials.
- Kill switch and heartbeat watchdog.

## 8. Verification

L3 auto-runs only non-destructive validation. Verification:

- capture request/response hashes;
- compare expected vs observed;
- repeat check once;
- roll back state;
- attach evidence;
- mark finding **candidate verified**, not resolved.

Resolution still requires human verification.

## 9. Evaluation

Compare L2 vs L3:

| Metric | What it shows |
|---|---|
| time-to-triage | automation benefit |
| findings verified per hour | throughput |
| false-positive actions | model/policy quality |
| human interventions | trust/exception rate |
| rollback count | state safety |
| audit completeness | governance |
| out-of-scope attempts | guardrail quality |
| destructive actions | must be zero |

A L3 result is only credible if “destructive actions = 0” and “out-of-scope
attempts = 0” across the evaluation.

## 10. Failure modes

- GNN false positive → wrong candidate ranking, not wrong authorization.
- stale scope → expiry check rejects.
- target drift/DNS change → pinned IP + allowlist.
- action catalog bug → tier gate + review.
- snapshot failure → stop.
- budget exhaustion → stop, report partial.

## 11. L3 vs L4

| Aspect | L3-C | L4 |
|---|---|---|
| Authorization | human-signed | self-granted |
| Scope | fixed manifest | model/planner can change |
| Exploitation | non-destructive, catalogued | arbitrary |
| Human | on the loop | absent |
| Risk | bounded | unacceptable |

L4 is rejected.

## 12. Implementation roadmap

1. Signed scope manifest + hash verification.
2. Policy engine and action catalog.
3. Snapshot/rollback orchestration.
4. GNN priority queue integration.
5. R0/R1 action implementations.
6. Approval/exception workflow for R2.
7. Audit + kill switch.
8. L2 vs L3 evaluation harness.

## 13. Acceptance criteria

- all actions trace to signed manifest;
- zero out-of-scope executions;
- zero destructive actions;
- every action has snapshot/rollback;
- high/critical findings still human-reviewed;
- GNN cannot change policy outcome;
- audit reconstructs the full decision path.

## 14. Implemented increment

Current implementation:

- `backend/app/automation.py` — manifest signing/verification, action catalog,
  tier policy, budget/expiry/scope checks.
- `backend/tools/make_automation_manifest.py` — operator manifest generator.
- `POST /api/v1/automation/check` — admin-only decision endpoint; audits every
  decision.
- `GET /api/v1/automation/actions` — admin-only catalog.
- `automation_candidate` / `automation_request` queue with R2 approval.
- `ReadOnlyExecutor` — R0 only; no shell, no redirects, host allowlist.
- VM05 `snapshot_juice.sh` / `rollback_juice.sh`.
- backend suite: **59 passed**.

Not implemented yet:

- R1 safe-PoC executor;
- automatic snapshot/rollback orchestration around execution;
- kill switch/UI;
- live GNN candidate scores.

This is deliberate: policy and audit must be proven before execution exists.

