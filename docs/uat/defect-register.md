# NFA-81 UAT Defect Register

## Status

UAT has not started, so there are no confirmed participant defects yet. Do not treat earlier automated defects as UAT findings unless a participant independently encounters the same problem.

## Severity rules

| Severity | Meaning                                                                                                  |
| -------- | -------------------------------------------------------------------------------------------------------- |
| Critical | Security, privacy, destructive-action, or complete core-workflow failure that blocks release immediately |
| High     | A representative user cannot complete a core task and no safe workaround exists                          |
| Medium   | Important confusion or failure with a reasonable workaround                                              |
| Low      | Cosmetic, wording, or minor efficiency issue that does not prevent completion                            |

## Defect register

| UAT defect ID | Jira Bug    | Scenario | Participant codes affected | Summary          | Expected | Actual  | Severity | Owner   | Status      | Fix or decision | Retest ID |
| ------------- | ----------- | -------- | -------------------------- | ---------------- | -------- | ------- | -------- | ------- | ----------- | --------------- | --------- |
| None yet      | Pending UAT | Pending  | Pending                    | UAT not executed | Pending  | Pending | Pending  | Pending | Not started | Pending         | Pending   |

## Defect recording rules

- Reproduce the issue before classifying it as a confirmed software defect where possible.
- Keep raw participant confusion as a usability observation even when no software fault is found.
- Create a Jira Bug for every confirmed Critical or High defect.
- Link the Jira Bug to NFA-81 and the implementation issue that owns the affected feature.
- Store screenshots only when they contain synthetic data and no session cookie, password, or private information.
- Do not close a release-blocking defect until its fix is merged and the affected scenario is retested.
