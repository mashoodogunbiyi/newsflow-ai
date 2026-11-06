# NewsFlow AI Demonstration Rehearsal Checklist

## 1. Rehearsal details

Complete one copy of this table for each manual rehearsal.

| Field | Value |
| --- | --- |
| Presenter | Pending |
| Date and time | Pending |
| Commit or pull request | Pending |
| Computer and browser | Pending |
| Demonstration mode | Deterministic mock / integrated Docker |
| Result | Pending |
| Notes or defects | Pending |

The automated browser rehearsal is recorded separately in [evidence.md](evidence.md). It does not replace a narrated human rehearsal.

## 2. Preflight

- [ ] The repository is on the intended reviewed commit.
- [ ] No `.env`, API key, password manager, private email, or unrelated browser tab is visible.
- [ ] Node.js and frontend dependencies are available.
- [ ] Ports 3100 and 4100 are free.
- [ ] `npm run demo` reaches the ready message.
- [ ] The homepage opens at `http://127.0.0.1:3100`.
- [ ] Architecture and fallback documents are open in separate tabs.
- [ ] The presenter has clearly identified the demonstration as synthetic and local.
- [ ] Screen sharing shows only the intended window.

## 3. Main journey

- [ ] Sign in with the mock-only account.
- [ ] Show the protected dashboard and navigation.
- [ ] Paste the approved synthetic article URL.
- [ ] Review the source and attribution.
- [ ] Explain the approved-catalogue boundary and no-scraping rule.
- [ ] Choose tone, language, and length.
- [ ] Generate the mocked LinkedIn draft.
- [ ] Edit the text and show the live preview.
- [ ] Generate the mocked illustration.
- [ ] Explain image safety and AI designation.
- [ ] Save the draft to the private library.
- [ ] Reopen the saved draft.
- [ ] Show version information.
- [ ] Copy the edited text.
- [ ] Download the selected illustration.
- [ ] Explain owner-scoped access.
- [ ] Show one controlled error or describe the tested provider-failure state.

## 4. Technical explanation

- [ ] Explain Next.js and React as the frontend.
- [ ] Explain FastAPI as the backend and security boundary.
- [ ] Explain PostgreSQL as persistent relational storage.
- [ ] Explain private image storage.
- [ ] Explain the backend-only OpenAI service boundary.
- [ ] Explain mocked provider responses in the deterministic demonstration.
- [ ] Explain migrations, Docker, tests, and CI.
- [ ] Explain source grounding and human review.

## 5. Safety and accuracy

- [ ] Do not say that NewsFlow AI has live CNN access.
- [ ] Do not describe the synthetic article as real reporting.
- [ ] Do not describe mocked AI output as a live API response.
- [ ] Do not claim that the application publishes to LinkedIn.
- [ ] Do not claim production readiness, full WCAG conformance, or completed human UAT.
- [ ] Keep credentials, session identifiers, private data, and environment values hidden.
- [ ] Identify generated images as conceptual AI illustrations.

## 6. Fallback readiness

- [ ] The four repository screenshots open correctly.
- [ ] The architecture diagram renders correctly.
- [ ] The presenter knows how to restart `npm run demo`.
- [ ] The presenter knows when to switch from integrated mode to deterministic mode.
- [ ] The presenter can explain any fallback without presenting it as a live result.

## 7. Closeout

- [ ] Stop the demonstration with `Ctrl+C`.
- [ ] Confirm ports 3100 and 4100 are no longer serving the application.
- [ ] Record every unexpected behaviour in Jira.
- [ ] Update [evidence.md](evidence.md) with the rehearsal result.
- [ ] Repeat the rehearsal after any material workflow change.
- [ ] Obtain project-owner approval before treating NFA-88 as Done.

