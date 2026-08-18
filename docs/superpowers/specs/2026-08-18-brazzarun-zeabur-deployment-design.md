# Brazzarun Zeabur Deployment Design

## Goal

Deploy `Celmaro/Brazzarun` to Zeabur as an isolated multi-service project that preserves the repository's expected runtime topology:

- public frontend
- public backend API
- dedicated worker planes for `trading`, `news`, and `discovery`
- managed PostgreSQL
- managed Redis

The deployment must avoid interference with the existing `mfpolybot` Zeabur service already running in another project.

## Context

Brazzarun is the Homerun prediction-market platform. The repository is not a single-container app. The checked-in deployment model uses:

- `backend` for FastAPI
- `frontend` for the React/nginx bundle
- `worker-trading`
- `worker-news`
- `worker-discovery`
- `postgres`
- `redis`

Important repo constraints discovered during review:

- `backend/Dockerfile` assumes the runtime source lives at `/app/backend`.
- `frontend/nginx.conf` proxies `/api` and `/ws` to an internal host named `backend:8000`.
- `docker-compose.yml` explicitly warns that the worker plane split is load-bearing and should not be collapsed.
- `backend/main.py` exposes `GET /health/live`, which can serve as the backend health check target.
- Database migrations are handled by backend startup logic through the application codepath, so a separate mandatory migration service is not required for the first Zeabur cut.

## Recommended Approach

Create a brand-new Zeabur project dedicated to Brazzarun and deploy all application services from the GitHub repository `Celmaro/Brazzarun`.

This is preferred over reusing the existing Zeabur project because:

- it avoids variable leakage and routing conflicts with `mfpolybot`
- it keeps service discovery simple inside one app-specific network
- it matches the repo's existing internal naming assumptions
- it makes rollback and teardown safer

## Service Topology

### Public Services

#### Frontend

- Source: `frontend/Dockerfile`
- Port: `3000`
- Visibility: public HTTP
- Role: serves static assets and reverse-proxies `/api` and `/ws` to `backend`

#### Backend

- Source: `backend/Dockerfile`
- Default command: `uvicorn main:app --host 0.0.0.0 --port 8000`
- Port: `8000`
- Visibility: public HTTP
- Health endpoint: `/health/live`
- Role: FastAPI server, API surface, websocket endpoints, startup initialization, DB upgrade path

### Private Worker Services

Each worker service uses the same image build as the backend, but overrides the command.

#### Worker Trading

- Source: `backend/Dockerfile`
- Command: `python -m workers.host trading`
- Visibility: private
- Role: trading-plane processing

#### Worker News

- Source: `backend/Dockerfile`
- Command: `python -m workers.host news`
- Visibility: private
- Role: news-plane processing

#### Worker Discovery

- Source: `backend/Dockerfile`
- Command: `python -m workers.host discovery`
- Visibility: private
- Role: discovery-plane processing

### Managed Infrastructure

#### PostgreSQL

- Zeabur managed service
- Version target: PostgreSQL 16 if configurable
- Must provide a connection string to all app services through `DATABASE_URL`

#### Redis

- Zeabur managed service
- Must provide a connection string to all app services through `REDIS_URL`

## Environment Design

### Required Variables

- `APP_SECRETS_KEY`
- `DATABASE_URL`
- `REDIS_URL`

`APP_SECRETS_KEY` must be generated before deployment. The repository documents this format:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

### Shared Optional Variables

- `LOG_LEVEL`
- `HF_TOKEN`
- `POLYGON_RPC_URL`
- `POLYGON_WS_URL`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

### Trading Optional Variables

These may be omitted for shadow or backtest-only operation:

- `POLYMARKET_PRIVATE_KEY`
- `POLYMARKET_API_KEY`
- `POLYMARKET_API_SECRET`
- `POLYMARKET_API_PASSPHRASE`
- `POLYMARKET_FUNDER`
- `POLYMARKET_BUILDER_CODE`

### Worker-Specific Variables

- `HOMERUN_PROCESS_ROLE=worker`
- `HOMERUN_WORKER_PLANE=trading|news|discovery`

The backend should keep its default server role and should not set a worker plane.

## Deployment Source Strategy

All services should build directly from `https://github.com/Celmaro/Brazzarun`.

Recommended source mapping:

- backend service -> repo root, Dockerfile path `/backend/Dockerfile`
- worker services -> repo root, Dockerfile path `/backend/Dockerfile`
- frontend service -> repo root, Dockerfile path `/frontend/Dockerfile`

This keeps the deployment aligned with the repository's existing Dockerfiles and avoids introducing a second deployment format as the source of truth.

The local `zeabur.json` draft is useful as a reference document but should not be treated as authoritative unless it is committed to the target repository and confirmed to match Zeabur's current schema.

## Networking Assumptions

The frontend nginx config expects the backend to be reachable at the hostname `backend` on port `8000`.

Therefore:

- the backend Zeabur service should be named `backend`
- the frontend service should run in the same Zeabur project/environment so that internal service discovery can resolve `backend`

If Zeabur's internal DNS naming differs from the service name, the frontend will require an nginx configuration override. That is out of scope for the first attempt and should only be added if runtime verification proves it necessary.

## Rollout Sequence

1. Create a new Zeabur project for Brazzarun.
2. Provision managed PostgreSQL.
3. Provision managed Redis.
4. Create the `backend` service and deploy from GitHub.
5. Create the `frontend` service and deploy from GitHub.
6. Create the three worker services and deploy them from GitHub.
7. Configure backend public HTTP port `8000`.
8. Configure frontend public HTTP port `3000`.
9. Apply required and optional environment variables.
10. Verify backend health at `/health/live`.
11. Verify the frontend loads successfully.
12. Inspect runtime logs for backend and all worker planes.

## Verification Plan

### Minimum Success Criteria

- Backend deploys and responds on `/health/live`
- Frontend serves the app shell successfully
- Workers start without crash loops
- Backend can reach PostgreSQL and Redis
- Frontend can proxy `/api` requests to backend

### Early Failure Checks

- Build failure in backend image due to large Python dependency resolution
- Frontend proxy failure if `backend` hostname is not resolvable in Zeabur
- Missing `APP_SECRETS_KEY`
- Incorrect `DATABASE_URL` or `REDIS_URL`
- Worker startup failures caused by missing shared env vars

## Risks And Mitigations

### Risk: Internal DNS mismatch

The frontend nginx config hardcodes `backend:8000`.

Mitigation:

- name the API service exactly `backend`
- only patch nginx if runtime verification proves Zeabur uses a different internal hostname

### Risk: Slow or heavy backend builds

The backend image installs CPU-only torch and other substantial dependencies.

Mitigation:

- deploy backend first
- inspect build logs before launching worker replicas

### Risk: Hidden runtime assumptions

The repository is optimized for Docker Compose, so some expectations may surface only after first boot.

Mitigation:

- keep the first rollout minimal
- use repo Dockerfiles directly rather than inventing new container logic
- validate logs service by service

## Out Of Scope

- custom domain setup
- production hardening beyond baseline deployment
- scaling policies
- persistent volume tuning for cache/runtime directories
- repo code changes unless deployment verification proves they are required

## Implementation Notes

The execution phase should prefer Zeabur MCP actions over manual guesswork:

- inspect or create the destination project
- create services explicitly
- map repo source by Dockerfile
- set ports and environment variables
- fetch build logs and runtime logs after deployment

If deployment fails because Zeabur requires a different internal host mapping or source specification, the implementation plan should include the smallest repo change necessary to adapt the service.
