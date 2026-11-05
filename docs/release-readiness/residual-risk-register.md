# NFA-82 Residual Risk Register

## Rating method

Likelihood and impact use a 1 to 5 scale. The risk rating is the product of likelihood and impact:

- 1 to 4: Low.
- 5 to 9: Medium.
- 10 to 16: High.
- 17 to 25: Critical.

No Critical residual risk below is accepted for public release.

## Register

| ID    | Risk                                                                                                          | Likelihood | Impact | Rating   | Current control                                                                                 | Release decision                                                                                       | Owner                              |
| ----- | ------------------------------------------------------------------------------------------------------------- | ---------: | -----: | -------- | ----------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ | ---------------------------------- |
| RR-01 | Live CNN content is retrieved or processed without written permission                                         |          4 |      5 | Critical | ADR-001 No-Go, disabled adapter, fixture-only configuration, rights checks                      | Block live integration; synthetic demonstration only                                                   | Product and Security Owner         |
| RR-02 | Public deployment lacks verified HTTPS, proxy, cookie, security-header, managed-secret, and incident controls |          4 |      5 | Critical | Secure application defaults and documented SEC-01 to SEC-06 gates                               | Block public deployment                                                                                | Technical and Security Owner       |
| RR-03 | Shared edge abuse, connection, and provider-budget controls are absent in a multi-instance deployment         |          4 |      5 | Critical | Application request limits, per-user controls, idempotency, bounded retries                     | Block public multi-user deployment                                                                     | Product and Technical Owner        |
| RR-04 | Supply-chain or workflow compromise bypasses local dependency checks                                          |          3 |      5 | High     | Lockfile, CI audits, read-only workflow permission, secret scan                                 | Complete continuous scanning, action pinning, SBOM, branch protection, and patch SLA before production | Technical Owner                    |
| RR-05 | Production database, backup, log, and private object-storage controls expose or resurrect private data        |          3 |      5 | High     | Owner-scoped queries, redaction, private local storage, cleanup records                         | Complete SEC-06 deployment and restore review before production                                        | Technical and Security Owner       |
| RR-06 | OpenAI receives data without approved production terms, privacy review, budget, or model decision             |          3 |      5 | High     | Permitted field allowlist, synthetic fixtures, backend-only keys, no live key in routine tests  | Mock providers for demonstration; block production calls until reviewed                                | Product and Security Owner         |
| RR-07 | Missing representative UAT leaves core usability failures undiscovered                                        |          4 |      4 | High     | Complete UAT package and deterministic technical rehearsal                                      | Block production acceptance until NFA-81 sessions and sign-off are complete                            | Product Owner                      |
| RR-08 | Local performance results do not represent deployed PostgreSQL, storage, network, or lower-powered devices    |          3 |      4 | High     | Executable local budgets and bounded queries                                                    | Allow controlled local demo; require staging measurements before public release                        | Technical Owner                    |
| RR-09 | Automated accessibility tests miss assistive-technology barriers                                              |          3 |      4 | High     | Axe, keyboard, focus, responsive, contrast, motion, and error-state checks                      | Complete representative VoiceOver journey before full accessibility acceptance                         | Product and Accessibility Reviewer |
| RR-10 | Database and object storage diverge after compound failure                                                    |          2 |      4 | Medium   | Transaction ordering, compensation, durable cleanup, bounded reconciliation                     | Accept for local demo; deploy scheduler, inventory, and alerting before production                     | Technical Owner                    |
| RR-11 | Model or policy changes reduce grounding or image-safety performance                                          |          3 |      4 | High     | Versioned evaluation, 100 percent synthetic thresholds, release-blocking failures, human review | Rerun evaluation after every relevant change; no automatic publication                                 | AI and Product Owner               |
| RR-12 | Users cannot recover a forgotten password                                                                     |          3 |      3 | Medium   | Registration and login remain available; feature is explicitly out of current MVP               | Accept for controlled demo; decide and implement before a user-facing account service                  | Product Owner                      |

## Review rule

Review this register whenever the deployment environment, source provider, OpenAI model, storage adapter, authentication flow, public exposure, or release scope changes. A conditionally accepted local risk must not be silently carried into production.
