# NewsFlow AI architecture decisions

## 1. Purpose and status

This decision register explains the significant trade-offs represented in the NFA-86 diagrams. It links to the detailed design records and implementation evidence already stored in the repository.

ADR-001 in [NFA-8](../jira/NFA-8.md) is the formal source-access architecture decision. The entries below summarise implemented choices and open deployment decisions; they do not rewrite or weaken ADR-001.

## 2. Decision summary

| ID | Decision | Status | Main consequence |
| --- | --- | --- | --- |
| AD-01 | Use a provider-neutral article interface and fail closed when no authorised provider is configured | Accepted and implemented | Fixture development remains possible without implying live CNN access |
| AD-02 | Use Next.js as the user interface and same-origin gateway, with FastAPI as the authoritative API | Accepted and implemented | Browser code receives a narrow interface while backend controls remain mandatory |
| AD-03 | Use server-managed cookie sessions with CSRF protection | Accepted and implemented | Sessions can be revoked centrally and raw tokens are not stored in PostgreSQL |
| AD-04 | Use PostgreSQL as the application system of record | Accepted and implemented | Ownership, rights, provenance, versions and audit evidence share transactional storage |
| AD-05 | Recheck source rights at every sensitive use | Accepted and implemented | Previously stored content cannot bypass current display or AI-processing restrictions |
| AD-06 | Keep OpenAI calls behind backend service interfaces | Accepted and implemented | Keys remain server-side and tests can replace live providers with deterministic doubles |
| AD-07 | Separate private image bytes from PostgreSQL metadata | Accepted locally; production adapter pending | Owner and provenance records remain queryable without exposing object locations |
| AD-08 | Require human review and do not auto-publish | Accepted and implemented | Generated text and images remain editable drafts rather than automatic claims or posts |
| AD-09 | Use versioned migrations, Docker packaging and health-ordered local startup | Accepted and implemented locally | Developers and CI can reproduce the application and schema consistently |
| AD-10 | Treat production hosting as a gated future architecture | Accepted | Local success cannot be presented as production readiness |

## 3. Detailed decisions

### AD-01 - Provider-neutral article boundary

**Decision:** Core ingestion depends on the `NewsProvider` interface. The provider factory creates only `FixtureNewsProvider` for the validated `fixture` mode and raises `SourceNotAuthorisedError` otherwise.

**Why:** NewsFlow AI needs deterministic development and testing without scraping CNN or presenting an unapproved access route as authorised.

**Trade-off:** There is no live article feed. Adding one requires written authorisation, a reviewed adapter, rights mapping, operational controls, and a replacement or update to ADR-001.

**References:** [NFA-8](../jira/NFA-8.md), [source-provider-interface.md](../source-provider-interface.md), and [cnn-adapter.md](../cnn-adapter.md).

### AD-02 - Next.js gateway and FastAPI authority

**Decision:** React components use Next.js pages and same-origin route handlers. The route handlers forward only approved cookies and headers to FastAPI. FastAPI remains authoritative for validation, authentication, rights, ownership, limits, persistence, and safe errors.

**Why:** Same-origin gateways simplify browser cookie handling and hide the internal backend origin without moving security decisions into the UI.

**Trade-off:** Gateway contracts must stay aligned with backend routes and add another request hop. Direct browser access to internal FastAPI should not be required in a deployment.

**References:** [frontend-layout.md](../frontend-layout.md), `apps/web/app/api`, and `apps/web/lib/*-proxy.ts`.

### AD-03 - Server-managed sessions and CSRF

**Decision:** Login returns an HTTP-only session cookie and a CSRF cookie. PostgreSQL stores hashes of both random values. Reads require an active session; state changes also require a matching CSRF header. Sessions have absolute expiry and can be revoked on logout.

**Why:** Server-side session state supports revocation and avoids storing a reusable session secret in browser JavaScript or local storage.

**Trade-off:** Authentication depends on PostgreSQL availability and requires careful HTTPS, proxy, cookie, and CSRF configuration in deployment.

**References:** `apps/api/app/services/authentication.py`, `apps/api/app/api/dependencies.py`, and [authorization.md](../authorization.md).

### AD-04 - PostgreSQL system of record

**Decision:** PostgreSQL stores application metadata and authoritative relationships. Alembic versions the schema. UUID keys, foreign keys, uniqueness, checks, and owner-scoped repositories enforce integrity.

**Why:** Accounts, provenance, rights, generation records, saved drafts, immutable history, audit and deletion state are relational and benefit from transactions.

**Trade-off:** API readiness and authentication depend on PostgreSQL. Production needs managed availability, private networking, least privilege, encrypted backups, and restore proof.

**References:** [NFA-20 schema](../jira/NFA-20.md), `apps/api/migrations`, and [backup-and-recovery.md](../deployment/backup-and-recovery.md).

### AD-05 - Rights checked at point of use

**Decision:** Stored provenance and versioned rights are checked for catalogue display and checked again before text or image generation.

**Why:** Permission can expire or change after ingestion. Storage is not permanent permission to display, process, or generate derivative material.

**Trade-off:** Sensitive workflows require additional database reads and fail closed when rights evidence is missing or unavailable.

**References:** [article-provenance-and-rights.md](../article-provenance-and-rights.md) and `apps/api/app/services/article_rights.py`.

### AD-06 - Backend-only OpenAI adapters

**Decision:** FastAPI services call OpenAI through small text and image interfaces. Configuration uses server-side environment values. Routine tests inject deterministic provider doubles.

**Why:** Keys must not reach the browser, provider errors need safe mapping, and CI must not require credentials or incur paid generation calls.

**Trade-off:** Live behavior still needs approved models, terms, privacy, budget, monitoring and release checks. Mocked tests cannot prove live provider availability or output quality.

**References:** [openai-integration.md](../openai-integration.md), [openai-image-generation.md](../openai-image-generation.md), and [ai-grounding-content-safety-evaluation.md](../ai-grounding-content-safety-evaluation.md).

### AD-07 - Private image bytes separated from metadata

**Decision:** PostgreSQL stores image ownership, lineage, model, safety, validation and digest metadata. A backend-only storage adapter holds bytes under opaque keys. Image delivery rechecks ownership and returns private no-store responses.

**Why:** Image bytes do not belong in normal API payloads or public URLs, while relational metadata must participate in owner and lifecycle rules.

**Trade-off:** PostgreSQL and object storage cannot commit atomically. The service uses compensation and cleanup evidence. The only current adapter is local and deliberately blocked in staging and production.

**References:** [image-storage.md](../image-storage.md), [image-delivery.md](../image-delivery.md), and [reliability-and-recovery.md](../reliability-and-recovery.md).

### AD-08 - Human review with no automatic publishing

**Decision:** Generated LinkedIn text and illustrations are private, editable, and marked for human review. Export requires an explicit user copy or download action. No LinkedIn publishing integration exists.

**Why:** Grounding checks reduce risk but cannot guarantee truth, appropriateness, or user intent. Users need control over the final content.

**Trade-off:** The application does not provide one-click publishing and the user remains responsible for final review and platform compliance.

**References:** [factual-grounding-validation.md](../factual-grounding-validation.md), [linkedin-draft-editor.md](../linkedin-draft-editor.md), and [content-export.md](../content-export.md).

### AD-09 - Versioned schema and reproducible local packaging

**Decision:** Alembic migrations version the PostgreSQL schema. Multi-stage Dockerfiles and Docker Compose package the frontend, backend, migrations, database, and local private image volume. Health conditions order startup.

**Why:** Developers and CI need a consistent setup that does not rely on manually creating tables or installing every service directly on the host.

**Trade-off:** Docker Compose is a development package, not a production platform. Local volumes are not backups and local container health does not prove production resilience.

**References:** [docker-packaging.md](../docker-packaging.md), `compose.yaml`, and [development-setup.md](../development-setup.md).

### AD-10 - Gated production architecture

**Decision:** NFA-85 documents a proposed deployment rather than claiming production exists. Production release stays No-Go, as does any public release, until rights, storage, secrets, transport, shared abuse controls, monitoring, backup, restore, UAT, accessibility and security gates pass.

**Why:** The implemented local application and deterministic test suite are not evidence that a secure hosting environment or operational recovery capability exists.

**Trade-off:** Portfolio and demonstration use must stay within the controlled synthetic-data scope until the release decision changes.

**References:** [deployment-guide.md](../deployment/deployment-guide.md), [release-readiness-quality-signoff.md](../release-readiness-quality-signoff.md), and [security-threat-model.md](../security-threat-model.md).

## 4. Open decisions

The following choices remain unresolved and must not be shown as implemented:

- Approved hosting platform and regional architecture.
- Production private object-storage provider and adapter.
- Authorised live article provider and permitted-use contract.
- Managed secret, logging, monitoring and alerting services.
- Shared rate limiting, provider budgets and emergency stop.
- Managed PostgreSQL availability, backup, retention and disaster recovery design.
- Background worker and scheduler platform.
- Production OpenAI model, data terms, privacy and cost approval.
- Final public-release, UAT and accessibility sign-off.

## 5. Decision maintenance

- Update the decision status and affected Mermaid diagrams in the same pull request as an architectural change.
- Add a formal ADR when a change affects source rights, security boundaries, primary storage, authentication, external providers, or deployment topology.
- Record rejected alternatives and migration consequences in that ADR.
- Never change a diagram from proposed or blocked to implemented without repository evidence and an accountable decision.
