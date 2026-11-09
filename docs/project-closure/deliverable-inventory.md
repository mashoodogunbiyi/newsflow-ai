# NewsFlow AI Deliverable Inventory

## 1. Purpose

This inventory maps the final deliverables and representative completed tasks to repository evidence. Git history through the NFA-90 baseline contains 82 merged pull requests, providing implementation traceability in addition to the documents below.

## 2. Inventory

| Deliverable | Status | Supporting evidence |
| --- | --- | --- |
| Requirements and acceptance baseline | Delivered | [NFA-3](../jira/NFA-3.md) |
| CNN access research and authorisation record | Delivered as No-Go evidence | [NFA-4](../jira/NFA-4.md), [NFA-5](../jira/NFA-5.md) |
| Source contract, safeguards, ADR and risk register | Delivered | [NFA-6](../jira/NFA-6.md), [NFA-7](../jira/NFA-7.md), [NFA-8](../jira/NFA-8.md), [NFA-9](../jira/NFA-9.md) |
| Repository and local development foundation | Delivered | [README](../../README.md), [development setup](../development-setup.md) |
| Next.js frontend | Delivered | `apps/web`, frontend tests and production build evidence |
| FastAPI backend and API documentation | Delivered | `apps/api`, [API reference](../api-reference.md), local `/docs` and `/openapi.json` |
| PostgreSQL schema, migrations and seeds | Delivered | `apps/api/migrations`, [database design](../jira/NFA-20.md), seed script |
| Authentication and object authorisation | Delivered | [authorisation](../authorization.md), [API security](../api-security.md), authentication tests |
| Article-provider and catalogue pipeline | Delivered for fixtures | [provider interface](../source-provider-interface.md), [pipeline tests](../article-pipeline-testing.md) |
| Live CNN adapter | Not delivered by design | [ADR-001 No-Go](../jira/NFA-8.md), [disabled adapter](../cnn-adapter.md) |
| LinkedIn generation service and API | Delivered | [generation service](../linkedin-generation-service.md), [generation API](../generation-api.md) |
| Grounding, limits, evaluation and monitoring | Delivered | [grounding](../factual-grounding-validation.md), [evaluation](../ai-grounding-content-safety-evaluation.md), [monitoring](../generation-monitoring.md) |
| Image generation, safety and local private storage | Delivered locally | [image safety](../image-safety-policy.md), [image storage](../image-storage.md), [E5 testing](../e5-image-testing.md) |
| Dashboard, controls, editor and preview | Delivered | [dashboard](../article-dashboard.md), [editor](../linkedin-draft-editor.md), [preview](../linkedin-content-preview.md) |
| Content library, versions, export and deletion | Delivered | [library](../content-library-interface.md), [versions](../draft-version-history.md), [export](../content-export.md), [deletion](../content-deletion-retention.md) |
| Security and reliability assurance | Delivered for local scope | [threat model](../security-threat-model.md), [reliability](../reliability-and-recovery.md) |
| Integration and browser testing | Delivered | [integration evidence](../integration-e2e-testing.md), [testing guide](../testing.md) |
| Human UAT execution | Not completed | [UAT plan](../user-acceptance-testing.md), [pending acceptance](../uat/retest-and-acceptance.md) |
| Docker packaging and reproducibility | Delivered and verified | [Docker record](../docker-packaging.md), [handover results](../handover/reproducibility-results.md) |
| Deployment and operations documentation | Delivered as proposed guidance | [deployment guide](../deployment/deployment-guide.md), [operations runbook](../deployment/operations-runbook.md) |
| Architecture and data-flow diagrams | Delivered | [system architecture](../architecture/system-architecture.md), [data flow](../architecture/data-flow.md) |
| Professional README and screenshots | Delivered | [README](../../README.md), [screenshot manifest](../screenshots/README.md) |
| Demonstration package | Delivered; narrated rehearsal pending | [demonstration package](../demonstration/README.md), [evidence](../demonstration/evidence.md) |
| Technical report and portfolio case study | Delivered | [technical report](../technical-report.md), [case study](../portfolio-case-study.md) |
| Reproducibility and handover package | Delivered and merged in PR #82 | [handover](../handover/README.md) |
| Project closure and retrospective | NFA-91 technical candidate | [closure report](project-closure-report.md), [retrospective](retrospective.md) |

## 3. Evidence rule

A document, branch or Jira status alone does not prove functionality. Completed implementation claims above are supported by source code, tests and merged history. Items labelled proposed, pending, local, fixture-only or Not completed retain that status and must not be converted into a completed production claim.

