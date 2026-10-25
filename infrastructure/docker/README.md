# Docker development environment

NFA-16 provides a local Docker Compose environment for the NewsFlow AI frontend, backend, and PostgreSQL database. Run all commands in this guide from the repository root.

## How the services connect

```text
Browser
  |-- http://localhost:3000 --> frontend container
  `-- http://localhost:8000 --> backend container
                                     |
                                     `-- database:5432 --> PostgreSQL container
```

Docker Compose creates a private network automatically. Containers use their service names as hostnames on that network:

- The backend connects to PostgreSQL at `database:5432`.
- Server-side frontend code can connect to FastAPI at `http://backend:8000`.
- Browser code uses `http://localhost:8000` because the browser runs outside Docker.

FastAPI accepts credentialed browser requests only from `FRONTEND_ORIGIN`, which defaults to `http://localhost:3000`. This exact-origin CORS rule permits cookies and the NFA-23 CSRF header without allowing untrusted origins.

The frontend waits for a healthy backend, and the backend waits for a healthy database. This ordering avoids starting a dependent service before the service it needs is ready.

## First-time setup

Create the ignored local environment file:

```bash
cp .env.example .env
```

Open `.env` and replace these example values:

```dotenv
POSTGRES_USER=your_local_user
POSTGRES_PASSWORD=your_local_password
POSTGRES_DB=newsflow
```

Use a development-only password. Do not put a production password, OpenAI key, or any other real secret in `compose.yaml`, a Dockerfile, `.env.example`, documentation, screenshots, Jira, or Git.

Use letters, numbers, and underscores for the local PostgreSQL username and password. Other characters must be URL-encoded because Compose uses these values to construct the backend database URL.

The root `.env` supplies Compose values but remains excluded by `.gitignore`. Compose constructs the container-only `DATABASE_URL` with the `database` hostname. The separate `DATABASE_URL` in `.env` continues to support running FastAPI directly on the host, where PostgreSQL is reached through `localhost`.

Published ports bind to `127.0.0.1`, so the development services are reachable from your computer but are not deliberately exposed to other devices on the local network.

## Start the application

Validate the resolved configuration without starting containers:

```bash
docker compose config --quiet
```

The `--quiet` option validates the configuration without printing resolved credential values to the terminal.

Build the images and start all services:

```bash
docker compose up --build
```

Keep that terminal open. When all services are healthy, use:

- Frontend: [http://localhost:3000](http://localhost:3000)
- Backend health: [http://localhost:8000/health](http://localhost:8000/health)
- Database readiness: [http://localhost:8000/ready](http://localhost:8000/ready)
- FastAPI documentation: [http://localhost:8000/docs](http://localhost:8000/docs)

To run in the background instead, use:

```bash
docker compose up --build --detach
docker compose ps
```

## Logs and service checks

View logs from every service:

```bash
docker compose logs --follow
```

View one service:

```bash
docker compose logs --follow backend
```

Confirm that the frontend container can reach the backend container:

```bash
docker compose exec frontend node -e "fetch('http://backend:8000/health').then(async response => console.log(response.status, await response.text()))"
```

A successful response is HTTP `200` with `{"status":"ok"}`. The backend `/ready` endpoint separately proves that FastAPI can reach PostgreSQL.

## Create the schema and load development fixtures

After the database and backend are healthy, apply every pending Alembic migration:

```bash
docker compose exec backend alembic upgrade head
```

Load the optional synthetic development records:

```bash
docker compose exec -e SEED_DATA_ENABLED=true backend python -m app.database.seed
```

The seed command is safe to repeat. It contains only fictional content, creates no usable account, and refuses staging or production environments. Do not place `SEED_DATA_ENABLED=true` permanently in committed Compose configuration.

Migration `20261025_0002` adds the NFA-23 CSRF session control and session lookup indexes. It invalidates any pre-release session rows because older rows cannot provide valid CSRF proof. After applying it, existing development users can log in again normally.

Show the current revision or migration history:

```bash
docker compose exec backend alembic current
docker compose exec backend alembic history
```

`alembic downgrade -1` is available for a disposable local database, but the initial downgrade deletes all application tables and their data. Do not run it as part of normal shutdown.

## Stop the application

Stop and remove the containers and private network:

```bash
docker compose down
```

The `postgres_data` named volume remains, so database information survives the normal shutdown and the next startup.

Only when you intentionally want to delete the local development database, run:

```bash
docker compose down --volumes
```

That command permanently deletes the Compose-managed PostgreSQL data volume. It must not be used as the normal shutdown command.

## Troubleshooting

- If a port is already in use, change `FRONTEND_PORT`, `BACKEND_PORT`, or `POSTGRES_PORT` in `.env`.
- If the backend reports an example-placeholder error, replace the `POSTGRES_USER` and `POSTGRES_PASSWORD` values in `.env`.
- If credentials change after PostgreSQL has initialised its volume, either restore the previous values or deliberately recreate the development volume. PostgreSQL applies its initial user, password, and database settings only when the data directory is first created.
- Use `docker compose ps` for health state and `docker compose logs SERVICE_NAME` for startup errors.
- If the API is healthy but application tables are missing, run `docker compose exec backend alembic upgrade head`.
