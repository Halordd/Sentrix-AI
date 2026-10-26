# SENTRIX M1 — Per-VM SSH Key Register

**Status:** ALL FIVE VMS VERIFIED WITH DEDICATED KEYS; OLD SHARED KEY DELETED LOCALLY AND FROM VM BACKUPS  
**Private keys:** local only, never committed or printed  
**Purpose:** one dedicated SSH key per VM, least-privilege operational separation

## Old shared key retirement

The previously shared key `sentrix_m1_ed25519` (`sentrix-m1-local`) was removed from `authorized_keys` on VM01 and VM02 after the dedicated per-VM keys were verified. The old local private/public key pair and the VM `authorized_keys` backups containing the old key were then deleted. The old key is no longer valid for VM01/VM02 and no longer exists on this Windows host. VM03–VM05 contain only their dedicated key and no old shared key. All five dedicated keys were re-verified after cleanup.

| VM | Private key path (local) | Public key | Fingerprint | Installed |
|---|---|---|---|---|
| VM01 `sentrix-app` | `C:\Users\Halord\.ssh\sentrix_m1_vm01_ed25519` | `ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOMkXyPrX56wKJx/H30UYH3PYI8aZuQ15HzRZJtxFP/9 sentrix-m1-vm01` | `SHA256:e7wKkNK8eSO7VxjQ//vJmjZAxLzq5oz2nOG38NP8RQQ` | **INSTALLED + VERIFIED** |
| VM02 `sentrix-data` | `C:\Users\Halord\.ssh\sentrix_m1_vm02_ed25519` | `ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIADcjZ49aqOyynTtxEtm/MHaUMsfTjMNQIcfjZeERqFv sentrix-m1-vm02` | `SHA256:iYMMaqsfcYSlhsbxcye8s7F+8Mbt9NjKrjchlFwaAyY` | **INSTALLED + VERIFIED** |
| VM03 `sentrix-ai` | `C:\Users\Halord\.ssh\sentrix_m1_vm03_ed25519` | `ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIIFNf51KSGWycnFOhgsasMB7OrFN4KtFxWGmceaQ2UH+ sentrix-m1-vm03` | `SHA256:xG8YiaBtQpyiNK6is6j1FOds36FNeFK0YnMG91slp5s` | **INSTALLED + VERIFIED** |
| VM04 `sentrix-worker` | `C:\Users\Halord\.ssh\sentrix_m1_vm04_ed25519` | `ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIEJe7bwNppdRx06VHtCT3ufmBw1/+MX2ORAVb442ye8O sentrix-m1-vm04` | `SHA256:ddcO/lePPNXOL2DAIPVzT5/SgGCThTm8oEAPzoz0+88` | **INSTALLED + VERIFIED** |
| VM05 `sentrix-lab` | `C:\Users\Halord\.ssh\sentrix_m1_vm05_ed25519` | `ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIF7XmxcOBcU0spOTXBqoUUvBRb/L/GNgpThg9rt/m5hj sentrix-m1-vm05` | `SHA256:2/m+DEL6nH4NLIBnj/rImWYkPYGGoGh4nwM1CcOdGNY` | **INSTALLED + VERIFIED** |

## Installation rule

On each VM, append **only that VM's** public key to `~/.ssh/authorized_keys`; do not install all five keys on every VM. Use `>>`, not `>`, to preserve existing keys.

## Scope

These keys grant SSH login as `sentrixadmin`. They do **not** grant sudo, PostgreSQL admin, or database ownership. Privileged operations still require a separate authorized path.

## Verification

After installation, verify from Windows with the matching private key:

```text
ssh -i C:\Users\Halord\.ssh\sentrix_m1_vm01_ed25519 sentrixadmin@10.20.10.10 hostname
ssh -i C:\Users\Halord\.ssh\sentrix_m1_vm02_ed25519 sentrixadmin@10.20.10.20 hostname
ssh -i C:\Users\Halord\.ssh\sentrix_m1_vm03_ed25519 sentrixadmin@10.20.10.30 hostname
ssh -i C:\Users\Halord\.ssh\sentrix_m1_vm04_ed25519 sentrixadmin@10.20.10.40 hostname
ssh -i C:\Users\Halord\.ssh\sentrix_m1_vm05_ed25519 sentrixadmin@10.20.20.20 hostname
```

No key is claimed installed until the matching host returns the expected hostname.
