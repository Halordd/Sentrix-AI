# SENTRIX lab (VM05)

Isolated Juice Shop target. This VM has no NAT/default route and only serves the
LAB network.

## Runtime

Current container:

```text
name:    sentrix-juice-shop
image:   bkimminich/juice-shop
network: host  (listens on *:3000)
restart: unless-stopped
```

UFW allows port 3000 only from:

```text
10.20.20.10   # VM04 worker LAB
10.20.20.1    # optional administrative host
```

## Reproduce

```bash
docker rm -f sentrix-juice-shop
docker run -d --name sentrix-juice-shop \
  --restart unless-stopped \
  --network host \
  bkimminich/juice-shop
```

`docker-compose.yml` is provided for a compose-capable host.

## Verify

From VM04:

```bash
curl -sS -o /dev/null -w "%{http_code}\n" http://10.20.20.20:3000/
```

Expected `200`.

From Windows:

```text
http://10.20.20.20:3000/
```

Expected `200` while UFW allows `.1`.
