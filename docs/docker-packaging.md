# NFA-84 - Docker Packaging Verification

## Outcome

NewsFlow AI has a verified Docker Compose package for a controlled local development and synthetic-data demonstration environment.

The package builds and coordinates:

- the standalone Next.js frontend;
- the FastAPI backend;
- the PostgreSQL 16 database;
- automatic Alembic migrations; and
- one repeatable synthetic demonstration record loaded by a development-only one-shot service; and
- persistent private development image storage.

This evidence does not approve a public or production deployment.

## Packaging decisions

| Area             | Decision                                                                    | Reason                                                                                    |
| ---------------- | --------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| Frontend image   | Multi-stage Node.js 22 Alpine build with Next.js standalone output          | Keeps build tooling and development dependencies out of the runtime stage.                |
| Backend image    | Multi-stage Python 3.12 slim build with a prebuilt virtual environment      | Installs an immutable application package and excludes test and local development files.  |
| Runtime identity | UID and GID 10001 for frontend and backend                                  | Avoids running application processes as root.                                             |
| Backend command  | `uvicorn app.main:app --host 0.0.0.0 --port 8000`                           | Loads the installed Python module without depending on a source-file path.                |
| Database         | Official PostgreSQL 16 Alpine image                                         | Matches the supported development database.                                               |
| Migrations       | One-shot `migrate` service before backend startup                           | Prevents the API from starting against an outdated schema.                                |
| Demo data        | One-shot `demo-data` service after migrations                               | Makes the local dashboard usable while the seed safety checks prevent production loading. |
| Persistence      | Named PostgreSQL and private-image volumes                                  | Preserves development data across normal container recreation.                            |
| Network exposure | Host ports bind to `127.0.0.1`                                              | Limits the development services to the local computer by default.                         |
| Configuration    | Required PostgreSQL variables plus safe optional defaults                   | Missing database configuration fails before startup and secrets remain outside Git.       |
| Startup order    | Database health, migration success, backend readiness, then frontend        | Each dependent service starts only when its prerequisite is usable.                       |
| Runtime controls | Non-root users, all capabilities dropped, `no-new-privileges`, init process | Applies practical local container hardening without claiming production isolation.        |

## Configuration and secret handling

The committed `.env.example` contains placeholders only. The local `.env` file is Git-ignored and supplies developer-specific settings.

Compose constructs the backend database connection inside the container network. OpenAI credentials remain backend-only and are never placed in a `NEXT_PUBLIC_` variable. Real keys, passwords, private user data, and provider content are not copied into either image.

The verification script uses synthetic, test-only database values. It passes them through the process environment and uses `/dev/null` as the Compose environment file so it does not read the developer's `.env` or reveal resolved configuration.

## Health and migration behaviour

- PostgreSQL uses `pg_isready`.
- FastAPI `/health` proves process liveness.
- FastAPI `/ready` proves application and PostgreSQL connectivity.
- Next.js is checked over HTTP on port 3000.
- `migrate` runs `alembic upgrade head` after PostgreSQL is healthy.
- `demo-data` runs the idempotent synthetic seed after a successful migration.
- The backend requires successful migration, demo-data loading and database readiness.
- The frontend requires a healthy backend.

The migration service is repeatable. Already-applied revisions are not reapplied.

## Automated verification

Command:

```bash
NFA84_NO_CACHE=true bash scripts/verify_docker_packaging.sh
```

Verified on 5 November 2026 using Docker Desktop on Apple Silicon.

| Check                                            | Result    |
| ------------------------------------------------ | --------- |
| Missing PostgreSQL configuration rejected        | Pass      |
| Compose model validation                         | Pass      |
| Clean frontend image build                       | Pass      |
| Clean backend image build                        | Pass      |
| Fresh database migration through `20261102_0015` | Pass      |
| PostgreSQL health                                | Pass      |
| FastAPI readiness and database connection        | Pass      |
| Next.js HTTP health                              | Pass      |
| Frontend and backend non-root runtime users      | Pass      |
| Database marker after PostgreSQL restart         | Pass      |
| Frontend and backend restart recovery            | Pass      |
| Full clean stop and start                        | Pass      |
| Database marker after clean stop and start       | Pass      |
| Temporary resource and local test-image cleanup  | Pass      |
| Production standalone browser journeys           | 13 passed |

The first clean run exposed a real packaging defect: the backend command referenced `app/main.py`, but the runtime image contains an installed Python package rather than the source file tree. The command was corrected to the Uvicorn module target `app.main:app`, and the complete lifecycle then passed. This preserves the multi-stage package design instead of copying the source tree back into the runtime image.

The browser regression run also exposed an outdated `next start` command after standalone output was enabled. The local `prestart` step now prepares public and static assets in the standalone directory before launching its server. The Dockerfile already assembles the same required layout directly in the runtime image. All 13 deterministic Chromium journeys then passed against the standalone production server.

## Image review

The verified uncompressed local images were:

| Image      |   Size |
| ---------- | -----: |
| Frontend   | 308 MB |
| Backend    | 472 MB |
| PostgreSQL | 411 MB |

The final frontend image contains the standalone Next.js server, static files, public assets, and Node.js runtime. The final backend image contains the Python runtime, installed production dependencies, installed application, and migration files. Tests, reports, `.git`, local environments, caches, and frontend development dependencies are excluded.

## CI integration

`.github/workflows/quality.yml` runs `scripts/verify_docker_packaging.sh` in an independent job on pull requests and changes to `main`. A failed build, health check, migration, restart, non-root assertion, or persistence assertion fails that job with the relevant Compose output.

## Operating commands

```bash
# Build, start, and wait for readiness
docker compose up --build --detach --wait

# Inspect status and logs
docker compose ps
docker compose logs --follow

# Stop without removing containers
docker compose stop

# Start stopped containers
docker compose start

# Remove containers but preserve named data volumes
docker compose down
```

`docker compose down --volumes` deliberately deletes the local database and private development image data and must not be used for normal shutdown.

## Known limitations and release boundary

- This configuration is development packaging, not a production deployment.
- The local private-image volume is not a production object-storage service.
- TLS, managed secrets, backups, restore exercises, deployment rollback, infrastructure monitoring, registry signing, and production vulnerability policy remain environment-specific work.
- Local Docker health and persistence checks do not prove production availability or disaster recovery.
- Image sizes are local uncompressed Apple Silicon results and will vary by architecture and registry compression.
- Python dependencies use reviewed bounded version ranges rather than a complete lock file, and base-image tags receive upstream updates. Exact bit-for-bit production builds require an approved lock and image-digest update process.
- The stack remains fixture-first. It does not authorise or enable live CNN access.
- Routine verification does not call OpenAI and does not require a real OpenAI key.

## Acceptance status

All NFA-84 implementation and local packaging verification criteria are complete. The document and changes are ready for Mashood Ogunbiyi's review. Public release and live CNN integration remain No-Go under the NFA-82 release boundary.
