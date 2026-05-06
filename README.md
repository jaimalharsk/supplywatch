# SupplyWatch

SupplyWatch is a B2B SaaS MVP for small manufacturing and electronics companies that need an API-first way to monitor potential critical-mineral supply disruptions and trigger automated alerts before sourcing risk impacts production.

## Local setup
1. Ensure Python 3.11+ and PostgreSQL are available.
2. Copy envs: `cp .env.example .env`
3. Install deps: `pip install -r requirements.txt`
4. Run API: `uvicorn main:app --reload`

## .env.example
- `DATABASE_URL`: async PostgreSQL DSN.
- `RESEND_API_KEY`: API key used by alert email dispatcher.
- `RESEND_FROM_EMAIL`: sender used in outbound alerts.
- `ENABLE_SCHEDULER`: enables 6-hour scoring + Monday digest jobs.
- `DEFAULT_RATE_LIMIT_FREE`: daily request cap for free tier keys.

## API reference
Health:
```bash
curl http://localhost:8000/health
```

Create API key:
```bash
curl -X POST http://localhost:8000/auth/keys -H 'Content-Type: application/json' -d '{"company_name":"Acme","tier":"free"}'
```

List materials:
```bash
curl http://localhost:8000/materials -H 'X-API-Key: YOUR_KEY'
```

Material signal:
```bash
curl http://localhost:8000/materials/1/signal -H 'X-API-Key: YOUR_KEY'
```

Material history:
```bash
curl http://localhost:8000/materials/1/history -H 'X-API-Key: YOUR_KEY'
```

Subscribe alert:
```bash
curl -X POST http://localhost:8000/alerts/subscribe -H 'X-API-Key: YOUR_KEY' -H 'Content-Type: application/json' -d '{"material_id":1,"threshold":65,"email":"ops@acme.com"}'
```

Alert history:
```bash
curl http://localhost:8000/alerts/history -H 'X-API-Key: YOUR_KEY'
```

Trigger digest:
```bash
curl -X POST http://localhost:8000/digest/trigger -H 'X-API-Key: YOUR_KEY'
```



Scheduler smoke test (isolated):
```bash
python -c "from scheduler.jobs import run_pipeline_once; import asyncio; asyncio.run(run_pipeline_once())"
```

## Upgrading to agent mode
`ingest/base.py` defines `BaseIngestor` with strict `fetch -> normalize -> run` behavior, making each ingestor portable as a standalone tool without refactoring. `signals/scorer.py` exposes a pure, side-effect-free scoring function (`disruption_score`) that can be wrapped as a deterministic LLM-callable tool in v2.
