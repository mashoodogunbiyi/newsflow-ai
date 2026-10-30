# NFA-48 - Safe Image-Prompt Composer

## Outcome

NFA-48 adds a reusable backend service that converts an authorised article, or an associated private LinkedIn draft plus its article, into a structured prompt package for a future image-generation provider.

The composer does not call OpenAI, generate an image, expose a public endpoint, store a prompt, or publish content. It prepares versioned trusted instructions and separate untrusted context after validating source rights and controlled presentation choices.

## Architecture

```text
Strict style and composition choices
                 +
Current NFA-32 article-rights decision
                 +
Validated NFA-6 article contract
                 +
Optional owner-scoped NFA-40 LinkedIn draft
                 |
                 v
         ImagePromptComposer
           |             |
           |             +----> approved source reference and rights version
           v
Versioned structured prompt result
  |-- trusted_instructions
  `-- untrusted_context
                 |
                 v
Future authorised image-generation service
```

The calling workflow remains responsible for authenticating the user, loading an owner-scoped draft when requested, obtaining the current rights decision, calling a future image provider, validating its output, storing provenance, and requiring human review.

## Internal request

`ImagePromptRequest` accepts only:

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `article_id` | UUID | Yes | Application article whose current rights control the operation. |
| `generation_id` | UUID or null | No | Associated private LinkedIn generation when draft context is requested. |
| `style` | Enum | Yes | One supported application-owned illustration style. |
| `aspect_ratio` | Enum | Yes | One supported output shape. |
| `composition` | Enum | No | Safe layout choice; defaults to `balanced`. |

Extra properties and free-text prompt instructions are rejected by Pydantic. A caller cannot submit a provider model, source text, safety override, person, location, logo, photographic treatment, or arbitrary instruction through this schema.

## Supported presentation choices

### Illustration styles

| Value | Intended visual treatment |
|---|---|
| `editorial_illustration` | Simplified conceptual forms and measured publication-quality visual storytelling. |
| `minimalist_illustration` | Restrained shapes, negative space, limited colour, and one conceptual focus. |
| `abstract_technology` | Non-branded geometry and data-like systems for technology topics. |
| `professional_infographic_style` | Clear hierarchy and generic symbols without unsupported numbers, labels, charts, or claims. |

These are NewsFlow AI product-level prompt styles. A future image-provider adapter must confirm that its selected model can follow them and must not silently expose additional provider options.

### Aspect ratios

| Value | Prompt target |
|---|---|
| `landscape` | 16:9 LinkedIn feed composition. |
| `square` | 1:1 LinkedIn feed composition. |
| `portrait` | 4:5 LinkedIn feed composition. |

### Composition

| Value | Prompt behaviour |
|---|---|
| `balanced` | Clear central visual hierarchy and comfortable spacing. |
| `focal_point_left` | Main concept on the left with clean text-free space on the right. |
| `focal_point_right` | Main concept on the right with clean text-free space on the left. |

## Source rights and context validation

The composer fails closed unless:

- The rights decision belongs to the requested article.
- The operation is `USE_FOR_AI_GENERATION`.
- The decision is allowed and records the current rights version.
- Required attribution is complete.
- Permitted article content is available.
- AI processing and derivative output are both allowed.
- The article source reference is internally consistent.

If a LinkedIn draft is supplied, the service also requires:

- The request contains the same generation ID.
- The draft references the same article ID, title, source name, and canonical URL.
- The draft was not rejected by grounding validation.
- The draft context does not exceed 4,000 characters.

The service intentionally still requires the article when a draft is used. A draft is derived text and cannot replace current source rights or permitted factual context. The calling workflow must retrieve the draft through an owner-scoped repository query before calling the composer.

## Permitted source fields

Only these article fields enter the untrusted image context:

| Field | Purpose |
|---|---|
| `title` | Broad topic identification. |
| `category` | General conceptual domain. |
| `description` | Approved provider description when present. |
| `permitted_content` | Text explicitly approved for AI processing and derivative output. |

The prompt excludes the URL, provider item ID, byline, copyright notice, authorisation reference, retention rule, database identifiers, source-rights metadata, and confidential provider information.

The exact article title, source name, canonical URL, approved attribution, article ID, and rights-version ID are preserved separately in `ImagePromptSourceReference` for application use. The future image model does not need those reference fields.

## Draft context

An associated LinkedIn draft may be supplied as one derived field named `linkedin_draft`. It remains untrusted and can influence only the broad thematic emphasis. The trusted instructions explicitly state that the draft cannot establish a new fact.

Rejected, unrelated, missing, or oversized drafts fail with a content-free error. The composer does not accept a draft without the matching authorised article.

## Prompt separation and injection protection

`ImagePromptResult` keeps two secret-string fields separate:

- `trusted_instructions` contains only application-owned safety, illustration, style, aspect-ratio, and composition rules.
- `untrusted_context` contains one JSON object between `UNTRUSTED_IMAGE_CONTEXT_JSON` markers.

Article and draft values never enter the trusted template. Embedded text asking the system to reveal secrets, follow links, copy a photograph, bypass safety, use tools, or invent details remains inert untrusted data. Secret-string representation also prevents context from appearing through ordinary object logging.

This separation reduces risk but does not make model behaviour trustworthy. A future image-generation service must validate the generated asset and keep human review mandatory.

## Originality and non-deception rules

The versioned trusted instructions require the future image model to:

- Create an original professional illustration rather than a documentary image.
- Represent the general supported topic conceptually.
- Avoid inventing specific scenes, venues, people, events, demonstrations, injuries, disasters, statistics, quotations, logos, interfaces, or other unsupported details.
- Avoid recognisable real people and false participation in a reported event.
- Avoid photorealistic, breaking-news, surveillance, evidence, and on-location visual treatments.
- Never reproduce, imitate, trace, transform, or closely resemble CNN photographs, video frames, graphics, logos, or trade dress.
- Avoid headlines, captions, watermarks, source marks, unsupported charts, and factual text inside the image.
- Never imply that a synthetic illustration is authentic news evidence.
- Keep human review mandatory before the asset is used.

If authorised information is insufficient, the service raises `insufficient_image_context` instead of constructing a specific visual scene.

## Structured result

The composer returns:

- Prompt version.
- Context kind: `article` or `linkedin_draft`.
- Associated generation ID when applicable.
- Validated presentation preferences.
- Included source and derived field names.
- Approved source reference and rights version.
- Masked trusted instructions.
- Masked untrusted context.
- `human_review_required = true`.
- `documentary_use_allowed = false`.

Prompt text and context must not be logged. A later generation record should persist the prompt version, safe choices, source reference, rights version, provider metadata, and review state without storing restricted prompt content unless a separately reviewed requirement authorises it.

## Prompt versioning

Current identifier: `image_prompt_v1`

| Version | Date | Change |
|---|---|---|
| `image_prompt_v1` | 30 October 2026 | Initial rights-aware conceptual-illustration template with four styles, three aspect ratios, three compositions, untrusted article-or-draft context, source allowlisting, restricted-photography protection, and non-deception rules. |

A material change to safety behaviour, accepted fields, or presentation meanings must create a new prompt version and corresponding regression tests. Do not silently change the meaning of a version already stored with generated assets.

## Safe errors

The composer raises typed internal errors with stable codes and messages that do not contain article or draft text:

| Code | Meaning |
|---|---|
| `article_image_generation_not_permitted` | Current rights do not permit AI derivative illustration. |
| `article_attribution_incomplete` | Required approved attribution is missing. |
| `article_content_not_permitted` | Source content is explicitly restricted. |
| `insufficient_image_context` | There is not enough authorised information for a safe theme. |
| `linkedin_draft_context_missing` | A requested draft was not supplied. |
| `linkedin_draft_context_mismatch` | The supplied draft has the wrong generation ID. |
| `linkedin_draft_source_mismatch` | The draft and approved article do not match. |
| `linkedin_draft_validation_rejected` | Grounding validation rejected the draft. |
| `linkedin_draft_context_too_long` | The draft exceeds the bounded context size. |

A future API layer must map these to safe HTTP responses without exposing the source, draft, prompt, rights internals, or stack traces.

## Automated verification

Run the focused checks from the repository root:

```bash
apps/api/.venv/bin/ruff check \
  apps/api/app/models/image_prompt.py \
  apps/api/app/prompts/image_illustration.py \
  apps/api/app/services/image_prompt.py \
  apps/api/tests/test_image_prompt.py
apps/api/.venv/bin/ruff format --check \
  apps/api/app/models/image_prompt.py \
  apps/api/app/prompts/image_illustration.py \
  apps/api/app/services/image_prompt.py \
  apps/api/tests/test_image_prompt.py
apps/api/.venv/bin/pytest -q apps/api/tests/test_image_prompt.py
```

The tests cover:

- Valid structured article prompts.
- All supported styles, aspect ratios, and compositions.
- Invalid and extra parameter rejection.
- Exact permitted-field filtering.
- Current rights, attribution, and derivative-use gates.
- Restricted and insufficient source handling.
- Prompt-injection separation.
- Associated draft validation and size bounds.
- Rejected and mismatched drafts.
- Non-deception and restricted-photography rules.
- Stable prompt-version metadata and masked representations.

All fixtures are original and synthetic. The tests make no network call, invoke no image provider, use no CNN content, and require no API credential.

Verified locally on 30 October 2026:

- The focused NFA-48 image-prompt run passed 23 tests.
- The complete backend run passed 329 tests and safely skipped 13 opt-in PostgreSQL and live-model tests.
- Branch-aware backend coverage measured 80.51 percent, above the enforced 75 percent floor.
- Ruff linting and formatting checks passed for all 144 Python files.

## Implementation evidence

| Deliverable | Repository location |
|---|---|
| Input, enum, reference, and result schemas | `apps/api/app/models/image_prompt.py` |
| Versioned trusted template | `apps/api/app/prompts/image_illustration.py` |
| Rights-aware composer | `apps/api/app/services/image_prompt.py` |
| Unit tests | `apps/api/tests/test_image_prompt.py` |
| Technical documentation | `docs/image-prompt-composer.md` |

## Limitations and next steps

- NFA-48 does not call OpenAI or another image provider.
- It does not generate, validate, store, display, download, or delete an image.
- It does not expose an HTTP endpoint or user interface.
- It does not check whether a final image visually copied a restricted asset; later output review is required.
- It cannot guarantee that a model will follow the prompt.
- Provider-specific size values, output formats, content policies, timeouts, retries, usage limits, and cost controls remain future work.
- Object storage, image provenance, retention, accessibility text, and deletion behaviour remain future work.
- Live CNN material remains blocked by ADR-001 and cannot enter this workflow without written authorisation and a revised Go decision.

NFA-48 is implemented and ready for Mashood Ogunbiyi's review. Move the Jira issue to Done only after the pull request is merged and final GitHub evidence is attached.
