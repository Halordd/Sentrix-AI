# SENTRIX — Transmittal: Decision Memo 001

| Field | Value |
|---|---|
| Transmittal ID | `SENTRIX-M1-DM-001-TR-001` |
| Attached memo | `SENTRIX-M1-DM-001` v0.2 |
| Subject | Request for decision: SENTRIX M1 target environment (`ASR-D-01`, `ASR-D-02`) |
| Status | **NOT SENT — DELIVERY NOT RECORDED** |
| Approval status | **NOT RECORDED** |
| Overall status | **NO-GO / HOLD — INSUFFICIENT INFORMATION** |
| Date prepared | 2026-10-19 (Asia/Saigon) |
| Sender | **NOT PROVIDED** |
| Delivery channel | **NOT PROVIDED** |

## 1. Recipients

| Role | Name | Email / channel | Status |
|---|---|---|---|
| Technical Supervisor | **NOT PROVIDED** | **NOT PROVIDED** | Not sent |
| Infrastructure Owner | **NOT PROVIDED** | **NOT PROVIDED** | Not sent |
| Database/Security Owner | **NOT PROVIDED** | **NOT PROVIDED** | Not sent |
| Independent Reviewer (CC, optional) | **NOT PROVIDED** | **NOT PROVIDED** | Not sent |

No recipient identity or address is invented. Delivery is **not claimed**.

## 2. Cover message (ready to send)

**Subject:** SENTRIX M1 — Decision requested: target environment for ASR-D-01 / ASR-D-02

Kính gửi anh/chị,

Tôi gửi kèm **Decision Memo 001 — SENTRIX M1 Target Environment** (bản nháp v0.2).

Memo đề nghị ba owner quyết định hai nội dung:

1. **ASR-D-01 — M1 target model và resource boundary:** chọn một trong các phương án:
   - **A — Isolated disposable PostgreSQL instance/cluster** (khuyến nghị chính, chưa được chọn);
   - **B — Separate cluster/instance on VM02** (phương án dự phòng, chưa được chọn);
   - **C — Disposable database inside the existing shared cluster** (không khuyến nghị cho M1 role/privilege tests);
   - **D — Defer** (M1 tiếp tục bị block).

2. **ASR-D-02 — Exact target environment and connection path:** cung cấp host/VM, PostgreSQL instance/cluster, port, database, account, connection path, backup/restore scope, snapshot/console, change ticket và environment owner — hoặc xác nhận rõ các trường này vẫn `UNRESOLVED`.

**Đề nghị phản hồi:**

- Chọn A/B/C/D cho `ASR-D-01`, kèm lý do ngắn.
- Điền hoặc xác nhận các trường `ASR-D-02` (không gửi mật khẩu, private key, token hoặc connection string chứa secret).
- Ghi rõ người ký, vai trò, thời điểm (UTC) và approval reference.
- Nếu chưa thể quyết định, ghi rõ `UNRESOLVED — NOT APPROVED` và lý do; M1 sẽ tiếp tục `NO-GO / HOLD`.

**Lưu ý:** Memo này là **decision request**, không phải authorization. Không có thay đổi hạ tầng/database nào được thực hiện. Việc chọn A hoặc B không tự động cho phép thay đổi VM, PostgreSQL, HBA, TLS, firewall hay SSH; các thay đổi đó vẫn cần change record và approval riêng.

Trân trọng,
**NOT PROVIDED**

## 3. Decision requested — response form

| Field | Response |
|---|---|
| `ASR-D-01` selected option | ☐ A ☐ B ☐ C ☐ D ☐ `UNRESOLVED` |
| Rationale | ______________________________________________ |
| `ASR-D-02` target record supplied? | ☐ Yes ☐ No — still `UNRESOLVED` |
| Change ticket | ______________________________________________ |
| Decision owner name/role | ______________________________________________ |
| Decision timestamp (UTC) | ______________________________________________ |
| Approval reference/signature | ______________________________________________ |
| Conditions/limitations | ______________________________________________ |

## 4. Attachments

| Attachment | Status |
|---|---|
| `docs/phase2/09-decision-memo-001-m1-target-environment.md` | Present in repository |
| `SENTRIX-M1-ASR-001` v1.3 authorization package | Supplied in review conversation; not yet committed as a separate repository file |
| Supporting Phase 2 documents (`06`, `07`, `schema.sql`, `seed-manifest.json`) | Present in repository; design artifacts only |

## 5. Delivery checklist

- [ ] Recipient names/addresses confirmed by sender.
- [ ] Memo attached or linked.
- [ ] Subject and response deadline confirmed.
- [ ] No secrets or credentials included.
- [ ] Delivery channel and timestamp recorded.
- [ ] Responses stored in the same evidence/decision register.
- [ ] `ASR-D-01`/`ASR-D-02` outcomes updated only from written responses.
- [ ] No gate marked PASS from this transmittal.

## 6. Final status

**NOT SENT — DELIVERY NOT RECORDED.**
**No approval is implied.**
**M1 remains `NO-GO / HOLD — INSUFFICIENT INFORMATION`.**

No infrastructure, database, network, firewall, SSH, PostgreSQL, role, grant or data change was performed. No command was executed and no evidence was collected.
