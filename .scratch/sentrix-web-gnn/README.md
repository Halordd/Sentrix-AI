# SENTRIX web/API GNN workspace

Goal: replace the C-code Devign model in the core with a web/API attack-graph
model. Devign remains a separate appendix experiment.

| Ticket | Scope | Status |
|---|---|---|
| WG-01 | Quarantine Devign from web scoring | done |
| WG-02 | Finding cwe/location context | done |
| WG-03 | Graph collector | done |
| WG-04 | 40 unauth probes | done |
| WG-05 | 20 BOLA/IDOR probes | done |
| WG-06 | Human review | **partial — 46 reviewed, 18 pending** |
| WG-07 | Web graph dataset | **partial — reviewed-only 46 records** |
| WG-08 | Hetero SAGE model | done — pilot |
| WG-09 | 5 seeds + ablation | **done on 46 reviewed records** |
| WG-10 | WebGoat lab 2 | done — 40 records / 24 positive |
| WG-11 | External WebGoat test | **done — F1 0.7586** |
| WG-12 | Calibration | **done — pilot; not production** |
| WG-13 | Corpus project import | done — 141 findings/candidates |
| WG-14 | Read-only corpus API | done |
| WG-15 | Corpus pilot UI | code done; deploy pending |
| WG-16 | Score import | **pilot-uncalibrated only** |

## Corrected metrics

Training uses only HUMAN_VERIFIED / HUMAN_REJECTED:

```text
reviewed train: 46 (14 positive / 32 negative)
pending: 18
WebGoat test: 40 (24 positive / 16 negative)
```

5-seed mean:

```text
full        F1 0.7550 ± 0.0863
no_graph    F1 0.3555
no_evidence F1 0.3605
no_endpoint F1 0.8788
no_cwe      F1 0.7352
severity baseline precision@K 0.40
```

External WebGoat:

```text
F1 0.7586, precision 0.6471, recall 0.9167
baseline precision@24 0.625
ECE 0.3563
```

## Caveats

- 18 records remain pending; do not claim 40 positives.
- Test set is small.
- Calibration is not production-grade.
- Scores are `pilot-uncalibrated`.
- No score import into production.
