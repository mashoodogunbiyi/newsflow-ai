# NewsFlow AI Local Development Guide

This guide explains how to install, configure, run, and test NewsFlow AI locally. It is written for a developer who has not worked on the project before.

NewsFlow AI currently contains:

- frontend - the Next.js application in apps/web
- backend - the FastAPI application in apps/api
- database - PostgreSQL 16

The application currently uses fixture news data. Live CNN access remains disabled until an authorised access method is approved.

## 1. Choose a setup method

1. **Docker Compose - recommended for first-time setup.** Docker builds and runs all three services. Only Git and Docker are required on the host.
2. **Manual setup - useful for developing one service.** Install Node.js, Python, and PostgreSQL separately and run each service in its own terminal.

## 2. Required software and versions

| Software                        |           Required version | Needed for                                    |
| ------------------------------- | -------------------------: | --------------------------------------------- |
| Git                             |              2.30 or later | All setups                                    |
| Docker Desktop or Docker Engine |                24 or later | Docker setup                                  |
| Docker Compose plugin           |             v2.20 or later | Docker setup                                  |
| Node.js                         |             20.19 or later | Manual frontend setup                         |
| npm                             | 11 or a compatible release | Manual frontend setup                         |
| Python                          |               3.10 to 3.14 | Manual backend setup                          |
| Python 3.12                     |                Recommended | Matches .python-version and the backend image |
| PostgreSQL                      |                         16 | Manual database setup                         |

curl is optional but useful for checking API endpoints.

Check installed versions:

```bash
git --version
docker --version
docker compose version
node --version
npm --version
python3.12 --version
psql --version
```

Node.js, Python, PostgreSQL, and psql do not need to be installed on the host when all services run through Docker.

## 3. Get the repository

Clone the project and enter its root directory:

```bash
git clone https://github.com/mashoodogunbiyi/newsflow-ai.git
cd newsflow-ai
```

If it is already cloned, open a terminal in the repository root and check its state:

```bash
git status
```

All commands below start in the repository root unless stated otherwise.

## 4. Configure environment variables

Create the private local file from the safe example:

```bash
cp .env.example .env
```

Open .env and replace the PostgreSQL username and password placeholders with development-only values:

```dotenv
APP_ENV=development
NEWS_SOURCE_MODE=fixture
FRONTEND_ORIGIN=http://localhost:3000
FRONTEND_PORT=3000
BACKEND_PORT=8000
POSTGRES_PORT=5432
POSTGRES_USER=choose_a_local_username
POSTGRES_PASSWORD=choose_a_local_password
POSTGRES_DB=newsflow
DATABASE_URL=postgresql://choose_a_local_username:choose_a_local_password@localhost:5432/newsflow
DATABASE_CONNECT_TIMEOUT_SECONDS=5
REGISTRATION_RATE_LIMIT_ATTEMPTS=5
REGISTRATION_RATE_LIMIT_WINDOW_SECONDS=60
LOGIN_RATE_LIMIT_ATTEMPTS=5
LOGIN_RATE_LIMIT_WINDOW_SECONDS=60
SESSION_LIFETIME_MINUTES=60
SEED_DATA_ENABLED=false
OPENAI_API_KEY=your_openai_api_key_here
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
API_INTERNAL_BASE_URL=http://localhost:8000
```

Use the same username and password in POSTGRES_USER, POSTGRES_PASSWORD, and DATABASE_URL. URL-encode special characters inside DATABASE_URL.

### Environment variable reference

| Variable                         | Purpose                                           | Required now                                     |
| -------------------------------- | ------------------------------------------------- | ------------------------------------------------ |
| APP_ENV                          | Selects the application environment.              | No - defaults to development                     |
| NEWS_SOURCE_MODE                 | Selects the approved news source mode.            | No - must remain fixture                         |
| FRONTEND_ORIGIN                  | Allows this exact browser origin to send API cookies. | No - defaults to http://localhost:3000        |
| FRONTEND_PORT                    | Host port for the Docker frontend.                | No - defaults to 3000                            |
| BACKEND_PORT                     | Host port for the Docker backend.                 | No - defaults to 8000                            |
| POSTGRES_PORT                    | Host port for Docker PostgreSQL.                  | No - defaults to 5432                            |
| POSTGRES_USER                    | Creates the Docker database user.                 | Yes for Docker Compose                           |
| POSTGRES_PASSWORD                | Creates the Docker database password.             | Yes for Docker Compose                           |
| POSTGRES_DB                      | Creates the Docker database.                      | Yes for Docker Compose                           |
| DATABASE_URL                     | Connects a host-run backend to PostgreSQL.        | Yes for a manually run backend                   |
| DATABASE_CONNECT_TIMEOUT_SECONDS | Sets the database timeout.                        | No - defaults to 5                               |
| REGISTRATION_RATE_LIMIT_ATTEMPTS | Limits registration attempts per client.         | No - defaults to 5                               |
| REGISTRATION_RATE_LIMIT_WINDOW_SECONDS | Sets the rate-limit window in seconds.      | No - defaults to 60                              |
| LOGIN_RATE_LIMIT_ATTEMPTS        | Limits login attempts per client.                | No - defaults to 5                               |
| LOGIN_RATE_LIMIT_WINDOW_SECONDS  | Sets the login rate-limit window in seconds.     | No - defaults to 60                              |
| SESSION_LIFETIME_MINUTES         | Sets the absolute authenticated-session lifetime.| No - defaults to 60                              |
| SEED_DATA_ENABLED                | Explicitly allows synthetic seed loading.        | No - keep false except for one seed command      |
| OPENAI_API_KEY                   | Authenticates future server-side OpenAI features. | Not required for current features or tests       |
| NEXT_PUBLIC_API_BASE_URL         | Gives the browser the public backend URL.         | No - defaults to http://localhost:8000 in Docker |
| API_INTERNAL_BASE_URL            | Lets the Next.js server reach FastAPI.            | No - defaults to http://localhost:8000 manually  |

Docker Compose constructs its own backend database URL using database as the hostname and sets the frontend's internal API URL to http://backend:8000. The DATABASE_URL and API_INTERNAL_BASE_URL values in .env are for services running directly on the host.

### Secret safety

- Add real credentials only to .env.
- Never put credentials in .env.example, source code, browser variables, documentation, Jira, screenshots, commits, or pull requests.
- Never name the OpenAI key NEXT_PUBLIC_OPENAI_API_KEY. Next.js exposes NEXT_PUBLIC_ values to the browser.
- Confirm that Git ignores the file:

```bash
git check-ignore -v .env
```

The output should identify a rule from .gitignore.

## 5. Recommended Docker setup

Make sure Docker Desktop is running, or start Docker Engine on Linux.

Validate the configuration without printing resolved secrets:

```bash
docker compose config --quiet
```

Build and start all services:

```bash
docker compose up --build
```

Keep that terminal open. Docker starts PostgreSQL first, FastAPI after the database is healthy, and Next.js after the backend is healthy.

To run in the background:

```bash
docker compose up --build --detach
docker compose ps
```

All three services should eventually report running or healthy.

Create the database schema and optionally load the synthetic fixture:

```bash
docker compose exec backend alembic upgrade head
docker compose exec -e SEED_DATA_ENABLED=true backend python -m app.database.seed
```

The seed command is repeatable and does not create duplicate fixtures.

### Local addresses

| Service            | Address                                                      | Expected result                           |
| ------------------ | ------------------------------------------------------------ | ----------------------------------------- |
| Frontend           | [http://localhost:3000](http://localhost:3000)               | NewsFlow AI homepage                      |
| Backend health     | [http://localhost:8000/health](http://localhost:8000/health) | {"status":"ok"}                           |
| Database readiness | [http://localhost:8000/ready](http://localhost:8000/ready)   | {"status":"ready","database":"connected"} |
| Swagger UI         | [http://localhost:8000/docs](http://localhost:8000/docs)     | Interactive API documentation             |

These links work only while the services are running. They are not public website links.

Check the API from the terminal:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/ready
```

Register a development account after applying the migration:

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"example@email.com","password":"ExampleSecurePassword123!"}'
```

The response contains only the generated ID, normalised email, and success message. It never contains the password or password hash. The full endpoint contract is available in Swagger UI.

Log in and save the returned cookies after registering the account:

```bash
curl -c cookies.txt -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"example@email.com","password":"ExampleSecurePassword123!"}'

curl -b cookies.txt http://localhost:8000/api/v1/auth/me
```

The session identifier is in an HTTP-only cookie and cannot be read by browser JavaScript. PostgreSQL stores only its SHA-256 hash. Logout is a state-changing request, so it also requires the session-specific CSRF cookie value in the `X-CSRF-Token` header:

```bash
CSRF_TOKEN=$(awk '$6 == "newsflow_csrf" { print $7 }' cookies.txt)
curl -b cookies.txt -X POST http://localhost:8000/api/v1/auth/logout \
  -H "X-CSRF-Token: ${CSRF_TOKEN}"
rm cookies.txt
```

The cookie file contains temporary local credentials, so delete it when the check is complete. Sessions expire after 60 minutes by default. Staging and production session cookies receive the HTTPS-only `Secure` attribute automatically.

View logs:

```bash
docker compose logs --follow
docker compose logs --follow backend
```

Stop the application without deleting database data:

```bash
docker compose down
```

Data remains in the postgres_data volume. Do not use docker compose down --volumes unless you deliberately want to delete the local development database.

## 6. Manual PostgreSQL setup

Skip this section when using the full Docker setup.

Install and start PostgreSQL 16 using the official installer or an operating-system package manager. Confirm it is accepting connections:

```bash
psql --version
pg_isready -h localhost -p 5432
```

Create a development role and database:

```bash
createuser --pwprompt newsflow_user
createdb --owner=newsflow_user newsflow
```

Update the root .env with the same role, password, and database:

```dotenv
DATABASE_URL=postgresql://newsflow_user:your_url_encoded_password@localhost:5432/newsflow
```

Alternatively, run only PostgreSQL in Docker while running the applications manually:

```bash
docker compose up --detach database
docker compose ps database
```

The root .env must have matching POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB, and DATABASE_URL values.

## 7. Manual backend setup

Make sure PostgreSQL is running. From the repository root:

```bash
cd apps/api
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
alembic upgrade head
fastapi dev app/main.py
```

On Windows PowerShell, activate the environment with:

```powershell
.venv\Scripts\Activate.ps1
```

The backend finds the root .env automatically. Missing, unchanged, or unreachable database configuration produces a clear error without revealing the credential.

Keep the server running and open:

- http://127.0.0.1:8000/health
- http://127.0.0.1:8000/ready
- http://127.0.0.1:8000/docs

Stop it with Control-C. Leave the virtual environment with:

```bash
deactivate
```

To add the optional synthetic data while the environment is active:

```bash
SEED_DATA_ENABLED=true python -m app.database.seed
```

The script refuses to run unless `APP_ENV` is `development` or `test`. Keep `SEED_DATA_ENABLED=false` in `.env` and opt in for only the command that needs it.

## 8. Manual frontend setup

Open another terminal at the repository root:

```bash
cd apps/web
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). Stop the server with Control-C.

The authentication pages require FastAPI and PostgreSQL to be running. Visit `/register` to create an account, `/login` to sign in, and `/dashboard` to verify that the session survives a refresh. The browser calls the same-origin `/api/auth` route; the Next.js server then uses `API_INTERNAL_BASE_URL` to contact FastAPI.

For a clean, reproducible installation from package-lock.json, use:

```bash
npm ci
```

## 9. Run quality checks and tests

Run all frontend checks from apps/web:

```bash
npm run lint
npm run format:check
npm run typecheck
npm test
npm run build
```

The frontend tests check the homepage and the NFA-24 registration, login, error, loading, logout, session-restoration, gateway, and route-protection behaviour.

Run all backend checks from apps/api with the development virtual environment active:

```bash
ruff check .
ruff format --check .
pytest
```

The normal backend tests use database test doubles. They do not need PostgreSQL, real database credentials, or an OpenAI API key. The NFA-25 authorisation tests create two synthetic users and prove that neither user can read, change, delete, or export the other user's saved content.

Migration verification uses a separate disposable PostgreSQL database because the test deliberately upgrades, seeds twice, rolls back, and rebuilds the schema:

```bash
TEST_DATABASE_URL="postgresql://USER:PASSWORD@localhost:5432/newsflow_migration_test" \
ALLOW_DATABASE_RESET_FOR_TESTS=true \
pytest -m integration tests/test_migrations_integration.py
```

Never use the normal `newsflow` development database for that destructive test.

Run the registration integration test only against a separate disposable database:

```bash
TEST_DATABASE_URL="postgresql://USER:PASSWORD@localhost:5432/newsflow_registration_test" \
ALLOW_DATABASE_RESET_FOR_TESTS=true \
pytest -m integration tests/test_registration_integration.py
```

Run the NFA-23 authentication integration test only against a separate disposable database:

```bash
TEST_DATABASE_URL="postgresql://USER:PASSWORD@localhost:5432/newsflow_authentication_test" \
ALLOW_DATABASE_RESET_FOR_TESTS=true \
pytest -m integration tests/test_authentication_integration.py
```

Apply formatting when needed:

```bash
# From apps/web
npm run format

# From apps/api
ruff check --fix .
ruff format .
```

Review automatic changes before committing them.

## 10. Verify the complete setup

A working environment meets this checklist:

- The homepage opens at http://localhost:3000.
- GET http://localhost:8000/health returns HTTP 200 and {"status":"ok"}.
- GET http://localhost:8000/ready returns HTTP 200 and confirms the database connection.
- Swagger UI opens at http://localhost:8000/docs.
- POST http://localhost:8000/api/v1/auth/register creates an account and returns no password data.
- POST http://localhost:8000/api/v1/auth/login sets an HTTP-only session cookie and returns no credential or token data.
- GET http://localhost:8000/api/v1/auth/me returns the logged-in user's ID and email.
- POST http://localhost:8000/api/v1/auth/logout requires CSRF proof and invalidates the session.
- Protected `/api/v1/library/items` operations use the session user as owner and reject cross-user record identifiers.
- Saved-content creates, updates, and deletes require the session-specific CSRF token.
- http://localhost:3000/register creates an account and offers a route to sign in.
- http://localhost:3000/login authenticates the account and redirects to the dashboard.
- http://localhost:3000/dashboard restores a valid session after refresh and redirects an unauthenticated visitor.
- The dashboard logout button revokes the session and returns to the login page.
- Frontend linting, formatting, type checking, tests, and build pass.
- Backend linting, formatting, and tests pass.
- `alembic current` reports revision `20261025_0002`.
- Running the seed command twice reports the same fixture counts without duplicates.
- git status --short does not show .env, dependency directories, build output, or test caches.

## 11. Common setup problems

### A local link cannot be reached

The URL works only while its service is running. Start the Docker stack or the related manual server and refresh the page.

```bash
docker compose ps
docker compose logs frontend
docker compose logs backend
```

### Docker is not available

Install Docker Desktop or Docker Engine with the Compose plugin. If Docker is installed but cannot reach its daemon, start Docker Desktop or the Docker service.

### Compose reports missing POSTGRES_ variables

The root .env is missing or incomplete. Run cp .env.example .env, then replace POSTGRES_USER, POSTGRES_PASSWORD, and POSTGRES_DB.

### The backend rejects example placeholders

Replace your_local_user and your_local_password everywhere in .env. The application deliberately rejects unchanged example database values.

### The backend cannot reach PostgreSQL

- Confirm PostgreSQL or the Docker database service is running.
- Use localhost in DATABASE_URL when FastAPI runs on the host.
- Do not use localhost for the backend container. Compose supplies database automatically.
- Check the username, password, port, and database name.
- For Docker, check docker compose logs database and the ready endpoint.

### Changed Docker database credentials do not work

PostgreSQL applies its initial credentials only when the data volume is created. Restore the original values or deliberately recreate the development volume. Recreating it deletes its data, so back up important data first.

### Port 3000, 8000, or 5432 is in use

For Docker, change FRONTEND_PORT, BACKEND_PORT, or POSTGRES_PORT in .env. If the backend port changes, also update NEXT_PUBLIC_API_BASE_URL.

### Python is unsupported

The macOS system python3 can be too old. Install Python 3.12, create the environment with python3.12 -m venv .venv, activate it, and check python --version.

### psql, createuser, or createdb is not found

Install PostgreSQL 16 client tools and add them to the system path, or use the Docker database.

### Frontend dependencies disagree

Confirm Node.js 20.19 or later is active, then run npm ci from apps/web. Peer warnings can appear while Next.js lint plugins update their ESLint 10 declarations. The current configuration has been verified and linting should still pass.

### Authentication pages report that the service is unavailable

- Confirm FastAPI is running and `http://localhost:8000/health` succeeds.
- When running Next.js directly, set `API_INTERNAL_BASE_URL=http://localhost:8000`.
- When using Docker Compose, do not replace the automatically supplied `http://backend:8000` value with localhost inside the frontend container.
- Confirm PostgreSQL is running and the backend `/ready` endpoint succeeds.

### An OpenAI key error appears

Current health checks, the fixture homepage, and normal tests do not need an OpenAI key. A future OpenAI-powered feature will need a real key in .env. Never send it to the frontend or commit it.

## 12. Related documentation

- [Project overview](../README.md)
- [Frontend guide](../apps/web/README.md)
- [Backend guide](../apps/api/README.md)
- [Object-level authorisation](authorization.md)
- [Docker guide](../infrastructure/docker/README.md)
- [Project plan](../PROJECT_PLAN.md)
- [Project management workflow](../PROJECT_MANAGEMENT.md)

## 13. Verification record

These instructions were checked on 25 October 2026 against the repository structure, environment template, Docker Compose configuration, authentication interface, frontend scripts, backend package configuration, and working toolchain.

The verified environment used Git 2.50.1, Docker 29.8.2, Docker Compose v5.5.1, Node.js 26.11.1, npm 11.20.0, Python 3.12.15 in the backend virtual environment, and the Compose-managed postgres:16-alpine image. Other developers should use the supported versions listed above.
