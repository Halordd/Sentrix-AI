# SENTRIX web/API GNN workspace

Goal: replace the C-code Devign model in the core with a web/API attack-graph
model. Devign remains a separate appendix experiment.

| Ticket | Scope | Status |
|---|---|---|
| WG-01 | Quarantine Devign from web scoring | **done** |
| WG-02 | Add finding `cwe` + structured `location` | **done** |
| WG-03 | Graph collector from current DB | **done** |
| WG-04 | 40 unauth probes | **done** |
| WG-05 | 20 BOLA/IDOR probes | **done â€” evidence** |
| WG-06 | Human review | **done â€” 20 positive, 40 rejected** |
| WG-07 | Web graph dataset | **done â€” 60 findings, 179 nodes, 480 edges** |
| WG-08 | Hetero SAGE model | **done â€” pilot** |
| WG-09 | Baseline comparison | **done â€” GNN beats severity on tiny test** |
| WG-10 | Corpus 101/40 | **done** |\n| WG-11 | 5 seeds/ablation on 101 | **done — full F1 .6758; no_endpoint .7935** |\n| WG-11b | External batch validation | **done — F1 .619 / .606** |\n| WG-11c | Calibration | **done — uncalibrated best; no method adopted** |\n| WG-12 | WebGoat lab 2 | **done — 40 records, 24 positive** |\n| WG-12b | WebGoat external validation | **done — F1 .9091; baseline .625** |\n| WG-13 | Corpus project import | **done — 141 findings/candidates in `corpus_pilot`** |\n| WG-14 | Read-only corpus API | **done — pilot labels; temp smoke test** |\n| WG-15 | Corpus pilot UI | **done — `/corpus.html`; deploy pending** |\n| WG-16 | Larger calibration holdout | **done — isotonic ECE .1336; still pilot** |
| WG-11 | L2/L3 real | **not done** |

## Pilot result

```text
train=36 valid=12 test=12
test precision=1.0 recall=0.75 f1=0.8571 prAuc=0.9062
test positives=4
severity baseline precision@4=0.25
```

Caveat: 4 test positives. Pilot signal only.

## Leakage fix

First run gave F1 1.0 because `Verification` nodes/edges encoded the label.
Removed both before the reported run.

## Artifacts

```text
backend/training/web_graph/train_web_gnn.py
backend/training/web_graph/web_metrics.json
~/sentrix-gnn/artifacts/web-hgt/model.pt
```

## Next

- independent lab/engagement
- 100+ records / 40+ positives
- 5 seeds + ablations
- calibration
- only then score import
