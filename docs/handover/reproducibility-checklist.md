# NewsFlow AI Reproducibility Checklist

## 1. Scope

This procedure verifies a clean candidate checkout, local configuration, Docker services, migrations, synthetic fixtures, automated tests, documentation, and the primary demonstration. It avoids live CNN access, real OpenAI calls, production data, and production storage.

Run commands from the repository root unless a step says otherwise.

## 2. Prerequisites

- [ ] Git 2.30 or later is installed.
- [ ] Docker Engine or Docker Desktop 24 or later is running.
- [ ] Docker Compose plugin 2.20 or later is installed.
- [ ] Node.js 20.19 or later and npm are installed for frontend tests and the demonstration.
- [ ] Python 3.10 to 3.14 is installed; Python 3.12 is recommended.
- [ ] Ports 3000, 8000, and 5432 are available for the integrated Docker environment.
- [ ] Ports 3100 and 4100 are available for the deterministic demonstration.

Check the tools:

```bash
git --version
docker --version
docker compose version
node --version
npm --version
python3 --version
```

## 3. Repository and version

```bash
git clone https://github.com/mashoodogunbiyi/newsflow-ai.git
cd newsflow-ai
git status --short --branch
git rev-parse HEAD
git tag --points-at HEAD
```

- [ ] The branch and commit match the final handover record.
- [ ] The working tree is clean after cloning.
- [ ] `apps/api`, `apps/web`, `docs`, `scripts`, `compose.yaml`, `.env.example`, and `README.md` exist.

For the NFA-90 candidate before commit, run:

```bash
python3 scripts/verify_handover_clean_checkout.py
```

This copies all tracked and intended untracked, non-ignored candidate files to a temporary directory. It verifies the handover package and supporting documentation without reading `.env`, `.venv`, `node_modules`, local storage, or the original working directory.

## 4. Secret and configuration safety

```bash
cp .env.example .env
git check-ignore -v .env
python3 scripts/scan_secrets.py
```

- [ ] Git reports that `.env` is ignored.
- [ ] `.env.example` contains placeholders only.
- [ ] No real key, password, private user data, or restricted article content is committed.
- [ ] `NEWS_SOURCE_MODE=fixture` remains selected.

Set development-only PostgreSQL values in `.env`. A real OpenAI key is not required for Docker health checks, routine tests, or the deterministic demonstration.

## 5. Integrated Docker setup

```bash
docker compose config --quiet
docker compose up --build --detach --wait
docker compose ps --all
curl --fail http://localhost:8000/health
curl --fail http://localhost:8000/ready
curl --fail http://localhost:3000/login
docker compose exec backend alembic current
```

- [ ] PostgreSQL becomes healthy.
- [ ] The one-shot migration and demo-data services exit successfully.
- [ ] FastAPI reports healthy and ready.
- [ ] Next.js serves the login page.
- [ ] Alembic reports the latest migration revision.
- [ ] The synthetic fixture exists without duplicate records after a repeat seed.

The automated isolated lifecycle proof uses disposable ports, credentials, containers, images, and volumes:

```bash
bash scripts/verify_docker_packaging.sh
```

It verifies missing-configuration failure, clean image builds, service health, non-root application users, migrations, restart behaviour, clean stop/start, and PostgreSQL volume persistence. It removes its isolated test environment when complete.

Stop the normal developer environment without deleting data:

```bash
docker compose down
```

Do not add `--volumes` unless local development data is deliberately being discarded.

## 6. Manual backend and frontend setup

The recommended first setup is Docker. To verify services separately, follow [development-setup.md](../development-setup.md).

Backend summary:

```bash
cd apps/api
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
alembic upgrade head
fastapi dev app/main.py
```

Frontend summary in a second terminal:

```bash
cd apps/web
npm ci
npm run dev
```

- [ ] `http://localhost:8000/docs` opens the generated FastAPI API documentation.
- [ ] `http://localhost:3000` opens the Next.js application.
- [ ] The frontend can reach FastAPI and the backend can reach PostgreSQL.

## 7. Database migration and synthetic seed data

For a host-run backend with a disposable development database:

```bash
cd apps/api
source .venv/bin/activate
alembic upgrade head
alembic current
SEED_DATA_ENABLED=true python -m app.database.seed
SEED_DATA_ENABLED=true python -m app.database.seed
```

- [ ] Both seed commands complete without creating an unintended duplicate.
- [ ] No real personal information, credential, or unlicensed article is loaded.
- [ ] Production seed loading remains disabled.

## 8. Automated verification

Backend:

```bash
cd apps/api
source .venv/bin/activate
ruff check .
ruff format --check .
pytest -m "not live_ai"
```

Frontend:

```bash
cd apps/web
npm ci
npm run lint
npm run format:check
npm run typecheck
npm test
npm run test:e2e
npm run build
```

Repository documentation and safety:

```bash
python3 scripts/scan_secrets.py
python3 scripts/verify_architecture_documentation.py
python3 scripts/verify_deployment_documentation.py
python3 scripts/verify_demonstration_package.py
python3 scripts/verify_technical_report.py
python3 scripts/verify_readme_documentation.py
python3 scripts/verify_handover_package.py
python3 scripts/verify_handover_clean_checkout.py
git diff --check
```

- [ ] Every executed command and its result are recorded in `reproducibility-results.md`.
- [ ] A skipped safety-gated or live-provider test is reported as skipped, not passed.
- [ ] A failed command is diagnosed, corrected, and rerun before it is marked complete.

## 9. Primary demonstration workflow

```bash
cd apps/web
npm ci
npm run demo
```

Open `http://127.0.0.1:3100` and follow the [demonstration script](../demonstration/demo-script.md). The printed account and approved URL are synthetic loopback fixtures.

- [ ] Sign in.
- [ ] Resolve the approved synthetic URL.
- [ ] select the synthetic article.
- [ ] generate the mocked LinkedIn draft.
- [ ] edit the draft.
- [ ] generate and regenerate the mocked illustration.
- [ ] preview and save the content.
- [ ] reopen it from the library.
- [ ] copy the edited text and download the illustration.
- [ ] delete the saved draft.
- [ ] stop the demonstration with `Ctrl+C`.

## 10. Documentation review

- [ ] The README matches the repository and contains valid local links.
- [ ] Architecture diagrams match implemented components and trust boundaries.
- [ ] API documentation explains the current endpoints and local OpenAPI routes.
- [ ] Deployment and operations documents describe proposed controls without claiming deployment.
- [ ] Source rights restrictions and fixture-only mode are explicit.
- [ ] Known limitations and unresolved risks remain visible.

## 11. Repeatability and final capture

Repeat the isolated handover verification and primary deterministic workflow after any setup correction. The second run must not depend on records created by the first run.

After NFA-90 is merged and local `main` is updated:

```bash
git switch main
git pull --ff-only origin main
git status --short --branch
git rev-parse HEAD
git tag --points-at HEAD
git ls-files docs/handover scripts/verify_handover_package.py scripts/verify_handover_clean_checkout.py
```

Record the final commit, pull request, tag status, test date, reviewer, and unresolved items in Jira and in the handover checklist.

