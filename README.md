# NewsFlow AI

NewsFlow AI is a planned full-stack application that turns authorised CNN International news information into original, source-grounded LinkedIn posts and accompanying AI-generated illustrations.

> Status: planning and discovery. NFA-3 through NFA-8 are complete and approved. ADR-001 records a No-Go decision for live CNN integration and a Go decision for development with original synthetic fixtures under the approved safeguards.

## Product workflow

1. Discover recent CNN articles through an authorised source.
2. Let a signed-in user filter and select an article.
3. Build a bounded fact pack from the permitted source fields.
4. Generate a LinkedIn post for the chosen tone, length, and audience.
5. Generate an original, LinkedIn-suitable illustration.
6. Let the user review, edit, regenerate, save, copy, and download the result.

Direct LinkedIn publishing, other news sources, video generation, payments, and social analytics are outside the first release.

## Planned architecture

| Layer | Planned technology | Responsibility |
|---|---|---|
| Web | Next.js, React, TypeScript, Tailwind CSS | Authentication screens, news dashboard, generation controls, editor, and preview |
| Backend API (our application) | FastAPI, Python | Business logic, validation, authorisation, orchestration, and REST endpoints |
| Data | PostgreSQL | Users, permitted article metadata, source lineage, generations, and saved posts |
| Queue/scheduler | Lightweight worker selected during implementation | Authorised news synchronisation and long-running generation work |
| External AI API | OpenAI API, called with the official Python SDK | LinkedIn post generation through the Responses API and original image generation |
| Object storage | S3-compatible storage; local adapter for development | Generated image assets |
| Delivery | Docker Compose and GitHub Actions | Reproducible local setup, tests, and release checks |

### FastAPI and the OpenAI API are different

- **FastAPI** is the Python framework we will use to build NewsFlow AI's own backend API. It will receive requests from the website, authenticate users, read and write the database, validate source facts, and coordinate external services.
- **The OpenAI API** is the external AI service that our FastAPI backend will call. We will use its Responses API to generate structured LinkedIn drafts and its image-generation capability to create original illustrations.
- **The OpenAI Python SDK** is the library used inside the FastAPI application to make those OpenAI API requests. Python is the implementation language; it is not a replacement for the OpenAI API.

```text
Next.js website
      |
      v
Our FastAPI backend
      |
      +----> Authorised CNN source
      |
      +----> OpenAI API
               |-- Responses API: LinkedIn post
               `-- Image generation: illustration
```

All OpenAI calls will therefore run on our backend. The `OPENAI_API_KEY` will be loaded from a server-side environment variable or secret manager and will never be sent to the browser or committed to the repository. This follows the [official OpenAI API guidance](https://developers.openai.com/api/reference/overview).

## Planning documents

- [PROJECT_PLAN.md](PROJECT_PLAN.md) - end-to-end delivery plan organised as Epics and Tasks.
- [PROJECT_MANAGEMENT.md](PROJECT_MANAGEMENT.md) - Jira setup, workflow, issue templates, roadmap, and operating rules.
- [docs/jira/NFA-3.md](docs/jira/NFA-3.md) - functional and non-functional requirements baseline with measurable acceptance criteria.
- [docs/jira/NFA-4.md](docs/jira/NFA-4.md) - research and recommendation for authorised CNN data access.
- [docs/jira/NFA-5.md](docs/jira/NFA-5.md) - authorisation decision, current restrictions, and supporting evidence record.
- [docs/jira/NFA-6.md](docs/jira/NFA-6.md) - approved fixture-first source data contract covering required fields, validation, missing information, attribution, provenance, refresh, and retention.
- [docs/jira/NFA-7.md](docs/jira/NFA-7.md) - approved privacy, copyright, hallucination, and AI-generated image risk review with mandatory safeguards and release gates.
- [docs/jira/NFA-8.md](docs/jira/NFA-8.md) - approved architecture decision recording No-Go for live CNN integration and Go for fixture-based development.

### Documentation update rule

The README is the running written record of the project's progress. Whenever a project Markdown document or NFA deliverable is added or modified, the same change must update this README to:

- Link to the new or modified document where appropriate.
- Explain what work was completed or changed.
- Update the current project status and next step when affected.

The README and the related project document should be staged and committed together so the repository history remains understandable.

## Intended repository layout

```text
newsflow-ai/
├── apps/
│   ├── api/                 # FastAPI application
│   └── web/                 # Next.js application
├── packages/                # Shared schemas or generated API client
├── infrastructure/          # Docker and deployment configuration
├── docs/                    # Architecture decisions, API notes, and reports
├── tests/                   # Cross-service and end-to-end tests
├── README.md
├── PROJECT_PLAN.md
└── PROJECT_MANAGEMENT.md
```

The layout is a target, not a claim about files that already exist.

## Key delivery gates

- **CNN access gate:** document a written, authorised feed, API, licensed service, or other permitted route before connecting the ingestion service to live CNN content. CNN International Commercial provides a route for licensing enquiries, and its published terms restrict unapproved reuse.
- **Grounding gate:** a post cannot be generated when the source fact pack is insufficient. Every factual claim must be traceable to the selected article data.
- **Safety gate:** generated imagery must not copy CNN photographs or branding, and sensitive stories must use non-deceptive illustration treatment with appropriate AI-generated labelling.
- **Release gate:** automated tests, security checks, user acceptance tests, documentation, and a rollback procedure must pass before release.

## Technical references

- [OpenAI API overview](https://developers.openai.com/api/reference/overview)
- [OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses)
- [OpenAI image generation](https://developers.openai.com/api/docs/guides/tools-image-generation)
- [OpenAI production best practices](https://developers.openai.com/api/docs/guides/production-best-practices)
- [CNN International Commercial terms](https://commercial.cnn.com/terms-of-use/)
- [CNN International Commercial contact](https://commercial.cnn.com/contact-us/)

## Current next step

Review the approved [NFA-8 Architecture Decision Record](docs/jira/NFA-8.md) and record its GitHub evidence in Jira. ADR-001 formally blocks live CNN integration while allowing the fixture-backed product and engineering work to continue.

After NFA-8 is recorded as Done in Jira, continue to NFA-9 - Create the initial risk register.

## Licence

No software licence has been selected yet. Add one before public distribution.
