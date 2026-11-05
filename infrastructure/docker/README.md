# Docker development environment

NFA-84 packages the NewsFlow AI frontend, backend, and PostgreSQL database as a reproducible local stack. Run the commands in this guide from the repository root.

## Services and networking

```text
Browser
  |-- http://localhost:3000 --> frontend:3000
  `-- http://localhost:8000 --> backend:8000
                                      |
                                      `-- database:5432
```

Docker Compose creates a private network and resolves services by name:

- `frontend` runs the standalone Next.js production server as a non-root user.
- `backend` runs FastAPI through Uvicorn as a non-root user.
- `database` runs PostgreSQL 16 and stores its data in `postgres_data`.
- `migrate` is a one-shot service that applies Alembic migrations before FastAPI starts.
- `image_storage_data` stores private development image objects outside the backend container.

Only ports bound to `127.0.0.1` are published to the host. PostgreSQL must be healthy before migrations run, migrations must succeed before FastAPI starts, and FastAPI must be ready before Next.js starts.

## First-time configuration

Create the ignored local environment file:

```bash
cp .env.example .env
```

Replace the PostgreSQL placeholders in `.env`:

```dotenv
POSTGRES_USER=your_local_user
POSTGRES_PASSWORD=your_local_password
POSTGRES_DB=newsflow
```

Use development-only values. Do not put a production password, OpenAI key, or other real secret in a Dockerfile, `compose.yaml`, `.env.example`, documentation, screenshots, Jira, or Git. The root `.env` is excluded by `.gitignore`.

`DATABASE_URL` in `.env` supports running FastAPI directly on the host. Compose builds its own container-only URL with the hostname `database`; it does not expose that connection string to browser code.

Validate the Compose model without printing resolved configuration:

```bash
docker compose config --quiet
```

Missing PostgreSQL settings stop configuration with a clear error.

## Build and start

Build the final images, start in the background, and wait for health checks:

```bash
docker compose up --build --detach --wait
docker compose ps
```

The one-shot `migrate` service automatically runs `alembic upgrade head` on every start. Alembic safely skips migrations already applied.

Open:

- Frontend: [http://localhost:3000](http://localhost:3000)
- FastAPI liveness: [http://localhost:8000/health](http://localhost:8000/health)
- FastAPI database readiness: [http://localhost:8000/ready](http://localhost:8000/ready)
- FastAPI documentation: [http://localhost:8000/docs](http://localhost:8000/docs)

Start without `--detach` when you want the logs in the current terminal:

```bash
docker compose up --build
```

Press Control+C to stop that foreground process. Do not type the words `Control-C` as a command.

## Logs and checks

View service state and logs:

```bash
docker compose ps
docker compose logs --follow
docker compose logs --follow backend
```

Check the database revision:

```bash
docker compose exec backend alembic current
docker compose exec backend alembic history
```

Load optional synthetic fixtures explicitly:

```bash
docker compose exec -e SEED_DATA_ENABLED=true backend python -m app.database.seed
```

The seed command is repeatable, contains no real credentials or licensed news copy, and refuses staging and production. `SEED_DATA_ENABLED` remains `false` in normal Compose configuration.

## Stop, start, and restart

Stop running containers but keep them available:

```bash
docker compose stop
```

Start stopped containers again:

```bash
docker compose start
```

Restart running services:

```bash
docker compose restart
```

Remove containers and the private network while preserving database and image volumes:

```bash
docker compose down
```

Recreate the stack later with:

```bash
docker compose up --detach --wait
```

Only when you intentionally want to erase the local database and private development images, use:

```bash
docker compose down --volumes
```

`--volumes` permanently deletes Compose-managed development data and is not a normal shutdown command.

## Automated packaging verification

Run the isolated NFA-84 lifecycle test:

```bash
bash scripts/verify_docker_packaging.sh
```

The script uses separate ports and volumes, synthetic credentials held only in the process environment, and automatic cleanup. It verifies:

- required configuration fails closed;
- Compose configuration is valid;
- frontend and backend images build;
- migrations run against a fresh PostgreSQL database;
- frontend, backend, and database become healthy;
- frontend and backend processes are not root;
- FastAPI can reach PostgreSQL;
- a database marker survives PostgreSQL restart;
- application containers recover after restart;
- data survives a clean stop and start; and
- all temporary containers, volumes, networks, and locally built test images are removed.

Force a clean dependency and image rebuild with:

```bash
NFA84_NO_CACHE=true bash scripts/verify_docker_packaging.sh
```

GitHub Actions runs the normal isolated verification on pull requests and updates to `main`.

## Verified image review

The clean Apple Silicon build on 5 November 2026 produced these uncompressed local image sizes:

| Image                |   Size | Review                                                                                            |
| -------------------- | -----: | ------------------------------------------------------------------------------------------------- |
| Next.js frontend     | 308 MB | Runtime contains Node.js, standalone server output, static assets, and public files only.         |
| FastAPI backend      | 472 MB | Runtime contains Python, the installed application, runtime dependencies, and Alembic files only. |
| PostgreSQL 16 Alpine | 411 MB | Official upstream image used without custom application content.                                  |

The frontend and backend use multi-stage builds. Source tests, local virtual environments, development reports, caches, `.git`, and frontend development dependencies are excluded from the final application images. Docker shares identical layers even when the migration and backend services refer to the same backend build.

These local development images have not been optimised against a production registry, vulnerability policy, or deployment platform. Image compression and architecture change the transferred size.

## Development and production differences

This Compose stack is approved for local development and a controlled synthetic-data demonstration. It is not a production deployment definition.

A production design still requires:

- managed secret storage and rotation;
- TLS and a trusted reverse proxy;
- managed PostgreSQL backup, restore, and high availability;
- production object storage instead of the local volume adapter;
- deployment-specific observability, scaling, rate limiting, and rollback;
- approved image registry, signing, vulnerability scanning, and base-image update policy;
- least-privilege network and runtime controls for the selected platform; and
- explicit authorisation before any live CNN integration.

The development services use restart policies, health checks, non-root application users, dropped Linux capabilities, and `no-new-privileges`, but these do not replace a production security review.

## Troubleshooting

- If a port is already in use, change `FRONTEND_PORT`, `BACKEND_PORT`, or `POSTGRES_PORT` in `.env`.
- If a placeholder error appears, replace `POSTGRES_USER` and `POSTGRES_PASSWORD` in `.env`.
- PostgreSQL uses its initial username, password, and database only when the data volume is first created. If those values change later, restore the old values or deliberately recreate the local volume.
- Use `docker compose ps` for health state and `docker compose logs SERVICE_NAME` for startup errors.
- If migrations fail, inspect `docker compose logs migrate`; the backend will not start after an unsuccessful migration.
- If the frontend opens but authentication fails, confirm both `backend` and `database` are healthy.
