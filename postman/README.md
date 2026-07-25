# SupplyWatch Postman / Newman Test Suite

This directory contains a Postman collection that exercises the live SupplyWatch
FastAPI service end-to-end: health check, API key issuance, auth enforcement,
materials listing, per-material signal/history lookups, and the alert
subscription flow.

## Files

- `supplywatch.postman_collection.json` — Postman Collection v2.1. Requests run
  in order and chain together via the `apiKey` collection variable (set by the
  "Create API Key" request and reused as the `X-API-Key` header on every
  subsequent authenticated request).
- `supplywatch.postman_environment.json` — Postman Environment v2.1 defining
  `baseUrl`, defaulted to `http://127.0.0.1:8002` for local runs.

## What it covers

1. `GET /health` — service is up and reports `status: ok`.
2. `POST /auth/keys` — issues a fresh API key (`sw_...`) and stores it for
   later requests.
3. `GET /materials` with no `X-API-Key` header — confirms the endpoint is
   protected (expects `401`).
4. `GET /materials` with the API key — expects all 8 seeded materials
   (including "Gallium").
5. `GET /materials/1/signal` — on a fresh database with no scoring job run
   yet, this correctly returns `404` ("signal not found"). This is expected,
   current behavior, not an error condition.
6. `GET /materials/1/history` — expects an empty array on a fresh database.
7. `POST /alerts/subscribe` — creates an alert subscription and returns its
   new `id`.
8. `GET /alerts/history` — expects an array (empty until an alert actually
   fires).

## Running locally

1. Start the SupplyWatch API on `http://127.0.0.1:8002` (see the app's own
   setup instructions — briefly: create a venv, `pip install -r
   requirements.txt`, set `DATABASE_URL` to point at a running Postgres 16
   instance, then `uvicorn main:app --host 127.0.0.1 --port 8002`).
2. From the repo root, run:

   ```bash
   npx newman run postman/supplywatch.postman_collection.json \
     -e postman/supplywatch.postman_environment.json
   ```

   (No global Newman install is required — `npx` fetches it on demand. `npm
   install -g newman` also works if you prefer a persistent install.)

3. Newman prints a pass/fail table per request/assertion and exits non-zero
   if anything fails.

## Running in CI

`.github/workflows/api-tests.yml` runs this same collection automatically on
every push and pull request:

- Spins up a `postgres:16` service container inside the Actions job.
- Installs `supplywatch/requirements.txt` under Python 3.11.
- Starts the API with `uvicorn` on `127.0.0.1:8000` and polls `/health` until
  it responds.
- Runs `npx newman run postman/supplywatch.postman_collection.json -e
  postman/supplywatch.postman_environment.json --env-var
  baseUrl=http://127.0.0.1:8000`, overriding the environment's default
  `baseUrl` (8002, for local runs) to match the port used in the workflow
  (8000).
- The job fails if Newman reports any failed assertion (Newman's process
  exit code is non-zero on failure, which fails the step automatically).
