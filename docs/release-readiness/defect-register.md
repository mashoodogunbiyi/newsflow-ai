# NFA-82 Release Defect Register

## Status

No unresolved Critical or High software defect is confirmed by the reviewed automated evidence at commit `29e94c69a1709ea3e78574869c6fdc712cd05241`.

This statement is limited to the evidence that exists. Human UAT has not run, so participant-discovered defects cannot yet be classified or ruled out.

## Severity policy

| Severity | Definition                                                                   | Release treatment                                     |
| -------- | ---------------------------------------------------------------------------- | ----------------------------------------------------- |
| Critical | Severe security, privacy, rights, or data-integrity failure                  | Blocks every affected release immediately             |
| High     | Primary workflow or important protection is unusable with no safe workaround | Blocks the affected release until fixed and retested  |
| Medium   | Significant issue with a reasonable safe workaround                          | Reviewer decides and records ownership before release |
| Low      | Minor issue that does not block the agreed MVP                               | May be accepted with an owner and target condition    |

## Open confirmed defects

| Defect ID      | Jira Bug | Severity | Summary                                                         | Affected scope    | Owner             | Status         | Retest evidence |
| -------------- | -------- | -------- | --------------------------------------------------------------- | ----------------- | ----------------- | -------------- | --------------- |
| None confirmed | None     | None     | No open confirmed software defect in current automated evidence | Reviewed baseline | Pending human UAT | No open defect | Not applicable  |

## Resolved evidence reviewed

| Defect                                               | Severity                            | Resolution                                                  | Evidence                                                                |
| ---------------------------------------------------- | ----------------------------------- | ----------------------------------------------------------- | ----------------------------------------------------------------------- |
| NFA77-DEF-01 - Missing frontend save control         | High workflow gap before correction | Added the authenticated save gateway and library redirect   | `docs/integration-e2e-testing.md` and complete Playwright journey       |
| NFA80-A11Y-01 - Source-link accessible-name mismatch | Serious accessibility finding       | Corrected the accessible name and added regression coverage | `docs/performance-accessibility-verification.md` and browser axe checks |

## Evidence gaps and accepted limitations

These are not recorded as confirmed software defects:

- Human UAT is not executed. This is a production acceptance blocker and may reveal defects.
- Human VoiceOver review is pending.
- Staging PostgreSQL, Lighthouse, object-storage, backup, and recovery evidence is pending.
- Forgotten-password functionality is outside the current agreed MVP and remains a product backlog item.
- Live CNN access is intentionally disabled because authorisation is absent.

Any newly confirmed Critical or High finding must receive a Jira Bug, an owner, a fix or explicit No-Go decision, and successful retest evidence before the affected release can proceed.
