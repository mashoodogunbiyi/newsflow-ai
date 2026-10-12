# NewsFlow AI API

This directory contains NewsFlow AI's Python FastAPI backend. NFA-13 establishes the application entry point, health check, local API documentation, consistent error responses, and automated foundation tests.

## Requirements

- Python 3.10 or newer. Python 3.12 is recommended and recorded in `.python-version`.
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

## Run the API

Activate the virtual environment, then run:

```bash
fastapi dev app/main.py
```

Keep that terminal running while using these local addresses:

- Health check: `http://127.0.0.1:8000/health`
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

## Run the tests

```bash
pytest
```

The test suite verifies the health response, generated OpenAPI schema, Swagger UI availability, and standard 404 error response.

## Project structure

```text
apps/api/
|-- app/
|   |-- api/routes/health.py    # GET /health
|   |-- core/errors.py          # Standard JSON exception handlers
|   |-- models/health.py        # Health response schema
|   `-- main.py                 # FastAPI application factory and entry point
|-- tests/test_api.py           # API foundation tests
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
- `httpx2` supports Starlette's test client used by FastAPI.
- `pytest` runs the automated tests.
- `hatchling` builds the installable Python package.

Application code must not read secrets directly from committed files. Future OpenAI credentials and other secrets will be provided through ignored environment variables or a managed secret store.
