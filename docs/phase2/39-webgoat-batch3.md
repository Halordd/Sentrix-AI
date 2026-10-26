# SENTRIX — WebGoat lab + batch 3

| Field | Value |
|---|---|
| Document ID | `SENTRIX-LAB-003` |
| Date | 2026-10-26 |
| Target | OWASP WebGoat, VM05 `10.20.20.20:8080` |
| Container | `sentrix-webgoat` |
| Image | `webgoat/webgoat:latest` |
| Batch 3 | 40 GET-only records |
| Status | Lab up; records pending human review |

## Provisioning

```bash
docker pull webgoat/webgoat:latest
docker run -d --name sentrix-webgoat --restart unless-stopped \
  -p 8080:8080 webgoat/webgoat:latest
```

Verified from VM01:

```text
GET http://10.20.20.20:8080/WebGoat/ → 302 (login)
```

## Batch 3

```text
records: 40
HTTP 200: 32
HTTP 302: 8
header candidates: 20
path HTTP 200: 12
reviewStatus: PENDING_HUMAN_REVIEW
```

### Strong actuator candidates

These returned Spring Boot Actuator JSON, not SPA HTML:

```text
b3-path-01  /WebGoat/actuator          200  actuator v3 JSON
b3-path-02  /WebGoat/actuator/health   200  actuator v3 JSON
b3-path-04  /WebGoat/actuator/env      200  actuator v3 JSON
b3-path-09  /WebGoat/actuator/configprops 200 actuator v3 JSON
```

`env` and `configprops` are especially sensitive and must be reviewed by a human.

### Likely false positives

```text
b3-path-13 robots
b3-path-14 .git/config
b3-path-19 swagger-ui
b3-path-20 h2-console
```

These returned the same HTML fallback body hash; do not accept them as exposed
resources without checking the body.

## Artifacts

```text
backend/training/web_graph/batch3_harness.py
backend/training/web_graph/web_corpus_batch3.json
backend/training/web_graph/batch3_review_sheet.csv
~/sentrix-backend/training/web_graph/batch3_review_sheet.csv
```

## Next

1. Human review of the 40 records.
2. Build batch 3 dataset.
3. Train on batch 1+2, test on batch 3 (real external lab).
4. Compare with the previous calibration results.
5. Only then decide whether score import is justified.
