# NewsFlow AI Presenter Script

## 1. Target duration

Allow 12 to 15 minutes for the main demonstration and 5 minutes for questions.

Keep the [fallback plan](fallback-plan.md), [system architecture](../architecture/system-architecture.md), and four repository screenshots open in separate tabs before beginning.

## 2. Before the audience joins

1. Close any editor tab showing `.env` or credentials.
2. Run `npm run demo` from `apps/web`.
3. Open `http://127.0.0.1:3100` in a private browser window.
4. Confirm the terminal says the demonstration is using synthetic data and mocked AI responses.
5. Keep the terminal available, but do not display unrelated logs or environment variables.

## 3. Part 1 - Problem and solution

Open the homepage.

Say:

> NewsFlow AI is a review-first workspace for turning permitted news facts into an editable LinkedIn draft and an original conceptual illustration. It preserves attribution and human control instead of automatically publishing AI output.

Explain that the demonstration uses an original synthetic article. Live CNN access remains blocked because written permission has not been obtained.

## 4. Part 2 - Authentication and protected workspace

Select **Sign in** and enter the mock-only account:

```text
owner@example.com
TestPassword123!
```

After the dashboard opens, point out the signed-in identity and workspace navigation.

Explain:

- FastAPI is the authoritative authentication and business-logic boundary in the integrated application.
- Server-managed sessions use HTTP-only cookies.
- Drafts and images are owner scoped.
- The deterministic mode reproduces those HTTP contracts without storing a real account.

## 5. Part 3 - Article discovery and rights boundary

In **Search URL**, paste:

```text
https://example.invalid/newsflow/synthetic-clean-energy
```

Select **Use this article**.

Explain:

- the field performs an exact match against the approved catalogue;
- it does not scrape or download an arbitrary web page;
- the source panel shows permitted metadata and attribution before generation; and
- the article is fictional and exists only for development and demonstration.

Optional controlled-error example: return to the dashboard, enter `https://example.invalid/not-approved`, and show the safe not-in-catalogue message. Then use the valid synthetic URL again.

## 6. Part 4 - Configure and generate a LinkedIn draft

On the generation page:

1. Review the source title, attribution, and generation status.
2. Select a tone, such as **Professional**, **Conversational**, or **Analytical**.
3. Select **English**, **French**, or **Spanish**.
4. Select a post length.
5. Select **Generate LinkedIn draft**.

Explain:

- the integrated backend rechecks the session and source rights before contacting OpenAI;
- system instructions and untrusted article data are separated;
- generation uses permitted source fields rather than unrestricted page content;
- deterministic validation checks the response shape, length, source reference, and grounding warnings; and
- the local demonstration response is mocked, not a live OpenAI result.

## 7. Part 5 - Human editing and preview

When the draft appears:

1. Edit at least one sentence in **LinkedIn draft text**.
2. Show that the LinkedIn-inspired preview updates.
3. Point out source attribution, grounding status, character count, and review messaging.

Say:

> AI output is a draft, not a verified fact or finished publication. The user remains responsible for reviewing the source, claims, context, tone, and wording.

Nothing has been published or saved automatically.

## 8. Part 6 - Image generation and safety

Select **Generate image**. After the illustration appears, optionally select **Regenerate image** and compare the alternatives.

Explain:

- the prompt is constructed from permitted source information;
- sensitive-event and deceptive-photorealism rules are checked before generation;
- the result is designated as AI generated;
- the original is preserved when a regeneration fails; and
- integrated images are validated and stored privately before delivery.

The deterministic image is a tiny mocked PNG used to verify the workflow. Do not describe it as live provider output.

## 9. Part 7 - Save, reopen, copy, and download

1. Select **Save to library**.
2. Show the saved draft detail and version information.
3. Open **Library** from the navigation and reopen the saved draft if needed.
4. Select **Copy Post** and explain that the current edited text is copied only after user action.
5. Select **Download Image** and explain that the integrated endpoint checks ownership before returning private bytes.

Explain that a different authenticated user receives a non-disclosing not-found response for this private record. This is covered by the automated cross-user browser test.

Do not delete the draft during the main path unless deletion is part of the review. The automated end-to-end test also verifies confirmed deletion and the final empty state.

## 10. Part 8 - Architecture explanation

Open the [system architecture diagram](../architecture/system-architecture.md).

Explain the components in this order:

1. **Browser and Next.js** - accessible pages, server-side routes, and same-origin API gateways.
2. **FastAPI** - validation, authentication, authorisation, rights enforcement, orchestration, and safe errors.
3. **PostgreSQL** - users, sessions, article provenance and rights, generated content, versions, and audit evidence.
4. **Private image storage** - generated image bytes kept behind owner-authorised delivery endpoints.
5. **OpenAI APIs** - backend-only text and image service boundaries, mocked for routine tests and this demonstration.
6. **Article provider boundary** - synthetic provider implemented; live CNN adapter disabled and unauthorised.

Point out the internet, browser, application, database, provider, and storage trust boundaries.

## 11. Part 9 - Engineering evidence

Show the repository README or CI page and summarise:

- automated backend, frontend, browser, accessibility, security, and recovery tests;
- Alembic migrations and PostgreSQL integration tests;
- Docker packaging and health checks;
- structured logging without private prompt or credential content; and
- documentation contracts that prevent the portfolio claims from drifting away from the code.

Do not quote a test count unless it matches the current evidence record or the latest successful CI run.

## 12. Part 10 - Close honestly

Finish with:

> NewsFlow AI is ready for a controlled local demonstration with synthetic data. It is not approved for live CNN access or public production use. Open production work includes authorised source access, hosted private storage, managed secrets, monitoring, backups, human UAT, and final accessibility review.

Invite questions about API design, database relationships, security, testing, AI grounding, image safety, or the project-management workflow.

