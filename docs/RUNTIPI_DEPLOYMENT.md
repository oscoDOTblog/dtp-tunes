# Deploying dtp-tunes behind Runtipi (custom domain)

This runbook covers running the **standalone** dtp-tunes Compose stack on the
same host as [Runtipi](https://runtipi.io), reusing Runtipi’s Traefik for
HTTPS on a public hostname you own.

dtp-tunes is **not** installed from the Runtipi App Store and does **not** use
the dashboard “Expose app” switch. Traefik discovers the gateway via Docker
labels in [`docker-compose.runtipi.yml`](../docker-compose.runtipi.yml).

## Architecture

```
Client  →  DNS (music.example.com)
        →  Router :80/:443
        →  Runtipi Traefik (Let's Encrypt / myresolver)
        →  dtp-tunes gateway (nginx)
        →  web (Next.js) + api (FastAPI)
```

Only the `gateway` container joins `runtipi_tipi_main_network`. `web`, `api`,
`worker`, and `mongodb` stay on the private Compose network.

## Prerequisites

1. **Runtipi is running** and already owns host ports **80** and **443**.
2. Docker network exists:

   ```bash
   docker network ls | grep runtipi_tipi_main_network
   ```

   Default name: `runtipi_tipi_main_network` (see Runtipi’s compose
   `networks.tipi_main_network.name`).

3. You own a domain and can create DNS records.
4. Router can forward **TCP 80 and 443** to the Runtipi host.
5. Your ISP is **not** on CGNAT (or you have a public IPv4 / alternative path).
   Check: compare the host’s WAN IP to what [ifconfig.me](https://ifconfig.me)
   reports. If they differ and you cannot port-forward, use Tailscale/WireGuard
   or a Cloudflare Tunnel instead of this direct-expose path.

## DNS

1. Pick a dedicated hostname that does **not** collide with another Traefik
   `Host(...)` rule (e.g. `music.example.com`, not the same FQDN as Navidrome
   or the Runtipi dashboard).
2. Create an **A** record pointing that hostname at your **public** IP.
3. If the zone is on Cloudflare, set the record to **DNS only** (grey cloud)
   for this hostname. Proxying long audio streams through Cloudflare often
   adds buffering/timeout pain; Traefik already terminates TLS.

Propagation can take a few minutes. Confirm:

```bash
dig +short music.example.com
```

## Router / firewall

1. Forward WAN **80 → host:80** and **443 → host:443** (Runtipi Traefik).
2. Do **not** forward 8080. The dtp-tunes gateway publishes
   `127.0.0.1:8080` only (loopback diagnostics).
3. Allow inbound 80/443 on the host firewall if you use one (ufw, firewalld).

Official Runtipi notes:
[Expose your apps](https://runtipi.io/docs/guides/expose-your-apps),
[Reverse proxy explained](https://runtipi.io/docs/learn/reverse-proxy).

## Configure secrets

```bash
cd /path/to/dtp-tunes
cp .env.example .env
```

Edit `.env` at minimum:

| Variable | Notes |
| --- | --- |
| `DTP_TUNES_DOMAIN` | Exact public hostname (no scheme), e.g. `music.example.com` |
| `ADMIN_PASSWORD` | Strong password; used once at first boot |
| `APP_ENCRYPTION_KEY` | 32+ random bytes (`python3 -c "import secrets; print(secrets.token_urlsafe(32))"`) |

The Runtipi overlay **overrides** `APP_PUBLIC_URL` and `CORS_ORIGINS` to
`https://${DTP_TUNES_DOMAIN}` so localhost defaults never leak into
production.

Mount music where your library lives (bind mounts in `docker-compose.yml`):

```yaml
# default: ./music → /music
# on this host you may prefer /mnt/yuna/... — adjust the compose volumes
# the same way runtipi-user-configs overrides Navidrome.
```

## Start

Validate the merged config first:

```bash
docker compose -f docker-compose.yml -f docker-compose.runtipi.yml config
```

Confirm:

- `gateway` lists both `default` and `runtipi` networks
- Traefik labels include `Host(\`your.domain\`)` and `certresolver=myresolver`
- No Runtipi `forwardauth` middleware is attached
- API has no host port bindings

Then:

```bash
docker compose -f docker-compose.yml -f docker-compose.runtipi.yml up -d --build
```

Wait for healthy services:

```bash
docker compose -f docker-compose.yml -f docker-compose.runtipi.yml ps
```

## Why not Runtipi “Expose app”?

| Concern | Behavior |
| --- | --- |
| Lifecycle | Runtipi does not start/stop/update this stack |
| Domain UI | Setting `Expose app` on some *other* app does nothing for dtp-tunes |
| Auth | We deliberately omit Runtipi forward-auth — Subsonic clients cannot complete browser cookie challenges |
| Network | Gateway joins `runtipi_tipi_main_network` via the overlay; Traefik picks it up from Docker labels |

Manage this stack only with the `docker compose ...` commands above.

## Clients

### Web UI

Open `https://<DTP_TUNES_DOMAIN>/` and sign in with the admin credentials from
`.env` (first boot creates that user).

Session cookies should be `Secure; HttpOnly; SameSite=Lax`.

### Subsonic / OpenSubsonic

Server URL / base URL:

```text
https://<DTP_TUNES_DOMAIN>
```

(no path suffix). Prefer API keys from **Settings → Subsonic API keys**. See
[`SUBSONIC_COMPATIBILITY.md`](SUBSONIC_COMPATIBILITY.md).

## Verification checklist

- [ ] `curl -I http://<DTP_TUNES_DOMAIN>/health` → redirect to HTTPS
- [ ] `curl -fsS https://<DTP_TUNES_DOMAIN>/health` → `ok` / healthy JSON
- [ ] Browser shows a valid Let’s Encrypt cert for the hostname
- [ ] Login works; Set-Cookie includes `Secure`
- [ ] Audio seek/range returns `206 Partial Content`
- [ ] `https://<DTP_TUNES_DOMAIN>/rest/ping.view?…` succeeds with auth
- [ ] `curl http://<LAN_IP>:8080` fails (not published on LAN)
- [ ] `curl http://127.0.0.1:8080/health` works on the host (loopback)

Certificate issuance can take up to ~2 minutes after Traefik first sees the
router. If ACME fails, Traefik logs under Runtipi’s Traefik container are the
first place to look.

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| Traefik 404 / no router | Wrong domain env, gateway not on Runtipi network | Re-check `DTP_TUNES_DOMAIN`, `docker network inspect runtipi_tipi_main_network` |
| ACME / TLS errors | Ports 80/443 not reachable from internet, DNS wrong, CGNAT | Fix DNS/forwarding; wait; check Traefik logs |
| Login cookie missing Secure | `X-Forwarded-Proto` dropped | Ensure Traefik → nginx preserves forwarded proto (see `gateway/nginx.conf`) |
| Stalled streams | Buffering proxy (Cloudflare orange cloud, extra nginx) | DNS-only Cloudflare; keep Traefik buffering defaults; gateway already disables buffering for `/rest` and `/api` media |
| Conflict with another app | Same `Host(...)` rule | Change `DTP_TUNES_DOMAIN` |
| `network runtipi_tipi_main_network declared as external, but could not be found` | Runtipi not started | Start Runtipi first |

## Rollback

Stop the stack (leaves Runtipi alone):

```bash
docker compose -f docker-compose.yml -f docker-compose.runtipi.yml down
```

To remove only Traefik registration without wiping volumes, `down` without
`-v`. Data lives in the `mongodb-data` volume plus `./cache` and your music
mount.

Local-only mode (no Traefik):

```bash
docker compose -f docker-compose.yml up -d --build
# → http://127.0.0.1:8080
```

## Fallbacks (if direct expose is impossible)

- **CGNAT / no port forward:** [Cloudflare Tunnel](https://runtipi.io/docs/guides/expose-apps-with-cloudflare-tunnels) or a VPN (Tailscale/WireGuard). Point the tunnel at `https://127.0.0.1:8080` or at Traefik if you keep labels but restrict WAN.
- **LAN only:** skip the Runtipi overlay; use Tailscale MagicDNS or Runtipi’s local domain patterns for other apps, and reach dtp-tunes via Tailscale IP + loopback publish, or add a Tailscale-only Traefik rule later.

## Security notes

- Prefer HTTPS everywhere outside a trusted LAN — especially with legacy
  Subsonic password/token auth (see [`SUBSONIC_COMPATIBILITY.md`](SUBSONIC_COMPATIBILITY.md)).
- Keep MongoDB unpublished (default).
- Do not commit real `.env` values.
- Prefer Subsonic API keys over legacy password mode for remote clients.
