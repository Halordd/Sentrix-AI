# SENTRIX M4 — Local Governance & Acceptance Record

| Field | Value |
|---|---|
| Document ID | `SENTRIX-M4-GOV-001` |
| Version | 1.0 |
| Date | 2026-10-23 (Asia/Saigon) |
| Scope | Five local VMware VMs only |
| Decision | **ACCEPTED — LOCAL DEMO ONLY** |
| Production use | **NOT APPROVED** |
| External targets | **NOT APPROVED** |
| Decision owner | SENTRIX project owner (local operator) |

## 1. Accepted scope

M4 extracts the demo scanner, mock inference, artifact store, and execution
backend behind explicit ports, with an environment-selected adapter registry.
It does not implement a real scanner, remote inference adapter, or production
execution isolation.

## 2. Evidence

| Check | Result |
|---|---|
| `ScannerPort` / `InferencePort` / `ArtifactStorePort` / `ExecutionBackend` | defined |
| Demo scanner | `Demo configuration exposure`, `LOW`, `NEW`, one finding |
| Demo evidence | contains “No external target was contacted” |
| Mock inference | 0.91 CRITICAL, 0.76 otherwise; pinned 4.8.2 |
| Artifact store | sha256 put/get/delete; traversal/size/hash guards |
| Execution backend | no shell, timeout, process-group kill, output cap |
| DI registry | env-selected scanner/inference/execution/artifact |
| Conformance | demo passes; deliberately broken scanner fails |
| Full pytest | **34 passed** |
| Seed after tests | analysis 1, finding 3, audit 2 |

## 3. Decisions

1. M4 is accepted for local demo use.
2. The default adapters are `demo`, `mock`, `subprocess`, and filesystem
   artifacts.
3. `run_simulated_scan` and `create_analysis` use the adapter registry.
4. No schema, endpoint, or UI path was intentionally changed.
5. Remote inference is not selected by default; the mock adapter owns the
   analysis result for the local demo.

## 4. Known gaps and conditions

1. The execution backend is not yet used by the scanner adapter.
2. The artifact store is not exposed through the API.
3. AT-4.7 prompt pinning is only partially represented; the mock adapter does
   not verify the prompt-template content hash.
4. The demo scanner is deterministic and does not exercise the execution
   backend.
5. M4 conformance is local and does not replace M6 isolation/egress tests.
6. Production/external use remains unapproved.
7. M5 remains gated on X-01 frontend-change approval; the current demo UI
   changes were made outside that formal gate and must be reconciled in M5.

## 5. Approval

The project owner reviewed M4 evidence and accepted it for the local demo only.
M5 may be planned but not treated as formally approved until X-01 is recorded.
