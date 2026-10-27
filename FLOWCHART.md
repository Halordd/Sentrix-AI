# SENTRIX — system flowchart

> As of 2026-10-26. This supersedes the earlier 26-table / Juice-Shop-only chart.

## 1. Lab topology

```mermaid
flowchart TB
    subgraph HOST["Windows host · 10.20.10.1"]
        BROWSER[Browser · HTTPS]
    end

    subgraph VM01["VM01 sentrix-app · 10.20.10.10"]
        NGINX[Nginx · :80 / :443<br/>local CA + TLS]
        WEB[frontend/<br/>console + corpus.html]
        API[FastAPI :8000<br/>auth · findings · scans<br/>L3 automation · corpus views]
        ART[artifact store<br/>~/sentrix-artifacts]
        NGINX -->|static| WEB
        NGINX -->|/api/ proxy| API
        API --> ART
    end

    subgraph VM02["VM02 sentrix-data · 10.20.10.20"]
        PG[(PostgreSQL 16<br/>database sentrix)]
        PUBLIC[public schema<br/>31 tables<br/>seed + runtime]
        CORPUS[corpus_pilot schema<br/>4 tables<br/>pilot corpus]
        PG --- PUBLIC
        PG --- CORPUS
    end

    subgraph VM03["VM03 sentrix-ai · 10.20.10.30"]
        AISVC[AI service :8000/:8001<br/>mock analysis]
        GNN[GNN inference :8002<br/>Devign C-code model]
        TRAIN[web_graph training<br/>HeteroConv-SAGE pilot]
    end

    subgraph VM04["VM04 sentrix-worker · 10.20.10.40 / 10.20.20.10"]
        WORKER[worker<br/>claim → heartbeat → run]
        EGRESS[egress allowlist<br/>API · LAB · DNS]
    end

    subgraph VM05["VM05 sentrix-lab · 10.20.20.20"]
        JUICE[Juice Shop :3000]
        WEBGOAT[WebGoat :8080]
    end

    BROWSER -->|HTTPS| NGINX
    API -->|SQL · TLS| PG
    API -->|mock adapter| AISVC
    API -.->|optional score service| GNN
    WORKER -->|authenticated API| API
    WORKER -->|allowlisted| JUICE
    WORKER -->|allowlisted| WEBGOAT
    EGRESS -.-> WORKER
    GNN --- TRAIN
```

## 2. Request, auth and scope

```mermaid
flowchart LR
    U[User] --> L[POST /api/v1/auth/login]
    L --> H[PBKDF2 verify]
    H --> T[HMAC bearer token]
    T --> R[Request + role]
    R --> M{Project member or admin?}
    M -->|no| X[403]
    M -->|yes| S{Target authorized and in scope?}
    S -->|no| Y[409 / blocked]
    S -->|yes| A[Action]
    A --> AUD[(append-only audit_event)]
    A --> RSP[Response]
```

Rules:

- project-scoped mutations require owner/member;
- admin-only routes cover automation policy and corpus pilot views;
- target authorization is recorded before a scan can be queued;
- audit/status history is append-only;
- corpus pilot routes are read-only and isolated.

## 3. Pentest workflow

```mermaid
flowchart LR
    P[Project] --> T[Authorized target]
    T --> SC[Scan job]
    SC --> Q[QUEUED]
    Q --> W[Worker claim]
    W --> RN[RUNNING]
    RN --> O[Observations]
    O --> F[Finding]
    F --> E[Evidence artifact]
    F --> AN[Analysis]
    F --> RM[Remediation]
    RM --> V[Verification]
    V -->|VERIFIED| RES[RESOLVED]
    V -->|NOT VERIFIED| REOPEN[REOPENED]
    F --> REP[Report snapshot]
```

Important: a remediation alone does not resolve a finding; verification does.

## 4. L3-C conditional automation

```mermaid
flowchart TB
    MAN[Signed HMAC manifest] --> CHK[Policy check<br/>expiry · scope · tier · budget]
    CHK --> CAT{Catalog action?}
    CAT -->|no| DENY[Denied]
    CAT -->|R0| AUTO[Read-only executor]
    CAT -->|R1| SAFE[Safe PoC executor<br/>non-destructive header check]
    CAT -->|R2| APPROVE[Human approval required]
    CAT -->|R3| DENY
    APPROVE --> REQ[Approval request]
    REQ -->|approved| R2EXEC[R2 executor]
    REQ -->|rejected| DENY
    AUTO --> SNAP[Before/after evidence hash]
    SAFE --> SNAP
    R2EXEC --> SNAP
    SNAP --> EX[(automation_execution)]
    EX --> AUD[(audit_event)]
```

- R0: root-only read-only HTTP, no redirects, host allowlist.
- R1: non-destructive security-header validation.
- R2: approval workflow exists; state-changing execution is not implemented.
- R3: prohibited.
- Authorization remains human-signed.

## 5. GNN tracks

There are **two separate tracks**. They are not the same model.

### 5.1 Devign C-code experiment (appendix)

```mermaid
flowchart LR
    DEV[Devign C/C++ dataset<br/>MIT mirror] --> AST[tree-sitter AST]
    AST --> CFG[approximate CFG]
    CFG --> GAT[GAT<br/>class weights<br/>threshold calibration]
    GAT --> MET[F1 0.6386 full split<br/>weak baseline]
    MET --> APP[Appendix only]
    APP -.->|never| WEBSCORE[Web/API score]
```

### 5.2 Web/API corpus pilot

```mermaid
flowchart LR
    LAB1[Juice Shop<br/>batch 1+2] --> H1[harnesses<br/>GET-only + BOLA]
    LAB2[WebGoat<br/>batch 3] --> H2[GET-only harness]
    H1 --> REV[human review<br/>14 positive / 32 negative<br/>18 pending]
    H2 --> REV2[human review<br/>24 positive / 16 negative]
    REV --> DS1[web corpus v2<br/>101 records]
    REV2 --> DS2[batch 3<br/>40 records]
    DS1 --> GRAPH[heterogeneous graph]
    DS2 --> GRAPH
    GRAPH --> HGT[HeteroConv-SAGE<br/>no Verification leakage]
    HGT --> EXT[external WebGoat test<br/>F1 0.7586]
    HGT --> CAL[calibration comparison<br/>isotonic pilot only]
    EXT --> PILOT[pilot result]
    CAL --> PILOT
```

Rules:

- training uses only HUMAN_VERIFIED / HUMAN_REJECTED labels; 18 records remain pending;
- `Verification` nodes/edges are excluded from training to prevent leakage;
- endpoint identity is an ablation that hurts; `no_endpoint` is better;
- Devign C-code scores are never applied to web findings;
- scores remain `pilot-uncalibrated`.

## 6. Corpus pilot import and UI

```mermaid
flowchart TB
    CORP[reviewed JSON corpus<br/>141 findings] --> MAP[mapping<br/>corpus-* / b2-* / b3-*]
    MAP --> IMP[import_web_corpus.py]
    IMP --> CP[(corpus_pilot schema<br/>project · target · finding · candidate)]
    CP --> RO[read-only API<br/>/api/v1/corpus/*]
    RO --> UI["/corpus.html<br/>pilot banner"]
    CP -.->|explicitly excluded| PUB[(public seed tables)]
    PUB --> TESTS[59 backend tests]
```

Isolation guarantees:

- public seed tables unchanged;
- corpus schema has `SELECT` only for `sentrix_app`;
- corpus API is admin-only and read-only;
- every response carries `pilot: true` and `pilot-uncalibrated`.

## 7. Milestones

```mermaid
flowchart LR
    M1[M1 schema + seed] --> M2[M2 auth/read API]
    M2 --> M3[M3 writes/audit]
    M3 --> M4[M4 adapter ports]
    M4 --> M5[M5 UI repository]
    M4 --> M6[M6 hardening/worker]
    M6 --> X1[X-01 approved local]
    X1 --> M5
    M5 --> M7[M7 experiments/ops]
    M7 --> L3[L3-C conditional automation]
    L3 --> GNN[web/API GNN pilot]
    GNN --> WG[WebGoat second lab]
    WG --> CORP[corpus project + pilot UI]
```

## 8. Component summary

| Component | Location | Responsibility |
|---|---|---|
| Nginx | VM01 | TLS termination, static UI, `/api/` proxy |
| FastAPI | VM01 `/backend/app` | auth, findings, scans, automation, corpus views |
| PostgreSQL | VM02 | 31 public tables + isolated `corpus_pilot` |
| Worker | VM04 | atomic job claim, heartbeat, scan execution |
| Juice Shop | VM05 :3000 | first lab target |
| WebGoat | VM05 :8080 | second lab target |
| AI service | VM03 | mock analyst support |
| GNN service | VM03 :8002 | Devign C-code inference only |
| Web GNN training | VM03 `~/sentrix-gnn` | HeteroConv-SAGE pilot |
| Corpus API | VM01 | read-only pilot data |

## 9. Honest boundaries

- The web GNN is a **pilot**, not production.\n- The current reviewed training set is 46 records (14 positive / 32 negative); 18 of 101 are still pending.
- External test is 40 records / 24 positives, dominated by header findings.
- Devign C-code model is weak and separate.
- Calibration is not production-validated.
- R2 state-changing execution is not implemented.
- Mobile and full IaC are explicitly out of scope.
