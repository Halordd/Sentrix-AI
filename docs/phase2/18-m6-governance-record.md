# SENTRIX M6 — Local Governance & Acceptance Record

| Field | Value |
|---|---|
| Document ID | `SENTRIX-M6-GOV-001` |
| Version | 1.0 |
| Date | 2026-10-26 (Asia/Saigon) |
| Scope | Five local VMware VMs only |
| Decision | **ACCEPTED — LOCAL DEMO ONLY** |
| Production use | **NOT APPROVED** |
| External targets | **NOT APPROVED** |
| Decision owner | SENTRIX project owner (local operator) |

## 1. Accepted scope

M6 hardens the local demo: atomic worker claims, heartbeat/recovery, worker
sandboxing, egress allowlist, authenticated artifact download, rate limiting,
token revocation, auth audit, least-privilege review, and a security test suite.

This record does not approve shared, remote, or production use.

## 2. Evidence

| Control | Result |
|---|---|
| Atomic claim | second claim on one job → 204 |
| Heartbeat/recovery | heartbeat endpoint; stale recovery implemented |
| Worker sandbox | hardening properties installed; `systemd-analyze security` score **1.6 OK** |
| Worker egress | API/LAB/DNS/loopback only; default outgoing deny; worker idle |
| Worker runtime | active, idle logs |
| API tests | **49 passed** on production API |
| Artifact download | octet-stream, attachment, nosniff; unknown key 404 |
| TLS | CA-signed local HTTPS listener active; UI/API 200/401 over TLS |
| Rate limit | 600 API/min, 60 login/min; 429 + Retry-After |
| Token revocation | logout then reuse → 401 |
| Auth audit | login SUCCESS/DENIED + logout SUCCESS |
| Worker recovery | automated stale-run test passes |
| Least privilege | schema CREATE false; DELETE only `project_member`, `revoked_token`, `rate_limit_bucket`; append-only protected |
| Secret exposure | API/frontend payloads clean; `.env`/`.pgpass` mode 600 |

## 3. Conditions

1. ~~Verify VM04 egress allowlist with `sudo ufw status numbered`.~~
   **Resolved 2026-10-26:** allowlist applied; default outgoing deny; worker
   remained authenticated and idle; API `/health` reachable from VM04.
2. Rate limiter and token denylist are process-local; use a shared store before
   multi-process or shared deployment.
3. ~~Successful login is not audited; add it before shared use.~~ **Resolved
   2026-10-26:** login SUCCESS is audited; test cleanup keeps the seed oracle
   stable.
4. **TLS applied** as a CA-signed local listener on 2026-10-26
   (`https://10.20.10.10/`); browser trust is not established. MFA/SSO remain
   out of scope. HTTP remains available for the local worker/API path.
5. M5 remains gated on X-01 frontend-change approval.
6. Production and external target use remain unapproved.
7. Re-run the security suite after any schema, auth, or worker change.

## 4. Residual risks

- Demo credentials are documented for local use.
- Artifact download now has per-project authorization via the `artifact`
  metadata table and membership check.
- Rate limiting/revocation uses PostgreSQL when `SENTRIX_SHARED_AUTH=1`; otherwise in-memory.

## 5. Approval

The project owner reviewed the M6 evidence and accepted the local demo
conditionally, subject to the egress verification and shared-use conditions
above. Production use remains unapproved.
