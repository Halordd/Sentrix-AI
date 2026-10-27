# SENTRIX — Corpus pilot UI

| Field | Value |
|---|---|
| Document ID | `SENTRIX-CORPUS-UI-001` |
| Date | 2026-10-26 |
| Page | `/corpus.html` |
| API | `/api/v1/corpus/*` |
| Status | Code complete; production deploy/restart pending |
| Labels | `pilot: true`, `pilot-uncalibrated` |

## Page

`frontend/corpus.html` + `frontend/corpus.js`

Shows:

- project summary;
- target counts;
- top candidates with score/action/verified;
- findings with severity/CWE/score/verified;
- explicit pilot banner.

A `Corpus pilot` link was added to the main console top bar.

## API routes

```text
GET /api/v1/corpus/projects
GET /api/v1/corpus/findings?targetId=...&limit=...
GET /api/v1/corpus/candidates?limit=...
```

Admin-only and read-only.

## Smoke test

Ran against a temporary API process:

```json
{
  "loginStatus": 200,
  "project": {"id": "project-corpus-pilot"},
  "targets": [
    {"id": "target-juice-shop", "name": "Juice Shop", "findings": 101},
    {"id": "target-webgoat", "name": "WebGoat", "findings": 40}
  ],
  "pilot": true,
  "scoreLabel": "pilot-uncalibrated"
}
```

## Deploy

Files are staged on VM01 at:

```text
~/sentrix-backend/frontend/corpus.html
~/sentrix-backend/frontend/corpus.js
~/sentrix-backend/frontend/app.js
```

Deploy:

```bash
sudo cp ~/sentrix-backend/frontend/corpus.html /var/www/sentrix/
sudo cp ~/sentrix-backend/frontend/corpus.js /var/www/sentrix/
sudo cp ~/sentrix-backend/frontend/app.js /var/www/sentrix/
```

Restart API for the routes:

```bash
sudo systemctl restart sentrix-api
```

Open:

```text
https://10.20.10.10/corpus.html
```

Login with an ADMIN account, because the corpus routes require admin.

## Tests

```text
backend: 62 passed
frontend: existing suite has Windows EPERM limitation in this environment
JS syntax: node --check passed
```

## Limitations

- Scores remain **pilot and uncalibrated**.
- No re-score with a calibrated model yet.
- The page is a separate read-only view, not part of the main SPA router.
- The corpus schema remains isolated from public seed data.
