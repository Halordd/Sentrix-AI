# SENTRIX M4 workspace

Goal: replace hard-coded demo behavior with explicit adapter ports and
replaceable demo implementations, preserving the M1–M3 API contract.

## Scope and guardrails

- Local-only. No external target is contacted.
- M4 does not change the database schema unless a migration is recorded.
- Adapters are wired by configuration; services do not import concrete demo
  adapters directly.
- Conformance tests must run against both the demo adapter and a deliberately
  broken adapter.
- M5 frontend migration is still gated; M4 keeps the current API/UI stable.

## Tickets

| Ticket | Scope | Status |
|---|---|---|
| M4-01 | Define `ScannerPort`, `InferencePort`, `ArtifactStorePort`, `ExecutionBackend` protocols | **done** |
| M4-02 | Demo scanner adapter — `Demo configuration exposure`, LOW, NEW, exact evidence text, one finding per job | **done** |
| M4-03 | Mock inference adapter — 0.91 CRITICAL, 0.76 otherwise, pinned version, simulated | **done** |
| M4-04 | Filesystem artifact store — put/get by sha256, traversal + size + mismatch guards | **done** |
| M4-05 | Subprocess execution backend — timeout, sanitized failure, no shell | **done** |
| M4-06 | Adapter conformance suite — demo and deliberately broken adapter | **done for scanner/inference/artifact/execution** |
| M4-07 | Configuration/DI wiring — swap adapters without service edits | **done** — env-based registry |
| M4-08 | M4 acceptance and governance record | **accepted — local demo only** |

## Entry context

M3 is accepted for local demo only. Known M3 gaps relevant to M4:

- The API currently hard-codes simulated scan and analysis behavior.
- Legacy `PATCH /findings/{id}/status` bypasses the transition matrix.
- No optimistic locking or idempotency.

## Acceptance anchors

From `06-migration-and-acceptance.md`:

- AT-4.2 demo finding: `Demo configuration exposure`, severity `LOW`,
  status `NEW`, evidence contains “No external target was contacted”.
- AT-4.3 confidence 0.91 for `CRITICAL`, 0.76 otherwise.
- AT-4.7 prompt/model pinning and content-hash check.
- AT-4.8 mock provenance (`is_mock=true`, `simulated=true`).

## Current evidence

- `backend/app/ports.py` defines the four ports.
- `DemoScannerAdapter` returns exactly one finding:
  `Demo configuration exposure`, `LOW`, `NEW`, evidence contains
  “No external target was contacted”.
- `run_simulated_scan` now calls the adapter; endpoint response keeps the same
  shape and returns `Low` / `New`.
- Scanner conformance test passes for the demo adapter and fails for a
  deliberately broken adapter.
- `MockInferenceAdapter`: CRITICAL → 0.91, HIGH/MEDIUM/LOW → 0.76, model/version
  pinned, `simulated=true`; wired into `POST /findings/{id}/analyses`.
- `FilesystemArtifactStore`: content-addressed put/get/delete, traversal key
  rejected, oversized rejected, tampered hash rejected.
- `SubprocessExecutionBackend`: no shell, hard timeout, process-group kill,
  output limit, invalid command rejection.
- `adapters.py` selects scanner/inference/execution/artifact via env; defaults:
  `demo`, `mock`, `subprocess`, `~/sentrix-artifacts`.
- `run_simulated_scan` and `create_analysis` call the registry, not concrete
  adapters.
- Full suite against latest auth API: **34 passed**.
- Seed after tests: analysis 1 · finding 3 · audit 2.

