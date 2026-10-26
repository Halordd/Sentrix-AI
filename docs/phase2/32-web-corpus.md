# SENTRIX — 20-record web corpus

| Field | Value |
|---|---|
| Document ID | `SENTRIX-WEB-CORPUS-001` |
| Date | 2026-10-26 |
| Target | Juice Shop lab `10.20.20.20:3000` |
| Method | GET-only, non-destructive |
| Records | 60 |
| Human-verified positive | 20 |
| False-positive candidates | 31 |\n| BOLA/IDOR pending review | 0 |

## Harness

`backend/training/web_graph/harness.py`

For each probe it records:

- HTTP status
- content type
- body SHA-256
- selected headers
- location (URL path)
- CWE
- severity
- verified/false-positive label + reason

It does not send authentication, exploit payloads, or write requests.

## Label meaning

`verified` here means **the deterministic harness rule confirmed the
observation**, not that a human exploited it.

All records start as:

```text
reviewStatus = RULE_ONLY
```

A human reviewer must use `review.py` to accept or reject each record before it
becomes a training label.

```bash
venv/bin/python training/web_graph/review.py \
  training/web_graph/web_corpus.json --list

venv/bin/python training/web_graph/review.py \
  training/web_graph/web_corpus.json \
  --accept corpus-02 --reviewer "reviewer-name" --note "confirmed header"

venv/bin/python training/web_graph/review.py \
  training/web_graph/web_corpus.json \
  --reject corpus-06 --reviewer "reviewer-name" --note "public by design"
```

Only `HUMAN_VERIFIED`/`HUMAN_REJECTED` records should be used for training.


Examples:

- missing CSP header → verified header finding;
- sensitive path returns JSON 200 → candidate exposure;
- SPA HTML fallback → false-positive candidate, not confirmed exposure.

## Baseline

`backend/training/web_graph/baseline.py`

```text
precision@5  = 0.20
precision@10 = 0.20
precision@20 = 0.25
recall@20    = 1.00
```

The severity heuristic is poor at ranking this corpus. This is the baseline a
future GNN must beat.

## Dataset

`backend/training/web_graph/web_dataset.json`

Graph:

```text
Target → Endpoint → Finding → CWE
                         ↘ Evidence
                         ↘ Verification (if verified)
```

## Why no GNN training

9 rule positives / 40 records is too small for a credible R-GCN/HGT result, and
**zero records have human review**. Training would overfit. Next steps:

1. Expand probes to distinct, genuinely vulnerable cases.
2. Add human verification outcomes.
3. Keep the severity baseline.
4. Train and compare with time/engagement split.

## BOLA/IDOR evidence collector

`backend/training/web_graph/auth_harness.py` requires a human-supplied bearer
token and object IDs:

```bash
venv/bin/python training/web_graph/auth_harness.py \
  --token "$JUICE_TOKEN" \
  --other-basket 2 \
  --other-user 2 \
  --out training/web_graph/bola_corpus.json
```

It is GET-only and writes `PENDING_HUMAN_REVIEW`; it does **not** auto-label.

## Artifacts

```text
backend/training/web_graph/web_corpus.json
backend/training/web_graph/web_dataset.json
backend/training/web_graph/auth_harness.py
```
