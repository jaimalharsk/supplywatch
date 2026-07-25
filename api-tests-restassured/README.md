# SupplyWatch API Tests (REST Assured + TestNG)

This is a REST Assured + TestNG contract test suite that runs against a **live,
locally running** instance of the SupplyWatch FastAPI service. There is no
mocking or stubbed server involved -- every test in this suite makes a real
HTTP call to a real FastAPI process, which itself talks to a real Postgres
database.

## What it covers

- `GET /health` -- returns 200, `data.status == "ok"`, `meta.version` present.
- `POST /auth/keys` -- creates an API key; `data.api_key` starts with `sw_`;
  defaults to `tier: "free"` when omitted; explicit `tier: "free"` passes
  through unchanged.
- `GET /materials`:
  - returns 401 with no `X-API-Key` header.
  - returns 200 with exactly the 8 seeded materials when a valid API key is
    supplied, including "Gallium" and "Cobalt".
- `GET /materials/{id}/signal` -- returns 404 (`"signal not found"`) on a
  fresh database where no scoring job has run yet. This is documented,
  expected behavior for the current environment, not a bug.
- `GET /materials/{id}/history` -- returns 200 with an empty `data` array on
  a fresh database.
- `POST /alerts/subscribe` -- subscribes to an alert for a material and
  returns a non-null `data.id`.
- `GET /alerts/history` -- returns 200 with an array (empty is expected,
  since no alert has actually fired without a scoring run).

## Prerequisites

1. A Postgres instance reachable at the URL configured in the SupplyWatch
   app's `.env` (`DATABASE_URL`).
2. The SupplyWatch FastAPI app running locally on `http://127.0.0.1:8001`,
   e.g. from `C:/Users/malha/supplywatch/supplywatch`:

   ```
   python -m venv .venv-ra
   ./.venv-ra/Scripts/python.exe -m pip install -r requirements.txt
   # create a .env with DATABASE_URL, ENABLE_SCHEDULER=false, etc. -- see main repo README
   ./.venv-ra/Scripts/python.exe -m uvicorn main:app --host 127.0.0.1 --port 8001
   ```

3. Confirm the app is up: `curl http://127.0.0.1:8001/health` should return
   `{"data":{"status":"ok"},...}`.

4. Java 17 and Maven available (`JAVA_HOME` pointing at a JDK 17 install).

## Running the tests

From this directory (`api-tests-restassured/`):

```
mvn test
```

This compiles the test sources and runs the TestNG suite defined in
`testng.xml` via the Maven Surefire plugin. All 4 test classes talk directly
to `http://127.0.0.1:8001` (see `BaseApiTest.BASE_URI`); there is nothing to
configure beyond having the API reachable at that address.

## Project layout

```
api-tests-restassured/
  pom.xml                     # Java 17, REST Assured 5.5.0, TestNG 7.10.2, Surefire
  testng.xml                  # TestNG suite definition
  src/test/java/com/supplywatch/apitests/
    BaseApiTest.java          # shared RestAssured.baseURI setup + API-key helper
    HealthApiTest.java
    ApiKeyApiTest.java
    MaterialsApiTest.java
    AlertsApiTest.java
```
