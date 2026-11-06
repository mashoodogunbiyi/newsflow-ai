# NewsFlow AI Demonstration Package

## 1. Purpose

This package provides a safe, repeatable portfolio demonstration of NewsFlow AI. It shows implemented functionality, explains the engineering decisions behind it, and keeps the demonstration inside the approved local, synthetic-data boundary.

The primary demonstration does not need CNN access, an OpenAI key, PostgreSQL, or Docker. It runs the real Next.js interface against a deterministic local mock API so the user journey remains available when a network or paid provider is unavailable.

## 2. Audience

The intended audience is:

- a supervisor reviewing project progress;
- a software engineering interviewer or portfolio reviewer;
- a developer joining the project; and
- a technical reviewer assessing architecture, security, testing, and responsible AI controls.

The audience is assumed to understand ordinary web applications but does not need prior knowledge of NewsFlow AI.

## 3. Objectives

By the end of the demonstration, the reviewer should understand:

1. the problem NewsFlow AI solves;
2. the implemented article-to-content user journey;
3. how Next.js, FastAPI, PostgreSQL, private image storage, and OpenAI fit together;
4. how authentication, ownership, source rights, grounding, image safety, and human review are enforced;
5. how deterministic tests avoid live CNN data and paid OpenAI calls; and
6. which production and source-rights limitations remain open.

## 4. Recommended demonstration mode

Use the deterministic local mode for a reliable presentation.

### 4.1 Prerequisites

- Node.js 20.19 or later.
- npm dependencies installed with `npm ci`.
- Ports 3100 and 4100 available on the presenter's computer.

### 4.2 Start the demonstration

From the repository root:

```bash
cd apps/web
npm ci
npm run demo
```

Wait for `NewsFlow AI demonstration is ready`, then open:

```text
http://127.0.0.1:3100
```

Use this mock-only account:

```text
Email: owner@example.com
Password: TestPassword123!
```

Use this approved synthetic article URL:

```text
https://example.invalid/newsflow/synthetic-clean-energy
```

The credentials are deliberately public test fixtures accepted only by the local mock API on `127.0.0.1`. They are not application, database, OpenAI, or production credentials.

Stop both services by pressing `Ctrl+C` in the terminal that runs the demonstration.

## 5. Demonstration data and isolation

The deterministic environment contains:

- two synthetic identities used for ownership tests;
- one fictional technology article with invented metadata;
- a mocked LinkedIn draft;
- mocked generated-image bytes;
- in-memory saved-draft state that resets whenever `npm run demo` starts; and
- no real user, CNN, LinkedIn, database, storage-provider, or OpenAI data.

The mock API binds to `127.0.0.1:4100`, and the demonstration frontend binds to `127.0.0.1:3100`. The command does not make a CNN or OpenAI request.

## 6. Demonstration materials

| Material | Purpose |
| --- | --- |
| [Presenter script](demo-script.md) | Timed, step-by-step application and architecture walkthrough |
| [Rehearsal checklist](rehearsal-checklist.md) | Preflight, workflow, safety, and closeout checks |
| [Fallback plan](fallback-plan.md) | Recovery paths for local, provider, network, and presentation failures |
| [Evidence record](evidence.md) | Verified commands, screenshots, test results, and remaining manual work |
| [System architecture](../architecture/system-architecture.md) | Components, boundaries, and external-service status |
| [Data flows](../architecture/data-flow.md) | Article, text, image, persistence, export, and recovery flows |
| [Screenshot manifest](../screenshots/README.md) | Safe screenshots and their deterministic recreation command |

## 7. Optional integrated Docker mode

The Docker environment demonstrates the real FastAPI and PostgreSQL integration. It is useful for an engineering explanation, but it is not the default presentation because it requires more local configuration and may depend on live OpenAI availability for generation.

From the repository root:

```bash
docker compose up --build --detach --wait
docker compose ps
```

Open `http://localhost:3000`, register a new local demonstration account, and use the same synthetic URL shown above. Stop the stack with:

```bash
docker compose down
```

Never display the `.env` file, terminal environment, provider dashboards, or real credentials during a demonstration. If live generation is used, state clearly that it is a metered external API response. If it fails, use the deterministic mode and identify the output as mocked.

## 8. Scope and limitations

- Live CNN integration is not authorised and remains disabled.
- An arbitrary pasted URL is not downloaded or scraped. It must match an article already stored in the rights-approved catalogue.
- AI output requires human review and may contain mistakes.
- Generated images are conceptual illustrations, not authentic event photographs.
- The application does not publish directly to LinkedIn.
- The deterministic demonstration proves the implemented user interface and contracts, not production hosting or provider availability.
- Public production release, real users, and commercial use remain No-Go.

## 9. Completion rule

NFA-88 is technically ready for owner review when:

1. the demonstration package verification passes;
2. the deterministic browser journey passes;
3. the screenshot evidence can be recreated;
4. a presenter completes the manual rehearsal checklist; and
5. the project owner records approval or changes in Jira.

