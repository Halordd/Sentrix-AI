# SENTRIX — WebGoat second-lab provisioning status

| Field | Value |
|---|---|
| Document ID | `SENTRIX-LAB-002` |
| Date | 2026-10-26 |
| Target | OWASP WebGoat on VM05 |
| Status | **Blocked: VM05 has no internet route/DNS** |

## What was attempted

```bash
docker pull webgoat/webgoat:latest
```

Result:

```text
failed to resolve reference "docker.io/webgoat/webgoat:latest"
dial tcp: lookup registry-1.docker.io on 127.0.0.53:53: server misbehaving
```

## Verified network state

VM05 (`10.20.20.20`):

```text
ip route:
10.20.20.0/24 dev ens34
```

No default route.

```text
nameserver 127.0.0.53
```

No usable upstream DNS.

VM05 has no `java`, so the JAR route is not available either.

VM04 has a default route but outbound HTTPS to Docker Hub times out; other VMs
have no Docker. Windows host has no Docker.

## What is needed

Choose one:

### A. Give VM05 outbound access

- NAT/default route through a gateway with internet;
- working DNS;
- then:

```bash
docker pull webgoat/webgoat:latest
docker run -d --name sentrix-webgoat -p 8080:8080 webgoat/webgoat:latest
```

### B. Import the image offline

On a machine with internet:

```bash
docker pull webgoat/webgoat:latest
docker save webgoat/webgoat:latest -o webgoat.tar
```

Copy to VM05, then:

```bash
scp webgoat.tar sentrixadmin@10.20.20.20:~/
ssh sentrixadmin@10.20.20.20
docker load -i ~/webgoat.tar
docker run -d --name sentrix-webgoat -p 8080:8080 webgoat/webgoat:latest
```

### C. JAR + JRE offline

Provide:

- WebGoat server JAR;
- Java 17+ runtime for Linux.

Then run the JAR under the `sentrixadmin` user.

## After WebGoat is up

Verify from VM01:

```bash
curl -sS -o /dev/null -w '%{http_code}\n' http://10.20.20.20:8080/WebGoat/
```

Expected: `200` or redirect to login (`302`).

Then batch 3 can be collected; every record must remain
`PENDING_HUMAN_REVIEW` until a human reviews it.

## Not done

- WebGoat did not start.
- No batch 3 candidates were generated.
- No external validation on a second lab.
- No score import.

Do not fabricate a second-lab corpus from Juice Shop and call it independent.
