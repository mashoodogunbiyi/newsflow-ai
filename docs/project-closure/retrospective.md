# NewsFlow AI Project Retrospective

## 1. Purpose

This retrospective reviews how NewsFlow AI was planned and delivered. It records actual project experiences from the Jira, Git, implementation, test, documentation and local-environment workflow.

## 2. What went well

### 2.1 Structured project management

- The 10-Epic Jira structure turned a broad idea into smaller outcomes covering discovery, foundations, data, AI, frontend, quality and delivery.
- Jira issue identifiers in branch names, commit messages and evidence comments made the work traceable.
- Feature branches and pull requests provided repeated practice with collaborative Git workflows even during a solo phase.

### 2.2 Rights-first decision making

- The project investigated CNN access before enabling ingestion.
- The absence of authorisation produced an explicit No-Go rather than unauthorised scraping.
- The provider interface and synthetic fixtures allowed engineering to continue safely.

### 2.3 Incremental engineering

- PostgreSQL, FastAPI, Next.js and Docker were introduced as separate, understandable services.
- Authentication and ownership were established before private content features expanded.
- Provider fakes allowed text and image workflows to be built without unreliable or billable live calls.

### 2.4 Automated quality

- Tests grew with each feature across backend, frontend, database and browser layers.
- CI caught contract drift, including an outdated article-pipeline expectation after an intentional `generation` response field was added.
- Browser tests exercised a complete synthetic user journey rather than only isolated components.
- Security, reliability, performance, accessibility and documentation received executable checks.

### 2.5 Documentation and learning

- The README was updated alongside new implementation and documentation.
- Architecture, deployment, demonstration, report and handover packages made the project understandable beyond the source code.
- Repeated explanation of frontend, backend, database, virtual environments, `.env`, Docker, branches, commits and pull requests improved the developer's ability to explain the system.

## 3. What was difficult

### 3.1 Scope size

The original three-sprint, six-week shape was too ambitious for one developer. The project eventually required many Jira tasks and 82 pull requests before closure. Protecting rights, security and evidence was correct, but the breadth increased coordination and documentation overhead.

### 3.2 Source authorisation

The intended live CNN feature could not be delivered legally because written permission was unavailable. This created a permanent difference between the original product vision and the safe portfolio implementation.

### 3.3 Local environment understanding

It took time to understand that the frontend, backend and PostgreSQL are separate services; that Python `.venv` is unrelated to the Node.js frontend; and that Docker may preserve old database credentials in a named volume after `.env` changes.

### 3.4 Authentication and ownership

Secure sessions, HTTP-only cookies, CSRF, password hashing, expiry and cross-user object protection required more design and testing than a basic login form suggests.

### 3.5 External-service reliability

OpenAI, article sources and private storage can fail independently. Deterministic fakes, timeouts, retries, idempotency, recovery and no-duplicate paid calls required explicit design.

### 3.6 Evolving contracts and CI

API responses evolved as useful functionality was added. One GitHub Actions pipeline failed because an isolated test still expected the older response shape. The correct resolution was to confirm that the new field was intentional and update the outdated expectation without weakening the assertion.

### 3.7 Browser and Docker process isolation

Local test servers, ports and Docker state introduced environment-specific failures. Clean CI-mode browser servers and isolated Compose project names made the final checks repeatable.

## 4. What could be improved

### 4.1 Re-scope earlier

After the CNN No-Go decision, the project plan should have been formally re-baselined immediately from live CNN product to provider-neutral synthetic portfolio application. This would have reduced later ambiguity in Epic names and release criteria.

### 4.2 Deliver one vertical slice sooner

A smaller early path - register, select one synthetic article, generate one mocked draft and save it - would have demonstrated the architecture before expanding every layer.

### 4.3 Keep the project plan current

The original plan remained labelled planning while implementation advanced. Future projects should update plan status, accepted scope changes and completed outcomes at every Epic review, not only at closure.

### 4.4 Separate technical completion from acceptance

Prepared UAT documents are not executed UAT. Future planning should schedule participants, screen-reader review and owner sign-off as named activities with dates and owners.

### 4.5 Prioritise user account recovery earlier

The missing forgotten-password journey was discovered through use of the interface. A future user-facing authentication Epic should decide account recovery during requirements work rather than defer it implicitly.

### 4.6 Reduce documentation duplication

The project has strong evidence but many overlapping documents. A future project should maintain one evidence index and generate summary views where practical.

### 4.7 Automate closure evidence earlier

Repository contract and clean-checkout verifiers were added late. Future work should create documentation, secret, reproducibility and evidence checks during the engineering-foundation Epic.

## 5. Lessons learned

1. Permission and technical feasibility are different decisions.
2. Safe re-scoping is better than quietly bypassing a blocked dependency.
3. PostgreSQL persistence, backend logic and frontend presentation need separate mental models and tests.
4. A feature is not complete because the page renders; data ownership, failures, accessibility and recovery matter.
5. Branches organise work, commits preserve changes and pull requests provide review and merge evidence.
6. Test failures should be diagnosed against the current contract rather than patched until green.
7. Mocked external providers make routine CI reliable, private and affordable.
8. Docker improves reproducibility but does not create production security by itself.
9. Automated accessibility and UAT preparation do not replace human review.
10. Closure can be honest and successful while still recording limitations and future work.

## 6. Achievements to carry forward

- Practical Jira Epic, task, sprint and evidence workflow.
- Git branching, commit, pull request, merge and synchronisation experience.
- Full-stack TypeScript and Python integration.
- PostgreSQL schema and migration design.
- Secure authentication and owner-scoped API work.
- Provider abstraction, data normalisation, deduplication and provenance.
- AI prompting, grounding, image safety and provider failure handling.
- Docker, CI, automated tests, technical writing and portfolio presentation.

## 7. Recommended next phase

Do not continue the closed project as an undefined stream of additions. If work resumes, create a new phase with a small outcome, owner, dates, acceptance criteria and release boundary. The strongest candidates are:

1. secure password reset;
2. representative human UAT and VoiceOver review;
3. an authorised non-CNN provider proof, if permission is available; or
4. deployment to an approved private staging environment with managed secrets, storage, monitoring and backups.

## 8. Retrospective conclusion

NewsFlow AI succeeded as a substantial portfolio and learning project. Its strongest result is not a claim of production readiness; it is the combination of working software, rights-aware re-scoping, security controls, broad automated evidence, clear limitations and a reproducible handover.

