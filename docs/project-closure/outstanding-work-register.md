# NewsFlow AI Outstanding Work Register

## 1. Purpose

This register transfers incomplete work and residual risks out of the active portfolio delivery without pretending they are complete. A future phase must create or retain Jira issues with owners and acceptance criteria before work starts.

## 2. Confirmed defect status

No unresolved Critical or High software defect is confirmed by the reviewed automated baseline. Two earlier findings were resolved: the missing frontend save control and a source-link accessible-name mismatch.

Human UAT has not run. Therefore, participant-discovered defects are unknown rather than zero.

## 3. Outstanding work

| ID | Category | Outstanding item | Priority or risk | Owner | Required before | Status and Jira treatment |
| --- | --- | --- | --- | --- | --- | --- |
| OW-01 | Rights | Obtain written authorisation and permitted-use terms for CNN or another approved provider | Critical | Product and compliance owner | Any live news integration | Open external dependency; retain or create rights task |
| OW-02 | Product acceptance | Run representative human UAT, record feedback, triage defects, retest and sign off | High | Product owner | Production acceptance | Open; NFA-81 must not be treated as executed UAT |
| OW-03 | Accessibility | Complete representative VoiceOver or equivalent assistive-technology review | High | Product and accessibility reviewer | Full accessibility claim | Open follow-up |
| OW-04 | Production security | Verify HTTPS, proxy, cookies, headers, managed secrets, shared limits and incident controls | Critical | Technical and security owner | Public deployment | Open production gate |
| OW-05 | Production data | Configure PostgreSQL backup, restore, retention, monitoring and data-protection controls | High | Technical and security owner | Production persistence | Open production gate |
| OW-06 | Private storage | Implement managed private object storage, inventory, cleanup scheduling and reconciliation | High | Technical owner | Production image storage | Open production gate |
| OW-07 | OpenAI operations | Approve production terms, model, privacy, budget, alerts, spending controls and emergency stop | High | Product, technical and security owner | Live provider calls outside private development | Open provider gate |
| OW-08 | Performance | Measure staging PostgreSQL, network, storage, Lighthouse and representative device workloads | High | Technical owner | Public performance claim | Open staging gate |
| OW-09 | Account recovery | Design and implement secure forgotten-password workflow | Medium | Product and technical owner | User-facing account service | Open product feature |
| OW-10 | Demonstration | Complete narrated rehearsal or approved recording and record owner acceptance | Medium | Project owner | External portfolio presentation where required | Prepared, manual completion pending |
| OW-11 | Release process | Select versioning and create a release tag if a distributable release is required | Medium | Project owner | Formal release distribution | No tag currently exists |
| OW-12 | Licensing | Select and document a software licence | Medium | Project owner | Any intended third-party reuse | Open decision |
| OW-13 | Supply chain | Continue dependency updates, continuous advisory review, action pinning and SBOM planning | High for production | Technical and security owner | Production release | Recurring control |
| OW-14 | Jira governance | Review parent Epic and child issue statuses against the closure evidence | High for accurate closure | Project owner | Project archive | Must be completed manually in Jira |

## 4. Remaining risks

The current residual-risk register remains active. Critical risks include unauthorised source use, public deployment without verified security controls and uncontrolled multi-instance or provider costs. High risks include supply chain, production data, provider privacy, absent UAT, unrepresentative performance and incomplete assistive-technology review.

These risks are acceptable only inside the controlled local synthetic-data demonstration boundary. They are not accepted for production.

## 5. Defect and work-item rule

- Create a Jira Bug for every newly confirmed Critical or High software defect.
- Do not classify an unexecuted human test as passed.
- Do not close an external dependency merely because no delivery date exists.
- Link future work back to NFA-91 and the affected Epic.
- Reopen the release decision whenever source, hosting, model, storage or public exposure changes.

