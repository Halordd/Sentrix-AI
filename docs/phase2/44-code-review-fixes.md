# SENTRIX — code-review fixes

| Field | Value |
|---|---|
| Document ID | `SENTRIX-REVIEW-FIX-001` |
| Date | 2026-10-27 |
| Scope | Corpus labels, importer, metrics, API validation, docs |
| Status | Fixed in the latest `fix:` commit; GitHub push still needs credentials |

## Why this document exists

The code review found that the checked-in corpus and the trained datasets
disagreed. Several documents reported “40 positive / 101 records” and
“F1 0.9091”, but the corpus actually contained 18 `PENDING_HUMAN_REVIEW`
records. This document is the authoritative correction.

## Corrected label accounting

```text
Juice Shop corpus v2: 101 records
  HUMAN_VERIFIED:        14
  HUMAN_REJECTED:        32
  RULE_ONLY:             37
  PENDING_HUMAN_REVIEW:  18

Review-only training dataset: 46 records
  positive: 14
  negative: 32

WebGoat batch 3: 40 records
  HUMAN_VERIFIED: 24
  HUMAN_REJECTED: 16
```

No pending or rule-only label is used for training.

## Corrected metrics

5-seed, 46 reviewed training records:

| Ablation | F1 mean | F1 std | Precision | Recall | PR-AUC |
|---|---:|---:|---:|---:|---:|
| full | 0.7550 | 0.0863 | 0.9143 | 0.7000 | 0.9929 |
| no_graph | 0.3555 | 0.1276 | 0.2976 | 0.4500 | 0.6143 |
| no_evidence | 0.3605 | 0.2078 | 0.4324 | 0.4500 | 0.5357 |
| no_endpoint | 0.8788 | 0.1497 | 0.9143 | 0.9000 | 0.9857 |
| no_cwe | 0.7352 | 0.1371 | 0.8032 | 0.8000 | 0.8643 |

Severity baseline precision@K: **0.40**.

External WebGoat test:

```text
test: 40 records / 24 positive
F1: 0.7586
precision: 0.6471
recall: 0.9167
ECE: 0.3563
severity baseline precision@24: 0.625
```

This replaces the earlier claims of 40 positives and F1 0.9091.

## Fixes applied

1. `build_dataset.py`
   - target is inferred / configurable instead of hardcoded `target:lab`;
   - `--reviewed-only` includes only `HUMAN_VERIFIED` / `HUMAN_REJECTED`;
   - verification nodes are created only for `HUMAN_VERIFIED`.
2. `import_web_corpus.py`
   - `verified` derives from `reviewStatus == HUMAN_VERIFIED`;
   - target IDs are `target-juice-shop` / `target-webgoat`;
   - target scope is a real URL, not the target name;
   - missing scores fail instead of silently becoming 0.
3. `calibrate_web_gnn.py`
   - fitted temperature is stored as `temperatureValue`, no longer overwritten.
4. Training / scoring
   - fixed seeds in `train_model` and training entry points;
   - dynamic stratified split for small corpora;
   - pending labels are represented as `-1` and excluded from loss.
5. `database/corpus`
   - score precision changed from `numeric(5,4)` to `numeric(7,6)`;
   - added `alter_score_precision.sql`.
6. API
   - `limit` now returns 400 on invalid input instead of 500.
7. UI
   - candidates fetched up to 500 so the summary is not capped at 100.
8. Lab harnesses
   - hardcoded disposable-account passwords replaced by
     `SENTRIX_LAB_PASSWORD`;
   - batch 2 docstring corrected to 41 records and account setup.

## Still open

- 18 Juice Shop records remain pending human review.
- No automated pytest coverage for `/api/v1/corpus/*` yet.
- Production API/UI deploy still requires sudo.
- Score remains `pilot-uncalibrated`.
- Git push still requires user credentials.

## Superseded documents

For metrics, this document supersedes the numeric claims in:

- `docs/phase2/34-web-gnn-5seed-ablation.md`
- `docs/phase2/35-web-gnn-100-run.md`
- `docs/phase2/37-web-gnn-calibration.md`
- `docs/phase2/40-webgoat-external-result.md` (rewritten)
- `docs/phase2/43-webgoat-calibration-holdout.md`
