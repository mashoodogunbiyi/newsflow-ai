# NewsFlow AI Frontend

The NewsFlow AI frontend is a Next.js, React, TypeScript, and Tailwind CSS application. It is located in `apps/web` and provides the user-facing layer of the project. NFA-17 adds automated linting, formatting, type checking, and component testing.

The current NFA-12 foundation contains a responsive homepage and uses original static demonstration content. It does not retrieve live CNN information, call the OpenAI API, or connect to the planned backend.

## Requirements

- Node.js 20.19 or later.
- npm 11 or a compatible npm release.

## Local development

From the repository root:

```bash
cd apps/web
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in a browser.

## Run with Docker Compose

NFA-16 adds a frontend development image and runs it with FastAPI and PostgreSQL from the repository-root `compose.yaml` file. From the repository root:

```bash
cp .env.example .env
docker compose up --build
```

Open [http://localhost:3000](http://localhost:3000). Browser requests use `NEXT_PUBLIC_API_BASE_URL`, while future server-side frontend requests can use the Docker network address `http://backend:8000`. Use `docker compose down` for a normal shutdown. See the [complete Docker development guide](../../infrastructure/docker/README.md) for all commands and service checks.

## Quality checks

NFA-17 uses ESLint with the Next.js Core Web Vitals and TypeScript rules, Prettier for formatting, TypeScript for static type checking, and Vitest with React Testing Library and jsdom for component tests.

```bash
npm run lint
npm run format:check
npm run typecheck
npm test
npm run build
```

To apply Prettier formatting instead of checking it:

```bash
npm run format
```

For a test watcher during development:

```bash
npm run test:watch
```

The baseline component test renders the homepage and checks its primary heading and fixture-mode status. It uses synthetic interface content and makes no network or paid API calls.

To serve the production build locally after a successful build:

```bash
npm run start
```

## Project structure

```text
apps/web/
├── .dockerignore          # Files excluded from the image build context
├── .prettierignore        # Files excluded from formatting checks
├── Dockerfile             # Next.js development image
├── __tests__/
│   └── page.test.tsx      # Basic homepage component test
├── app/
│   ├── globals.css          # Tailwind import and global design tokens
│   ├── layout.tsx           # Root layout, fonts, and metadata
│   └── page.tsx             # NewsFlow AI homepage
├── components/
│   ├── brand-mark.tsx       # Reusable project identity
│   ├── product-preview.tsx  # Fixture-mode product demonstration
│   └── workflow-step.tsx    # Reusable workflow item
├── public/                  # Static assets
├── eslint.config.mjs        # Next.js and TypeScript linting
├── next.config.ts           # Next.js and Tailwind build configuration
├── package.json             # Frontend scripts and dependencies
├── package-lock.json        # Reproducible npm dependency versions
├── postcss.config.mjs       # Tailwind CSS PostCSS integration
├── prettier.config.mjs      # Frontend formatting configuration
├── tsconfig.json            # Strict TypeScript configuration
└── vitest.config.mts        # Frontend unit-test configuration
```

Add future routes under `app` and shared interface elements under `components`. Add a `lib` directory only when frontend utilities or typed API clients are introduced.

## Configuration and security

- Keep real secrets in the repository-root `.env`, which Git ignores.
- Never expose `OPENAI_API_KEY` through a `NEXT_PUBLIC_` environment variable.
- The browser will call the NewsFlow AI backend. The backend will own OpenAI, database, and future authorised-source credentials.
- `NEWS_SOURCE_MODE` remains `fixture` until the live-source No-Go decision is formally replaced.

The production dependency audit completed with no known vulnerabilities on 23 October 2026. NFA-17 updated Next.js and its matching ESLint configuration from 16.4.0 to 16.4.2 to resolve the critical advisories found during the quality-tool setup. The complete development audit still reports a transitive `braces` advisory through `eslint-config-next`; npm does not provide a compatible non-breaking fix. Track the upstream dependency and do not use the suggested forced downgrade because it would make the Next.js toolchain inconsistent.

The project uses ESLint 10, which Next.js 16.4 supports. Some plugins bundled by `eslint-config-next` have not yet added ESLint 10 to their peer-version declarations, so npm can display peer dependency warnings during a clean install. The installed configuration has been verified with `npm run lint` under both the local runtime and the Node 20 Docker image. Do not enable `legacy-peer-deps` or suppress the warnings globally; remove this note when the upstream plugin declarations are updated.

The production build uses Next.js's supported Webpack option with Tailwind's official PostCSS plugin. Local development continues to use the standard `next dev` command.
