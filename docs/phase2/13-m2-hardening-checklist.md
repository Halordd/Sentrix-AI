# SENTRIX M2 — Hardening Checklist

| Control | State | Note |
|---|---|---|
| API authentication | Implemented | Bearer HMAC token, 8h TTL; verified 401 without token |
| Login UI | Implemented | `/login.html`; UI smoke passed |
| Password hash | Implemented | PBKDF2-SHA256, 210k iterations |
| Role gate | Implemented | writes require `ANALYST` or `ADMIN` |
| Secret storage | Implemented | `~/sentrix-backend/.env`, mode 600 |
| Backup | Verified | 25 tables, checksum |
| Restore | **Passed** | local-peer restore into `sentrix_restore_test`: 5 users, 3 findings; DB dropped |
| Worker auth | Implemented | authenticated as `maya@sentrix.local` |
| Placeholder worker | Disabled | `sentrix-worker` inactive |
| Mutation tests | **9 passed** | full workflow incl. cleanup |
| SSH password rotation | **Accepted risk** | local-only demo; rotate before shared/remote use |
| Remove duplicate migrator HBA rules | **Resolved** | one `hostssl sentrix sentrix_migrator 10.20.10.10/32` rule remains |
| UFW review | Pending | APP 80; AI 8001 from VM01; LAB 3000 from LAB/.1 |
| MFA / SSO | Not in scope | local demo |
| TLS | Not in scope | local HTTP only |
| Backup schedule | Not implemented | manual script |
| Restore drill | **Passed** | `sentrix_restore_test` created, restored, verified, dropped |
| Auth rate limiting | Not implemented | local demo |
| Token revocation | Not implemented | token expiry only |
| Audit of auth events | Not implemented | current audit is demo data |

## Required operator actions

1. Restart `sentrix-api` and copy `login.html`, `api.js`, `app.js` to
   `/var/www/sentrix`.
2. Restart `sentrix-worker-real` so it uses authenticated requests.
3. Rotate the `sentrixadmin` SSH password.
4. Remove the duplicate migrator rules from VM02 `pg_hba.conf`.
5. Run an offline restore drill into `sentrix_restore_test`.
