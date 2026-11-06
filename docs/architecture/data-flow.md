# NewsFlow AI data flows

## 1. Purpose and notation

These Mermaid diagrams show how information moves through the implemented NewsFlow AI workflows. They identify security decisions, persistent records, external calls, and user-visible results.

Notation:

- Solid arrows represent implemented flow.
- Dotted arrows represent a proposed or blocked flow.
- PostgreSQL cylinders represent persistent metadata or records.
- Private image storage represents image bytes, not public URLs.
- Every user-specific flow begins with authentication. State-changing requests also require CSRF proof.

## 2. Article ingestion flow

```mermaid
flowchart LR
    Admin["Authenticated administrator<br/>manual sync"]
    Scheduler["Production scheduler<br/>Proposed - not implemented"]

    subgraph SourceBoundary["Article source boundary"]
        Fixture["FixtureNewsProvider<br/>Implemented synthetic source"]
        CNN["Live CNN adapter<br/>Blocked"]
        Approved["Future authorised provider<br/>Proposed"]
    end

    Factory["Provider factory<br/>Fail closed"]
    Fetch["Provider interface<br/>fetch one bounded page"]
    Normalise["Validate, normalise<br/>and sanitise fields"]
    Identity["Canonical identity<br/>and deduplication"]
    Rights["Provenance and<br/>versioned rights decision"]
    Persist[("PostgreSQL<br/>articles, provenance, rights,<br/>sync jobs and checkpoints")]
    Catalogue["Authenticated article catalogue"]

    Admin -->|"POST admin sync with session and CSRF"| Factory
    Scheduler -.-> Factory
    Fixture --> Factory
    CNN -.->|"Denied - no authorised mode"| Factory
    Approved -.->|"Requires new adapter and approval"| Factory
    Factory --> Fetch
    Fetch --> Normalise
    Normalise --> Identity
    Identity --> Rights
    Rights --> Persist
    Persist --> Catalogue
```

Implemented behavior:

1. An administrator can request a bounded synchronisation through `POST /api/v1/admin/articles/sync`.
2. The provider factory creates only `FixtureNewsProvider` when `NEWS_SOURCE_MODE=fixture`; otherwise it raises a source-not-authorised error.
3. The provider returns a typed page containing synthetic article records and a checkpoint.
4. Validation permits only the contracted fields and rejects malformed, unsafe, or unpermitted records.
5. Identity and deduplication prevent duplicate articles while allowing reviewed metadata updates.
6. Provenance, attribution, permitted operations, restrictions, and rights validity are persisted with the article.
7. The catalogue returns only current, display-permitted metadata to authenticated users.

The repository contains an article-sync job abstraction, but no production scheduler is configured. Live CNN retrieval is blocked and absent from this flow.

## 3. LinkedIn text generation flow

```mermaid
sequenceDiagram
    actor User
    participant UI as Next.js generation page
    participant Gateway as POST /api/generations gateway
    participant API as FastAPI generation route
    participant DB as PostgreSQL
    participant Policy as Rights, usage and grounding services
    participant OpenAI as OpenAI Responses API

    User->>UI: Select article, tone and length
    UI->>Gateway: Submit bounded request with CSRF and idempotency key
    Gateway->>API: Forward selected cookies and headers
    API->>DB: Resolve active session and selected article
    API->>Policy: Check display and AI-generation rights
    Policy->>DB: Reserve per-user usage and duplicate control
    Policy->>Policy: Build versioned grounded prompt from permitted fields
    Policy->>OpenAI: Backend-only structured generation request
    OpenAI-->>Policy: Structured draft response and usage metadata
    Policy->>Policy: Validate schema, length and factual grounding
    alt Blocking validation or provider failure
        Policy->>DB: Record safe failure and finish usage attempt
        API-->>UI: Controlled error without private details
    else Accepted for human review
        Policy->>DB: Store private generated draft and audit evidence
        API-->>UI: Editable draft, attribution and warnings
        UI-->>User: Editor and LinkedIn-inspired preview
    end
```

Important properties:

- The prompt uses only rights-approved article fields and keeps instructions separate from untrusted source text.
- The OpenAI key remains in the FastAPI environment and is never sent to the browser.
- The service requires current rights at the moment of generation.
- Usage limits and idempotency reduce duplicate or uncontrolled paid calls.
- Deterministic validation can block or warn; it does not claim the draft is factually verified.
- Every accepted result requires human review and is never published automatically.

## 4. Image generation and secure delivery flow

```mermaid
flowchart TB
    User["Authenticated user"]
    UI["Next.js image controls"]
    Gateway["Same-origin image gateway"]
    API["FastAPI POST /api/images<br/>or regenerate endpoint"]
    Context["Load owned draft, article<br/>and current image context"]
    Rights["Recheck source rights"]
    Prompt["Compose versioned<br/>illustration prompt"]
    Safety["Sensitive-news image<br/>safety policy"]
    Usage["Usage, rate, duplicate<br/>and idempotency controls"]
    OpenAI(["OpenAI image API<br/>external provider"])
    Validate["Decode and validate MIME,<br/>bytes, pixels and digest"]
    Store[("Private image bytes<br/>local adapter in development")]
    Metadata[("PostgreSQL image metadata,<br/>ownership and version links")]
    Delivery["Owner-authorised preview<br/>or download route"]

    User --> UI --> Gateway --> API
    API --> Context --> Rights --> Prompt --> Safety --> Usage
    Usage --> OpenAI --> Validate
    Validate --> Store
    Store --> Metadata
    Metadata --> Delivery
    Store --> Delivery
    Delivery --> UI
```

Failure rules:

- Rights or safety denial happens before an external provider call.
- Invalid, oversized, corrupt, or mismatched image data is rejected before persistence.
- If byte storage succeeds but metadata persistence fails, the service attempts compensating object deletion.
- A failed regeneration preserves the original image.
- Each successful alternative is immutable and linked to its parent.
- Browser responses never expose a filesystem path or storage key.
- Preview and download routes recheck the authenticated owner and use private no-store responses.
- The implemented storage adapter is local-only. Production object storage is proposed, not implemented.

## 5. Draft saving and content library flow

```mermaid
flowchart LR
    Editor["Human-edited LinkedIn draft<br/>and selected image ID"]
    Gateway["Next.js POST /api/drafts"]
    Auth["Session, CSRF and<br/>idempotency validation"]
    Ownership["Verify generated draft<br/>and image belong to user"]
    Transaction["Create saved draft and<br/>immutable initial version"]
    DB[("PostgreSQL<br/>saved drafts and versions")]
    Library["Personal content library"]
    Update["Patch edited content with<br/>optimistic version check"]
    History["Immutable version history<br/>and restoration"]

    Editor --> Gateway --> Auth --> Ownership --> Transaction --> DB
    DB --> Library
    Library --> Update --> DB
    DB --> History
    History -->|"Restore as a new version"| DB
```

Implemented behavior:

1. The browser sends the reviewed text, generated-draft ID, optional selected-image ID, CSRF proof, and idempotency key through the Next.js gateway, which forwards the request to FastAPI `POST /api/v1/drafts`.
2. FastAPI verifies that referenced private resources belong to the authenticated user.
3. A PostgreSQL transaction creates the current saved draft and its immutable initial history record.
4. Listing and retrieval always scope queries to the authenticated owner.
5. Updates require the expected version and return a conflict when another update already changed the draft.
6. Restoration never overwrites history; it appends a new current version linked to the historical source.
7. Deletion immediately removes active access and records retryable cleanup and retention work.

## 6. Content export flow

```mermaid
flowchart LR
    User["Authenticated user"]
    Draft["Current human-edited text"]
    Clipboard["Browser Clipboard API"]
    Selected["Selected private image ID"]
    NextRoute["Next.js download gateway"]
    API["FastAPI owner-authorised<br/>download endpoint"]
    Meta[("PostgreSQL ownership<br/>and image metadata")]
    Bytes[("Private image storage")]
    Download["Browser file download<br/>safe filename and MIME"]

    User --> Draft -->|"Explicit copy action"| Clipboard
    User --> Selected -->|"Explicit download action"| NextRoute
    NextRoute -->|"Session cookie only"| API
    API --> Meta
    Meta -->|"Owned storage key"| Bytes
    Bytes --> API -->|"Private no-store bytes"| NextRoute --> Download
```

Export is user-controlled. NewsFlow AI does not publish to LinkedIn. Text copying uses the browser Clipboard API and always copies the current edited text. Image download uses an owner-authorised backend request, validates the returned media type and filename, and never reveals the internal storage key.

## 7. Complete user journey

```mermaid
flowchart LR
    Login["Register or sign in"] --> Browse["Browse authorised<br/>article metadata"]
    Browse --> Select["Select and review<br/>source information"]
    Select --> Generate["Generate grounded<br/>LinkedIn draft"]
    Generate --> Edit["Review and edit"]
    Edit --> Image["Generate and select<br/>AI illustration"]
    Image --> Save["Save owned content"]
    Save --> Library["Reopen from personal<br/>content library"]
    Library --> Export["Copy text or download<br/>private image"]
    Library --> Delete["Delete and begin<br/>retention cleanup"]
```

Every step after sign-in remains subject to backend authentication and owner checks. Source display and AI generation also remain subject to current rights. Provider output remains reviewable content, not an automatic publication.

## 8. Data stores and minimisation

| Store or destination | Data | Deliberately excluded |
| --- | --- | --- |
| PostgreSQL | Account email, password hash, hashed sessions, article metadata, provenance, rights, drafts, versions, image metadata, audit and operational records | Plaintext passwords, raw session tokens, image bytes |
| Private image storage | Validated generated image bytes under opaque keys | Public URLs, account credentials, article content |
| OpenAI request | Minimum permitted article facts and controlled instructions required for the selected generation | Database credentials, session tokens, unrelated user profile data |
| Structured logs | Request IDs, safe record IDs, status, duration, category and recovery state | Credentials, cookies, article content, prompts, drafts, provider bodies and private storage keys |
| Browser | Current interface state, edited text and private responses needed for the user's session | OpenAI keys, database credentials, server session secrets and internal storage keys |

## 9. Failure and recovery flow

```mermaid
flowchart LR
    Request["Authenticated operation"] --> Work["Bounded application workflow"]
    Work -->|"Success"| Commit["Commit authoritative state"]
    Work -->|"Controlled failure"| Safe["Safe user error and<br/>structured event"]
    Work -->|"Partial storage operation"| Reconcile["Compensation or durable<br/>cleanup state"]
    Reconcile --> Retry["Bounded operator or<br/>worker reconciliation"]
    Retry --> Verify["Verify database, storage,<br/>ownership and deletion state"]
```

Database transactions protect related PostgreSQL changes. PostgreSQL and image storage cannot share one transaction, so image workflows use compensation and durable reconciliation. Retrying uncertain paid provider operations is deliberately restricted.

## 10. Verification references

- Article ingestion: `apps/api/app/providers`, `apps/api/app/services/article_sync.py`, and `apps/api/app/services/article_deduplication.py`
- Text generation: `apps/api/app/api/routes/generations.py` and `apps/api/app/services/linkedin_generation.py`
- Image generation: `apps/api/app/api/routes/image_regeneration.py` and `apps/api/app/services/generated_image_storage.py`
- Saved drafts: `apps/api/app/api/routes/saved_drafts.py` and `apps/api/app/services/saved_drafts.py`
- Export: `apps/web/lib/content-export.ts`, `apps/web/lib/image-download-proxy.ts`, and `apps/api/app/api/routes/image_delivery.py`
- Reliability: [reliability-and-recovery.md](../reliability-and-recovery.md)
- Rights: [article-provenance-and-rights.md](../article-provenance-and-rights.md)
