# Brazzarun Zeabur Deployment — Status

> Last updated: 2026-08-19 02:50 UTC

## Project
- **Project ID:** `6a8514ffbdeaa87e2c53d88f`
- **Project Name:** brazzarun
- **Region:** Tencent Ashburn 2C 2GB (`server-6a7492ae1868deeacea20fab`)
- **Environment ID:** `6a8514fff8fa433a2b5e1946` (production)

## Services

| Service | ID | Port | Image |
|---|---|---|---|
| backend | `6a851513bdeaa87e2c53d896` | 8000 | `ghcr.io/braedonsaunders/homerun-backend:latest` |
| frontend | `6a851514bdeaa87e2c53d899` | 3000 | `ghcr.io/braedonsaunders/homerun-frontend:latest` |
| worker-trading | `6a851515bdeaa87e2c53d89c` | — | `ghcr.io/braedonsaunders/homerun-backend:latest` |
| worker-news | `6a851515bdeaa87e2c53d89f` | — | `ghcr.io/braedonsaunders/homerun-backend:latest` |
| worker-discovery | `6a851516bdeaa87e2c53d8a2` | — | `ghcr.io/braedonsaunders/homerun-backend:latest` |
| postgresql | `6a851645bdeaa87e2c53d964` | — | Managed PostgreSQL (Zeabur) |
| redis | `6a851645bdeaa87e2c53d971` | — | Managed Redis (Zeabur) |

**⚠️ API Status Note:** Zeabur's service-level API has been returning `INTERNAL_SERVER_ERROR` on all service queries since ~02:36 UTC. This is a platform-level infrastructure issue. Service state cannot be queried via API — manual dashboard verification required.

**Last known states** (before API overload): backend RUNNING, frontend RUNNING, worker-trading RUNNING, postgresql RUNNING, redis RUNNING, worker-news STARTING, worker-discovery STARTING

## Environment Variables Set

All 5 app services have these env vars set:

| Key | Value |
|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://root:ya4m1Xx3JS6e950W7Zc2o8vnHGDFMAQu@postgresql:5432/zeabur` |
| `REDIS_URL` | `redis://:o4FyiZp625Ox1YzlDc3rV9T8a0Gkdvb7@redis:6379/0` |
| `APP_SECRETS_KEY` | `pvFliL6fBr_7n-nxTpzlXh-dwhRtWsc9LNi3CGmcLY5YUlCgu8n8eUHYjcr3G_XY` |
| `LOG_LEVEL` | `INFO` |
| `POLYGON_RPC_URL` | `https://rpc-mainnet.matic.quiknode.pro` |
| `POLYGON_WS_URL` | `wss://polygon-bor-rpc.publicnode.com` |

Workers additionally have:

| Key | Value |
|---|---|
| `HOMERUN_PROCESS_ROLE` | `worker` |
| `HOMERUN_WORKER_PLANE` | `trading` / `news` / `discovery` |

## Public Ports

- Backend: port `8000` (HTTP) — set via `updateServicePorts`
- Frontend: port `3000` (HTTP) — set via `updateServicePorts`

## Deployment History

- **02:31–02:32 UTC**: Initial GitHub source builds — ALL FAILED (Dockerfile path issue: `backend/Dockerfile` copies `requirements-trading.txt` from repo root, but Zeabur build context is `/backend/`)
- **02:33 UTC**: Switched to GHCR prebuilt images, deployed all 5 services
- **02:36 UTC**: Zeabur service API started returning `INTERNAL_SERVER_ERROR`
- **02:48 UTC**: Re-deployed all 5 services with updated env vars (all returned `deploymentID: null` — spec updated, no new build triggered)
- **02:50 UTC**: Service API still returning errors

## Source Build Fix (Optional)

The source build issue can be resolved by adding a root-level `Dockerfile`:

```dockerfile
# /Dockerfile (at repo root — NOT /backend/Dockerfile)
FROM ghcr.io/braedonsaunders/homerun-backend:latest
```

Then in Zeabur, specify `dockerfile.path: /Dockerfile` for source builds.

## Verification Steps (Dashboard)

1. Open https://dash.zeabur.com → select project `brazzarun`
2. Verify all 7 services show `RUNNING` (ignore API errors — services may still be healthy)
3. Click on `backend` → Domains → assign a domain (e.g. `brazzarun-api.zeabur.app`)
4. Click on `frontend` → Domains → assign a domain (e.g. `brazzarun.zeabur.app`)
5. Visit `https://<backend-domain>/health/live` — expect HTTP 200
6. Visit `https://<frontend-domain>` — expect React app

## Optional: Add Polymarket Credentials

After deployment is verified, add these via the Zeabur dashboard (Environment Variables for each worker service):

| Key | Notes |
|---|---|
| `POLYMARKET_PRIVATE_KEY` | Required for live trading |
| `POLYMARKET_API_KEY` | Polymarket API key |
| `POLYMARKET_API_SECRET` | Polymarket API secret |
| `POLYMARKET_API_PASSPHRASE` | Polymarket passphrase |
| `POLYMARKET_FUNDER` | Optional funder address |
| `POLYMARKET_BUILDER_CODE` | Optional builder code |

Leave blank for shadow/backtest-only operation.
