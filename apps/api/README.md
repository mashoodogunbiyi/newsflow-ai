# NewsFlow AI API

This directory contains NewsFlow AI's Python FastAPI backend. NFA-13 establishes the application foundation. NFA-14 adds PostgreSQL connectivity and readiness checking. NFA-15 adds validated environment-based configuration and secure credential loading. NFA-17 adds Ruff linting and formatting while retaining Pytest as the backend test framework.

## Requirements

- Python 3.10 or newer. Python 3.12 is recommended and recorded in `.python-version`.
- PostgreSQL 16 or another currently supported PostgreSQL release running locally.
- A terminal opened in `apps/api`.

The current FastAPI release requires Python 3.10 or newer. Do not use the macOS system Python 3.9 environment for this application.

## Local setup

From the repository root:

```bash
cd apps/api
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

If your supported Python executable has a different name, replace `python3.12` with that executable in the virtual-environment command.

## Configure the application

Create a local PostgreSQL role and database using your preferred local PostgreSQL installation. The development database name used by this project is `newsflow`. Detailed tables and relationships are intentionally deferred to Epic E2.

From the repository root, create your ignored local configuration file:

```bash
cp .env.example .env
```

Edit only `.env` and replace the placeholders with your local values:

```dotenv
APP_ENV=development
NEWS_SOURCE_MODE=fixture
DATABASE_URL=postgresql://your_local_user:your_local_password@localhost:5432/newsflow
DATABASE_CONNECT_TIMEOUT_SECONDS=5
OPENAI_API_KEY=your_real_openai_api_key
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

`DATABASE_URL` is required when the API starts. `OPENAI_API_KEY` is loaded and validated by the backend but is required only when an OpenAI-powered feature runs. This keeps the current non-AI API usable while its OpenAI integration is developed. Empty values and the committed example placeholders produce clear errors without printing secret values.

Do not add real credentials to `.env.example`, source code, browser code, documentation, Jira, screenshots, commits, or pull requests. The repository `.gitignore` excludes `.env` files while retaining the safe `.env.example` template. The OpenAI API key is server-side only and must never use a `NEXT_PUBLIC_` name because Next.js exposes variables with that prefix to browser code. This follows [OpenAI's API authentication guidance](https://developers.openai.com/api/reference/overview), which says API keys must be loaded from an environment variable or key management service on the server.

### Configuration reference

| Variable | Required | Sensitive | Purpose |
|---|---|---|---|
| `APP_ENV` | No | No | Selects `development`, `test`, `staging`, or `production`; defaults to `development`. |
| `NEWS_SOURCE_MODE` | No | No | Remains `fixture` while live CNN access is not authorised. |
| `DATABASE_URL` | Yes at API startup | Yes | PostgreSQL connection string containing the database credentials. |
| `DATABASE_CONNECT_TIMEOUT_SECONDS` | No | No | Database connection timeout from 1 to 30 seconds; defaults to 5. |
| `OPENAI_API_KEY` | Yes for OpenAI features | Yes | Authenticates server-side OpenAI API requests. |
| `NEXT_PUBLIC_API_BASE_URL` | No | No | Public URL used by the frontend to reach the backend. Never place credentials here. |

Operating rules:

- Local development uses the ignored repository-root `.env` file.
- Deployed environments must inject secrets through their environment or a managed secret store instead of committing a file.
- Application code accesses credentials through `Settings`; it must not read or hard-code credentials elsewhere.
- Logs, API responses, exception messages, tests, screenshots, and Jira evidence must not contain secret values.
- If a secret is exposed, revoke or rotate it immediately, remove it from active files, and treat Git-history cleanup as a separate incident response task.

## Run the API

Activate the virtual environment, then run:

```bash
fastapi dev app/main.py
```

Keep that terminal running while using these local addresses:

- Health check: `http://127.0.0.1:8000/health`
- Database readiness: `http://127.0.0.1:8000/ready`
- Interactive Swagger UI: `http://127.0.0.1:8000/docs`
- Alternative ReDoc documentation: `http://127.0.0.1:8000/redoc`
- OpenAPI schema: `http://127.0.0.1:8000/openapi.json`

The links work only while the local FastAPI development server is running. They are not public deployment URLs.

The health check returns:

```json
{
  "status": "ok"
}
```

The readiness check runs `SELECT 1` against PostgreSQL and returns:

```json
{
  "status": "ready",
  "database": "connected"
}
```

The API checks PostgreSQL during startup. It stops with a safe configuration or connection error when `DATABASE_URL` is missing, invalid, or unreachable. If PostgreSQL becomes unavailable while the API is running, `/ready` returns HTTP `503` without exposing credentials or driver details. `/health` remains a liveness check and does not query the database.

## Run with Docker Compose

NFA-16 adds a backend development image and runs it with the frontend and PostgreSQL from the root `compose.yaml` file. From the repository root:

```bash
cp .env.example .env
docker compose up --build
```

Replace the PostgreSQL placeholders in `.env` before starting. Compose supplies a container-specific database URL that uses `database` as the PostgreSQL hostname. The backend waits for PostgreSQL to become healthy, performs its own startup connection check, and then exposes its health and readiness endpoints on `http://localhost:8000`.

Use `docker compose down` for a normal shutdown. The PostgreSQL named volume remains available for the next startup. See the [complete Docker development guide](../../infrastructure/docker/README.md) for configuration, service checks, logs, persistence, and troubleshooting.

## Run the tests

```bash
pytest
```

The normal test suite uses a database test double, so it does not need real credentials, an OpenAI API key, or a running PostgreSQL server. It verifies environment loading, masked secret representations, missing-configuration errors, placeholder rejection, startup checking, liveness, readiness, safe database failure responses, generated OpenAPI documentation, and standard API errors.

To prove the connection against your configured local PostgreSQL database, run the opt-in integration test without placing the URL in Git:

```bash
TEST_DATABASE_URL="$DATABASE_URL" pytest -m integration tests/test_database_integration.py
```

## Code quality

Install the development dependencies, including Ruff and Pytest, with `python -m pip install -e ".[dev]"`. Run the backend checks from `apps/api`:

```bash
ruff check .
ruff format --check .
pytest
```

Apply safe automatic lint fixes and formatting when needed:

```bash
ruff check --fix .
ruff format .
```

Ruff checks Python syntax errors, undefined names, import ordering, modern Python usage, and common bug patterns. Ruff also supplies the single Python formatter, avoiding competing formatting tools. Pytest continues to cover the health endpoint, database readiness, safe error handling, and secure configuration.

## Project structure

```text
apps/api/
|-- Dockerfile                  # FastAPI development image
|-- .dockerignore               # Files excluded from the image build context
|-- app/
|   |-- api/routes/health.py    # GET /health
|   |-- core/config.py          # Environment-based settings
|   |-- core/errors.py          # Standard JSON exception handlers
|   |-- database/connection.py  # PostgreSQL connection check
|   |-- models/health.py        # Health response schema
|   `-- main.py                 # FastAPI application factory and entry point
|-- tests/test_api.py           # API and readiness tests
|-- tests/test_config.py        # Environment and secret-safety tests
|-- tests/test_database_integration.py # Opt-in live PostgreSQL test
|-- .python-version             # Recommended Python runtime
|-- pyproject.toml              # Application and development dependencies
`-- README.md                   # Backend setup and operating guide
```

## Error response format

Expected HTTP errors, validation errors, and unexpected server errors use one top-level `error` object. For example, an unknown route returns:

```json
{
  "error": {
    "code": "http_404",
    "message": "Not Found"
  }
}
```

Unexpected exceptions are logged on the server, while clients receive a generic message that does not expose internal implementation details.

## Dependencies

Dependencies are declared in `pyproject.toml`:

- `fastapi[standard-no-fastapi-cloud-cli]` provides FastAPI, the Uvicorn development server, and the standard local development dependencies without adding deployment tooling.
- `psycopg[binary]` provides the PostgreSQL driver and asynchronous connection support.
- `pydantic-settings` validates environment-based application settings and masks the database URL and OpenAI API key as secret values.
- `httpx2` supports Starlette's test client used by FastAPI.
- `pytest` runs the automated tests.
- `ruff` provides Python linting, import checks, bug-pattern checks, and formatting.
- `hatchling` builds the installable Python package.

Application code must not read secrets directly from committed files. OpenAI credentials, database credentials, and other secrets must be provided through ignored environment variables or a managed secret store.
