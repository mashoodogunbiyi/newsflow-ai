# NFA-81 User Acceptance Testing Plan

## 1. Purpose and current status

NFA-81 verifies whether representative users can understand and complete the NewsFlow AI MVP workflow using synthetic articles and controlled AI responses.

This package is prepared and technically rehearsed. Human UAT execution has not yet occurred, so the product acceptance decision is **Pending**. No participant result, usability finding, defect, retest, or approval may be marked complete until the corresponding evidence has actually been recorded.

## 2. UAT objectives

The UAT sessions will determine whether representative users can:

- sign in without assistance;
- find and filter an appropriate synthetic article;
- understand the selected source, attribution, and fixture-data notice;
- configure and request a LinkedIn draft;
- understand that generated content requires human review and is not automatically published;
- edit the draft and understand the combined preview;
- generate, regenerate, compare, and select an AI illustration;
- save and reopen private content;
- copy the current edited text and download the selected illustration;
- delete saved content deliberately; and
- understand representative validation and provider-failure messages.

UAT evaluates user understanding and usability. Automated tests remain the evidence for technical correctness, security controls, and detailed edge cases.

## 3. Scope

### In scope

- Authentication using local synthetic test accounts.
- Synthetic article browsing, search, category filtering, and selection.
- Source and attribution review.
- Mocked LinkedIn draft and image generation.
- Draft editing and LinkedIn-style preview.
- Image regeneration and version selection.
- Saving, reopening, copying, downloading, and deleting content.
- Controlled error messages and recovery.
- Navigation clarity, labels, instructions, and overall confidence.

### Out of scope

- Live CNN content or CNN authorisation.
- Live OpenAI requests or assessment of live-model creativity.
- Automatic or manual publishing to LinkedIn.
- Production hosting, production accounts, production storage, or production monitoring.
- Penetration, load, disaster-recovery, or complete accessibility conformance testing.
- Forgotten-password functionality, which remains a separate product backlog item.

## 4. Participants

Use three to five participants for the MVP. Use participant codes instead of names in committed records.

| Code | Representative profile                                    | Why included                                        | Status        |
| ---- | --------------------------------------------------------- | --------------------------------------------------- | ------------- |
| P01  | Professional who creates or reviews LinkedIn posts        | Represents the main content-creation user           | Not recruited |
| P02  | Communications, marketing, or editorial reviewer          | Evaluates source clarity, review controls, and tone | Not recruited |
| P03  | General professional with limited content-tool experience | Evaluates learnability without specialist knowledge | Not recruited |
| P04  | Optional keyboard or assistive-technology user            | Provides additional accessibility feedback          | Not recruited |
| P05  | Optional small-business or project stakeholder            | Evaluates usefulness and MVP fit                    | Not recruited |

Do not record names, private account information, employer details, or unrelated personal information. Record only participant code, broad experience band, test device and browser, session date, and consent to use anonymised feedback.

## 5. Roles

| Role             | Responsibility                                                                                              |
| ---------------- | ----------------------------------------------------------------------------------------------------------- |
| UAT coordinator  | Prepare the environment, assign participant codes, protect test data, and retain the evidence package       |
| Moderator        | Read the neutral introduction, observe without leading, record assistance and comments, and reset data      |
| Participant      | Attempt tasks, think aloud where comfortable, and provide honest feedback                                   |
| Product reviewer | Review results and defects, decide whether blocking issues are resolved, and record the acceptance decision |
| Developer        | Investigate confirmed defects, link code changes and pull requests, and provide retest evidence             |

Mashood Ogunbiyi is the initial UAT coordinator. The final product reviewer must be recorded in the acceptance document before sign-off.

## 6. Controlled environment

The UAT environment reuses the deterministic NFA-77 and NFA-80 browser contract mock. It binds only to `127.0.0.1`, uses synthetic users and articles, returns controlled draft and image responses, and makes no CNN or OpenAI request.

### Prerequisites

- Node.js and npm versions supported by `apps/web/README.md`.
- Frontend dependencies installed with `npm ci`.
- Chromium, Safari, or another approved local browser.
- No real `OPENAI_API_KEY`, database password, or production credential in the terminal.

### Start the environment

From the repository root, build the reviewed frontend:

```bash
cd apps/web
npm ci
npm run build
```

In terminal 1:

```bash
cd apps/web
node e2e/support/mock-api.mjs
```

In terminal 2:

```bash
cd apps/web
API_INTERNAL_BASE_URL=http://127.0.0.1:4100 \
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:4100 \
npm run start -- --hostname 127.0.0.1 --port 3100
```

Open `http://127.0.0.1:3100/login`.

### Local test account

```text
Email: owner@example.com
Password: TestPassword123!
```

These credentials work only against the local deterministic mock. They must never be reused for a real service.

### Reset between participants

Run this from a moderator terminal before each participant starts:

```bash
curl -X POST http://127.0.0.1:4100/__test/reset
```

Then use a fresh private browser window or clear the localhost site data. The reset removes mock drafts and controlled failure state. It does not touch PostgreSQL or production data.

### Controlled provider-error setup

For the provider-failure part of UAT-15, the moderator runs:

```bash
curl -X POST http://127.0.0.1:4100/__test/generation-failure
```

Run that scenario last, then reset the environment before the next participant.

### Stop the environment

Press `Ctrl+C` in terminal 2 and terminal 1. Do not type the words `Control-C` as a terminal command.

## 7. Test data

| Data           | Controlled value                                           |
| -------------- | ---------------------------------------------------------- |
| User           | Synthetic `owner@example.com` account                      |
| Article        | Synthetic technology update for responsible AI testing     |
| Provider       | NewsFlow AI synthetic fixture                              |
| Source URL     | Reserved `example.invalid` address                         |
| Draft          | Deterministic AI-assisted text requiring human review      |
| Images         | Local one-pixel PNG fixtures with AI-generated designation |
| Storage        | In-memory mock state reset between participants            |
| External calls | None                                                       |

Participants must not enter real personal information, real unpublished business information, live news content, passwords used elsewhere, or confidential draft text.

## 8. Entry criteria

UAT may start only when:

- NFA-77 integration and end-to-end tests pass;
- NFA-78 grounding and content-safety evaluation is available;
- NFA-79 reliability tests pass;
- NFA-80 performance and accessibility verification is available;
- the UAT environment starts locally and the health and login journey work;
- the deterministic end-to-end suite passes, including image regeneration;
- participant instructions and consent wording are ready; and
- the coordinator has assigned unique participant codes.

## 9. Scenarios and evidence

The executable scenarios are in [the UAT test script](uat/test-script.md). Participants receive the neutral [participant instructions](uat/participant-instructions.md), while the moderator records results in [the execution record](uat/execution-record.md).

| Scenario group               | IDs              | Required evidence                                                   |
| ---------------------------- | ---------------- | ------------------------------------------------------------------- |
| Authentication and discovery | UAT-01 to UAT-04 | Completion, assistance, comments, actual result                     |
| Text and image creation      | UAT-05 to UAT-09 | Completion, comprehension, edited text preservation, version choice |
| Persistence and export       | UAT-10 to UAT-14 | Save, reopen, copy, download, and confirmed deletion result         |
| Error understanding          | UAT-15           | Safe message comprehension and recovery action                      |
| Overall acceptance           | UAT-16           | Questionnaire, confidence, blocking concern, recommendation         |

## 10. Session procedure

1. Assign a participant code and record only the permitted session metadata.
2. Explain that the application uses synthetic content and mocked AI output.
3. Explain that no content will be published and that generated material requires human review.
4. Obtain consent to record anonymised task results and comments.
5. Reset the mock and open a fresh private browser window.
6. Give the participant one task at a time without explaining where to click.
7. Record completion, time if desired, assistance, comments, observed confusion, and actual result.
8. Do not blame the participant or change a failed result to Pass after giving step-by-step help.
9. Administer the feedback questionnaire.
10. Classify confirmed defects and usability issues.
11. Reset the environment before the next participant.

## 11. Result rules

| Result                | Meaning                                                                                                                       |
| --------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| Pass                  | The participant completed the task and the expected result occurred without moderator intervention                            |
| Pass with observation | The task completed, but hesitation, one neutral clarification, or a non-blocking usability issue was recorded                 |
| Fail                  | The participant could not complete the task, required directed instructions, or the expected application result did not occur |
| Blocked               | Environment or earlier-scenario failure prevented a meaningful attempt                                                        |
| Not run               | The scenario has not been attempted                                                                                           |

Record the result that actually occurred. A successful automated test does not turn a participant's failed usability scenario into a UAT Pass.

## 12. Defect severity

| Severity | Definition                                                                                                    | Release treatment                              |
| -------- | ------------------------------------------------------------------------------------------------------------- | ---------------------------------------------- |
| Critical | Data exposure, destructive action without confirmation, security bypass, or complete loss of the core journey | Release blocked immediately                    |
| High     | A core scenario cannot be completed by a representative user and no safe workaround exists                    | Release blocked until fixed and retested       |
| Medium   | Important confusion or failure with a reasonable workaround                                                   | Product reviewer decides before acceptance     |
| Low      | Cosmetic, wording, or minor efficiency issue that does not prevent completion                                 | May be scheduled with an owner and target date |

Use the [defect register](uat/defect-register.md). Confirmed software defects should also become Jira Bug work items linked to NFA-81 and the affected implementation issue.

## 13. MVP acceptance thresholds

The product reviewer may record `Accepted` only when all of the following are true:

- at least three representative participants completed a recorded session;
- every participant attempted UAT-01 to UAT-15 unless a documented environment problem blocked the session;
- all participants completed the core create, edit, save, reopen, export, and delete journey after any approved retest;
- no Critical or High defect remains open;
- every confirmed release-blocking fix has a linked retest result;
- all participants understood that content is synthetic, requires human review, and is not automatically published;
- at least two of three participants, or at least 80 percent for a larger group, rated overall workflow clarity at 4 or 5 out of 5;
- unresolved Medium and Low issues have an owner, decision, and target date; and
- the product reviewer signs the acceptance record.

If any condition is not met, record `Rejected` or `Conditional` with the exact unmet conditions. Do not use `Accepted` because the implementation team expects it to pass.

## 14. Deliverables

- [UAT test script](uat/test-script.md)
- [Participant instructions](uat/participant-instructions.md)
- [Execution record](uat/execution-record.md)
- [Feedback questionnaire](uat/feedback-questionnaire.md)
- [Defect register](uat/defect-register.md)
- [Retest and acceptance record](uat/retest-and-acceptance.md)

## 15. Technical rehearsal record

The controlled environment was rehearsed on 5 November 2026 from branch `nfa-81-user-acceptance-testing`.

| Check                        | Result                                                                     |
| ---------------------------- | -------------------------------------------------------------------------- |
| Mock API JavaScript syntax   | Passed                                                                     |
| ESLint                       | Passed                                                                     |
| Prettier                     | Passed                                                                     |
| Strict TypeScript            | Passed                                                                     |
| Frontend component tests     | 167 passed across 35 files                                                 |
| Chromium end-to-end tests    | 13 passed, including regeneration and the complete saved-content lifecycle |
| Production JavaScript budget | Passed: 1,041,667 raw bytes and 326,988 gzip bytes across 42 files         |
| Project secret scan          | Passed                                                                     |

The browser result proves only that the controlled environment can support the planned sessions. It is not participant evidence and does not change the Pending acceptance decision.

## 16. Current decision

- Package status: Prepared and technically rehearsed.
- Participant execution: Not started.
- Confirmed UAT defects: None yet because UAT has not started.
- Retests: Not started.
- Acceptance decision: Pending.
- Jira recommendation: Keep NFA-81 In Progress or move it to Ready for UAT. Move it to Done only after the evidence and acceptance thresholds above are completed and reviewed.
