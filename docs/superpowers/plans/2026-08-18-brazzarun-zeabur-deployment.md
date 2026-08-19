# Brazzarun Zeabur Deployment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deploy `Celmaro/Brazzarun` to a new Zeabur project with managed PostgreSQL, managed Redis, a public backend, a public frontend, and three private worker services.

**Architecture:** Multi-service deployment from GitHub source on a single Zeabur project. All services share the same managed Postgres and Redis. The frontend proxies `/api` and `/ws` to the backend service internally.

**Tech Stack:** Zeabur, Docker (GitHub source builds), managed PostgreSQL, managed Redis, Celmaro/Brazzarun repo.

---

## Before Starting

Confirm the following are available in the current session:
- Zeabur MCP tools are connected (`get-me` returned a valid user)
- GitHub repo ID for `Celmaro/Brazzarun` is `1338274706`
- GitHub account is linked to the Zeabur account

If any of the above are missing, stop and re-run the discovery steps before proceeding.

---

## Step 1 — Create New Zeabur Project

**Goal:** Create a dedicated Zeabur project named `brazzarun`.

- [ ] **Step 1.1: List available regions**

Call `listRegions` to get a valid region code for the new project.

Expected output: a list of region objects with `code` fields.

- [ ] **Step 1.2: Create the project**

Call `createProject` with:
- `name`: `brazzarun`
- `region`: a region code from Step 1.1

Expected output: a project object with `_id` (save this as `PROJECT_ID`).

**Verify:** note the `PROJECT_ID` and the `environmentId` inside the production environment (save as `ENVIRONMENT_ID`).

---

## Step 2 — Provision Managed PostgreSQL

**Goal:** Add a managed PostgreSQL database to the new project.

- [ ] **Step 2.1: Check if `createProject` returned a managed database already**

If the project creation step returned a `databases.postgres` field with an ID, skip to Step 3.

If not, check Zeabur's managed database provisioning API via MCP (if available) or note that PostgreSQL must be provisioned manually through the Zeabur dashboard after project creation.

**Fallback:** If no MCP tool for database creation exists, document the required manual steps:
1. Open Zeabur dashboard → new project → Add Database → PostgreSQL
2. Note the auto-generated connection string

**Save:** `DATABASE_URL` from the managed instance (format: `postgresql+asyncpg://user:pass@host:5432/dbname`).

---

## Step 3 — Provision Managed Redis

**Goal:** Add a managed Redis instance to the new project.

- [ ] **Step 3.1: Check if project creation returned a managed Redis already**

If the project creation step returned a `addons.redis` field with a URL, skip to Step 4.

If not, check for a Redis creation MCP tool or document manual steps:
1. Open Zeabur dashboard → new project → Add Addon → Redis
2. Note the auto-generated connection URL

**Save:** `REDIS_URL` from the managed instance (format: `redis://host:6379/0`).

---

## Step 4 — Generate APP_SECRETS_KEY

**Goal:** Produce a valid `APP_SECRETS_KEY` for environment configuration.

- [ ] **Step 4.1: Generate the key**

Run in terminal:
```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

**Save:** the output as `APP_SECRETS_KEY`. This will be set as an environment variable in Step 6.

---

## Step 5 — Create Backend Service

**Goal:** Create and deploy the FastAPI backend service from GitHub source.

- [ ] **Step 5.1: Create the service**

Call `createService` with:
- `name`: `backend`
- `projectId`: `PROJECT_ID` from Step 1.2

Expected output: a service object with `_id` (save as `BACKEND_SERVICE_ID`).

- [ ] **Step 5.2: Deploy from GitHub source**

Call `deployFromSpecification` with:
- `service_id`: `BACKEND_SERVICE_ID`
- `source.type`: `BUILD_FROM_SOURCE`
- `source.build_from_source.source.type`: `GITHUB`
- `source.build_from_source.source.github.repo_id`: `1338274706`
- `source.build_from_source.dockerfile.path`: `/backend/Dockerfile`
- `env`: an array containing all shared environment variables (see list below)

**Environment variables for backend:**
```json
[
  { "key": "DATABASE_URL", "value": "<DATABASE_URL>" },
  { "key": "REDIS_URL", "value": "<REDIS_URL>" },
  { "key": "APP_SECRETS_KEY", "value": "<APP_SECRETS_KEY>" },
  { "key": "LOG_LEVEL", "value": "INFO" },
  { "key": "POLYGON_RPC_URL", "value": "https://rpc-mainnet.matic.quiknode.pro" },
  { "key": "POLYGON_WS_URL", "value": "wss://polygon-bor-rpc.publicnode.com" }
]
```

- [ ] **Step 5.3: Set public port**

Call `updateServicePorts` with:
- `serviceId`: `BACKEND_SERVICE_ID`
- `environmentId`: `ENVIRONMENT_ID`
- `ports`: `[{"id": "web", "port": 8000, "type": "HTTP"}]`

- [ ] **Step 5.4: Monitor build progress**

Call `getBuildLogs` with `serviceId: BACKEND_SERVICE_ID` to watch the image build.
Expected: a long build log showing Python dependencies installing, torch (CPU-only), uvicorn startup.

If the build fails, inspect the error, fix any Dockerfile path issues, and redeploy.

- [ ] **Step 5.5: Verify health endpoint**

Once deployed, call `getService` with `serviceId: BACKEND_SERVICE_ID` to get the service URL, then make a GET request to:
```
<BACKEND_URL>/health/live
```
Expected: HTTP 200 response.

---

## Step 6 — Create Frontend Service

**Goal:** Create and deploy the React/nginx frontend service from GitHub source.

- [ ] **Step 6.1: Create the service**

Call `createService` with:
- `name`: `frontend`
- `projectId`: `PROJECT_ID` from Step 1.2

Expected output: a service object with `_id` (save as `FRONTEND_SERVICE_ID`).

- [ ] **Step 6.2: Deploy from GitHub source**

Call `deployFromSpecification` with:
- `service_id`: `FRONTEND_SERVICE_ID`
- `source.type`: `BUILD_FROM_SOURCE`
- `source.build_from_source.source.type`: `GITHUB`
- `source.build_from_source.source.github.repo_id`: `1338274706`
- `source.build_from_source.dockerfile.path`: `/frontend/Dockerfile`
- `env`: empty array (frontend has no required env vars at build time)

- [ ] **Step 6.3: Set public port**

Call `updateServicePorts` with:
- `serviceId`: `FRONTEND_SERVICE_ID`
- `environmentId`: `ENVIRONMENT_ID`
- `ports`: `[{"id": "web", "port": 3000, "type": "HTTP"}]`

- [ ] **Step 6.4: Monitor build progress**

Call `getBuildLogs` with `serviceId: FRONTEND_SERVICE_ID`.
Expected: Node.js build, Vite bundle, nginx configuration.

- [ ] **Step 6.5: Verify frontend loads**

Call `getService` with `serviceId: FRONTEND_SERVICE_ID` to get the URL, then open it in a browser or fetch the HTML.
Expected: React app shell served from nginx.

---

## Step 7 — Create Three Worker Services

**Goal:** Create `worker-trading`, `worker-news`, and `worker-discovery` services. All use the same backend image with different command overrides.

**Each worker follows the same pattern (repeat for each):**

### 7a. Worker Trading

- [ ] **Step 7a.1: Create service**

Call `createService` with `name: worker-trading`, `projectId: PROJECT_ID`.
Save `_id` as `WORKER_TRADING_SERVICE_ID`.

- [ ] **Step 7a.2: Deploy**

Call `deployFromSpecification` with:
- `service_id`: `WORKER_TRADING_SERVICE_ID`
- `source.type`: `BUILD_FROM_SOURCE`
- `source.build_from_source.source.type`: `GITHUB`
- `source.build_from_source.source.github.repo_id`: `1338274706`
- `source.build_from_source.dockerfile.path`: `/backend/Dockerfile`
- `env`: shared env vars plus:
  ```json
  { "key": "HOMERUN_PROCESS_ROLE", "value": "worker" },
  { "key": "HOMERUN_WORKER_PLANE", "value": "trading" }
  ```

- [ ] **Step 7a.3: Check startup logs**

Call `getRuntimeLogs` with `serviceId: WORKER_TRADING_SERVICE_ID`.
Expected: worker host starting, trading plane initializing, no crash loop.

### 7b. Worker News

- [ ] **Step 7b.1: Create service**

Call `createService` with `name: worker-news`, `projectId: PROJECT_ID`.
Save `_id` as `WORKER_NEWS_SERVICE_ID`.

- [ ] **Step 7b.2: Deploy**

Same as Step 7a.2 but with:
- `service_id`: `WORKER_NEWS_SERVICE_ID`
- `HOMERUN_WORKER_PLANE`: `news`

- [ ] **Step 7b.3: Check startup logs**

Call `getRuntimeLogs` with `serviceId: WORKER_NEWS_SERVICE_ID`.

### 7c. Worker Discovery

- [ ] **Step 7c.1: Create service**

Call `createService` with `name: worker-discovery`, `projectId: PROJECT_ID`.
Save `_id` as `WORKER_DISCOVERY_SERVICE_ID`.

- [ ] **Step 7c.2: Deploy**

Same as Step 7a.2 but with:
- `service_id`: `WORKER_DISCOVERY_SERVICE_ID`
- `HOMERUN_WORKER_PLANE`: `discovery`

- [ ] **Step 7c.3: Check startup logs**

Call `getRuntimeLogs` with `serviceId: WORKER_DISCOVERY_SERVICE_ID`.

---

## Step 8 — Final Verification

- [ ] **Step 8.1: Verify all services are running**

Call `listServices` with `projectId: PROJECT_ID`.
Expected: 6 services all with status `RUNNING`.

- [ ] **Step 8.2: Verify backend health**

Fetch `https://<BACKEND_URL>/health/live`.
Expected: 200 OK.

- [ ] **Step 8.3: Verify frontend**

Fetch `https://<FRONTEND_URL>`.
Expected: HTML page with React app.

- [ ] **Step 8.4: Verify all worker logs are clean**

Call `getRuntimeLogs` on each worker service.
Expected: no ERROR-level entries indicating crashes.

- [ ] **Step 8.5: Inspect backend runtime logs for startup signal**

Call `getRuntimeLogs` with `serviceId: BACKEND_SERVICE_ID`.
Expected: alembic migrations run, Redis connected, PostgreSQL connected, uvicorn running on port 8000.

---

## Step 9 — Optional: Add Polymarket Credentials

Once the base stack is verified, optional credentials can be added to the backend service:

- [ ] **Step 9.1: Add trading secrets via environment variables**

Call `createEnvironmentVariable` (or `updateEnvironmentVariable` if already set) on the backend service with:
- `POLYMARKET_PRIVATE_KEY`
- `POLYMARKET_API_KEY`
- `POLYMARKET_API_SECRET`
- `POLYMARKET_API_PASSPHRASE`
- `POLYMARKET_FUNDER`
- `POLYMARKET_BUILDER_CODE`

**Note:** These can be left blank for shadow/backtest-only operation.

---

## File Map

| File | Role |
|---|---|
| `backend/Dockerfile` | Used by backend + all 3 worker services |
| `frontend/Dockerfile` | Used by frontend service |
| `frontend/nginx.conf` | Reverse-proxies `/api` and `/ws` to `backend:8000` |
| `backend/main.py` | Exposes `/health/live` endpoint |
| `backend/workers/host.py` | Worker host entrypoint with plane routing |

## Service IDs Reference

| Service | Variable Name |
|---|---|
| New project | `PROJECT_ID` |
| Production environment | `ENVIRONMENT_ID` |
| Backend | `BACKEND_SERVICE_ID` |
| Frontend | `FRONTEND_SERVICE_ID` |
| Worker Trading | `WORKER_TRADING_SERVICE_ID` |
| Worker News | `WORKER_NEWS_SERVICE_ID` |
| Worker Discovery | `WORKER_DISCOVERY_SERVICE_ID` |

## Potential Failure Modes

| Failure | Detection | Fix |
|---|---|---|
| Backend build fails on torch install | `getBuildLogs` shows pip error | Wait — torch CPU-only install can take 5-10 min |
| Frontend nginx can't reach backend | Runtime logs show `backend` hostname unresolved | Rename backend service to `backend` or add custom nginx override |
| Worker crash loop | Runtime logs show repeating ERROR entries | Check `DATABASE_URL` and `REDIS_URL` are reachable from worker |
| Migrations fail | Backend logs show alembic error | Verify `DATABASE_URL` format and Postgres version compatibility |
| APP_SECRETS_KEY missing | API returns 500 on startup | Set `APP_SECRETS_KEY` env var on backend service |
