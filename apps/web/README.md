# NewsFlow AI Frontend

The NewsFlow AI frontend is a Next.js, React, TypeScript, and Tailwind CSS application. It is located in `apps/web` and provides the user-facing layer of the project.

The current NFA-12 foundation contains a responsive homepage and uses original static demonstration content. It does not retrieve live CNN information, call the OpenAI API, or connect to the planned backend.

## Requirements

- Node.js 20.9 or later.
- npm 11 or a compatible npm release.

## Local development

From the repository root:

```bash
cd apps/web
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in a browser.

## Quality checks

```bash
npm run lint
npm run build
```

To serve the production build locally after a successful build:

```bash
npm run start
```

## Project structure

```text
apps/web/
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
└── tsconfig.json            # Strict TypeScript configuration
```

Add future routes under `app` and shared interface elements under `components`. Add a `lib` directory only when frontend utilities or typed API clients are introduced.

## Configuration and security

- Keep real secrets in the repository-root `.env`, which Git ignores.
- Never expose `OPENAI_API_KEY` through a `NEXT_PUBLIC_` environment variable.
- The browser will call the NewsFlow AI backend. The backend will own OpenAI, database, and future authorised-source credentials.
- `NEWS_SOURCE_MODE` remains `fixture` until the live-source No-Go decision is formally replaced.

The production dependency audit completed with no known vulnerabilities on 12 October 2026. The complete development audit currently reports a transitive `braces` advisory through `eslint-config-next`; npm did not provide a compatible non-breaking fix at setup time. Track the upstream dependency and do not use a forced downgrade that would make the Next.js toolchain inconsistent.

The production build uses Next.js's supported Webpack option with Tailwind's official PostCSS plugin. Local development continues to use the standard `next dev` command.
