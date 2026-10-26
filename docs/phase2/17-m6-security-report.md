# SENTRIX M6 — Security Review & Suite Report

| Field | Value |
|---|---|
| Document ID | `SENTRIX-M6-SEC-001` |
| Version | 1.0 |
| Date | 2026-10-26 (Asia/Saigon) |
| Scope | Local five-VM demo |
| Status | Security suite green; production/external use not approved |

## 1. Least privilege (M6-06)

`sentrix_app` grants:

- 70 table privileges across public tables.
- No `CREATE` on schema `public`.
- `USAGE` on schema `public` only.
- No `TRUNCATE`, `REFERENCES`, or `TRIGGER`.
- `DELETE` only on `project_member`.
- No `UPDATE`/`DELETE` on `audit_event`, `finding_status_event`, or
  `prompt_template_version`.
- App connects as `sentrix_app`; `sentrix_migrator` is not used by the API.

Tests:

- `test_app_role_identity_and_schema_privilege`
- `test_app_role_cannot_mutate_append_only_tables`
- `test_app_role_delete_is_scoped_to_project_member`
- `test_app_role_cannot_delete_audit_rows`

## 2. Secret redaction

- API login/bootstrap/me payloads contain no `password_hash`, PBKDF2 hash,
  demo password, database URL, or `SENTRIX_SECRET_KEY`.
- Served `app.js`, `api.js`, and `login.html` contain no password literals or
  secret key.
- `~/sentrix-backend/.env` and `~/.pgpass` are mode `600`.
- API unit loads the secret via `EnvironmentFile`.
- Artifact download is authenticated, octet-stream, attachment, nosniff;
  unknown keys return 404; project ownership is enforced through the
  `artifact` metadata table and project membership.
- Tests: `test_api_payloads_have_no_secret_material`,
  `test_frontend_bundle_has_no_password_literals`.

## 3. Rate limit, revocation, auth audit (M6-05)

- API: 600 requests/minute per client.
- Login: 60 requests/minute per client.
- Excess → `429` + `Retry-After: 60`.
- Logout revokes the token fingerprint; reuse → `401`.
- Auth audit records login `SUCCESS`/`DENIED` and logout `SUCCESS`.
- Rate and revocation stores use PostgreSQL when `SENTRIX_SHARED_AUTH=1`; otherwise in-memory.
- Tests clean `auth.*` rows to keep the 51-row seed oracle stable.

## 4. Security suite (M6-07)

Command:

```bash
cd ~/sentrix-backend && venv/bin/pytest -q
```

Result:

```text
49 passed
```

Covers auth, roles, transitions, scan/verification guards, atomic claims,
artifact download, rate limiting, token revocation, least privilege, and secret
exposure.

Seed after the suite:

```text
audit_event 2 · finding 3
```

## 5. TLS

Self-signed HTTPS is active at `https://10.20.10.10/`; `curl -k` returns UI
`200` and API `401`. HTTP remains available for the local worker path. Browser
trust is not established; MFA/SSO remain out of scope.

## 6. Residual risks

- Rate limit and token denylist are process-local.
- Demo passwords are documented for local use.
- HTTP only; no TLS.
- No MFA/SSO.
- Worker egress allowlist and hardened unit are prepared but operator
  install/verification is still pending.
- M5 frontend migration remains gated on X-01.
- No production or external use approval.
