# NFA-49 - Sensitive-News Image Safety Policy

## Outcome

NFA-49 adds the central backend policy that evaluates every composed news illustration request before a future image provider can be called.

The policy detects sensitive news topics, blocks fabricated documentary evidence and misleading real-person depictions, forces conceptual non-photorealistic treatment, requires AI-generated designation and human review, applies available provider safety controls, and records only content-free decision metadata.

NFA-49 does not call an image provider or claim that automated classification guarantees a safe output.

## Position in the workflow

```text
Authorised article and optional private LinkedIn draft
                         |
                         v
       NFA-48 ImagePromptComposer
                         |
                         v
         NFA-49 ImageSafetyService
              |                    |
              |                    +----> content-free decision record
              v
       provider_call_allowed?
          |              |
          | no           | yes, with enforced controls
          v              v
  stop or review     future image provider
```

The safety service must run after prompt composition and before provider access. `provider_call_allowed` is true only for `allowed` and `allowed_with_restrictions`. It is false for `rejected` and `review_required`.

A future orchestration service must enforce this gate. A frontend route, user request, or provider setting must never call the provider directly.

## Sensitive-news categories

The initial deterministic policy defines:

| Category | Examples of policy signals |
|---|---|
| `armed_conflict` | Armed conflict, war zone, invasion, military or missile strike, battlefield, combat, troops. |
| `terrorism` | Terrorism, terror attack, terrorist, suicide bombing, hostage attack. |
| `natural_disaster` | Earthquake, tsunami, wildfire, hurricane, tornado, landslide, major flood, collapsed building. |
| `death_or_serious_injury` | Fatalities, killed, death toll, serious injury, casualties, mass-casualty reporting. |
| `public_health_emergency` | Pandemic, epidemic, outbreak, quarantine, health crisis, public health emergency. |
| `election_or_political_event` | Elections, ballots, voting, campaigns, political rallies, parliament, presidential debates. |
| `criminal_allegation` | Criminal allegations, charges, arrests, fraud allegations, trials, police investigations. |
| `identifiable_person_sensitive_event` | A person marker combined with another sensitive category. |
| `uncertain` | Malformed context or explicit uncertainty and unconfirmed classification signals. |
| `non_sensitive` | No sensitive or uncertainty rule matched. |

Multiple sensitive categories can apply to one request. Categories are safe labels and do not contain article or user text.

## Decision model

| Decision | Provider call | Meaning |
|---|---:|---|
| `allowed` | Yes | An ordinary topic may proceed as a designated conceptual illustration with normal provider moderation. |
| `allowed_with_restrictions` | Yes | A sensitive topic may proceed only with the policy's conceptual treatment, no photorealism, strict available provider controls, AI designation, and human review. |
| `rejected` | No | The request asks for deceptive evidence, misleading real-person content, a safety override, or sensitive generation without essential provider moderation. |
| `review_required` | No | Classification is uncertain or the ordinary request lacks essential provider moderation. A human or corrected configuration must resolve it before generation. |

Every result has:

- `required_treatment = conceptual_illustration`.
- `photorealism_allowed = false`.
- `documentary_use_allowed = false`.
- `ai_generated_designation = AI-generated illustration`.
- `review_required = true` for the generated asset and its intended use.

The universal review flag means a person must review every generated image before use. The `review_required` decision is stricter: it prevents provider access until the classification or configuration is resolved.

## Safe reason codes

| Code | Decision use |
|---|---|
| `ordinary_conceptual_topic` | Ordinary allowed request. |
| `sensitive_real_world_event` | Sensitive request allowed only with restrictions. |
| `documentary_fabrication_request` | Rejected request for synthetic photographic or documentary evidence. |
| `identifiable_person_misrepresentation` | Rejected misleading depiction of a real or identifiable person. |
| `safety_override_attempt` | Rejected attempt to disable or override backend controls. |
| `classification_uncertain` | Conservative review-required outcome. |
| `provider_safety_controls_unavailable` | Provider moderation is insufficient for automatic continuation. |

Each code has an understandable content-free message. The message never repeats article, draft, or user text.

## Misleading documentary imagery

The policy rejects user requests that ask for fabricated photographic or documentary evidence, including signals such as:

- Fake photographs or photographic evidence.
- Realistic breaking-news photographs.
- The exact moment of a real attack or disaster.
- Images made to look real or authentic.
- On-location or documentary evidence treatment.

A sensitive subject may still receive `allowed_with_restrictions` when the request supports a broad conceptual illustration. For example, a conflict topic can use symbolic humanitarian themes without depicting a battlefield, identifiable people, actual weapons use, casualties, or a specific event scene.

Rejecting one documentary request does not automatically approve a replacement. A new conceptual request must pass the complete policy again.

## Identifiable real people

The policy detects a bounded initial set of person markers, such as president, prime minister, senator, candidate, governor, mayor, minister, public figure, or named person.

When an identifiable-person marker appears with a sensitive event and the user asks to show or portray that person participating, acting, committing, or speaking, the request is rejected. User text is not evidence that a depicted action, event, statement, or appearance is accurate or authorised.

This is intentionally conservative and incomplete. A future named-entity service may improve detection, but model-assisted classification must not be treated as infallible or allowed to weaken these backend rules.

## Untrusted article, draft, and user text

NFA-49 receives the structured NFA-48 prompt result. It reads only the marked `UNTRUSTED_IMAGE_CONTEXT_JSON` block for classification and does not retain that text.

- Article content remains untrusted data.
- An associated LinkedIn draft remains untrusted derived data.
- Optional user description remains a masked secret string.
- Embedded instructions cannot change the policy, enable photorealism, or disable restrictions.
- User text is inspected for explicit unsafe intent but is never treated as application configuration.

An article containing text such as "ignore safety" does not override the policy. Explicit attempts in the user's own request to disable safety are rejected.

## Frontend override prevention

`ImageSafetyRequest` accepts only:

- The completed NFA-48 image-prompt package.
- An optional bounded, masked user description.

It forbids extra properties. It has no frontend-controlled fields for decision, safety level, provider-call permission, photorealism, documentary use, AI designation, categories, reason code, or review state.

Provider capabilities are injected into `ImageSafetyService` from trusted backend configuration rather than accepted from the request. A frontend cannot claim that unavailable provider controls exist.

## Provider safety controls

The backend records whether the configured future provider supports:

- Prompt moderation.
- Output moderation.
- A strict safety level.
- Content credentials or equivalent provenance features.

For every request, the result tells the future adapter which available controls to enable. Sensitive and uncertain requests enable the strict safety level when available. Content credentials are requested when available.

Prompt and output moderation are essential for automatic provider access:

- A sensitive request without both is rejected.
- An ordinary request without both becomes `review_required` and cannot continue automatically.

Application rules remain mandatory even when the provider has strong moderation. Provider safety is defence in depth, not the only policy.

## Conservative uncertainty handling

Malformed composer context or explicit uncertainty markers produce the `uncertain` category and `review_required` decision. The provider call is blocked.

The system does not convert an uncertain classification into an ordinary topic. A human must review the source and classification, or the request must be corrected and evaluated again.

## Safe decision metadata

`ImageSafetyService` can send `ImageSafetyDecisionRecord` to a recorder boundary. The safe record contains only:

- Evaluation ID.
- Policy version.
- Article and optional generation IDs.
- Decision and reason code.
- Sensitive category labels.
- Provider-call gate.
- Review flag.
- Photorealism flag.
- Required AI-generated designation.
- Evaluation timestamp.

It does not contain article content, a LinkedIn draft, user instructions, prompt text, provider payloads, generated images, personal details, or secrets.

NFA-49 defines this recording contract and proves it with an in-memory recorder. A future persistence task must add reviewed retention, access-control, and deletion rules before storing decisions in PostgreSQL.

## Policy versioning

Current identifier: `image_safety_v1`

| Version | Date | Change |
|---|---|---|
| `image_safety_v1` | 30 October 2026 | Initial sensitive categories, four decisions, documentary-evidence rejection, real-person safeguards, conceptual restriction, override protection, provider-control requirements, conservative uncertainty, AI designation, human review, and content-free records. |

Material classification, decision, or restriction changes require a new version and regression tests. Do not silently change the meaning of a version already recorded against image requests.

## Automated verification

Run the focused checks from the repository root:

```bash
apps/api/.venv/bin/ruff check \
  apps/api/app/models/image_safety.py \
  apps/api/app/policies \
  apps/api/app/services/image_safety.py \
  apps/api/tests/test_image_safety.py
apps/api/.venv/bin/ruff format --check \
  apps/api/app/models/image_safety.py \
  apps/api/app/policies \
  apps/api/app/services/image_safety.py \
  apps/api/tests/test_image_safety.py
apps/api/.venv/bin/pytest -q apps/api/tests/test_image_safety.py
```

The focused suite covers:

- An ordinary technology topic.
- Every defined sensitive category.
- Conflict documentary fabrication.
- Fake disaster evidence.
- Conceptual restrictions.
- Identifiable-person misrepresentation.
- Frontend and text-based override attempts.
- Prompt injection in article context.
- Conservative uncertain classification.
- Missing provider moderation for ordinary and sensitive topics.
- Content-free policy recording.
- Masked user text.
- Timestamp validation.

All tests use original synthetic data. They make no CNN, OpenAI, or image-provider request and require no API credential.

Verified locally on 30 October 2026:

- The focused NFA-49 image safety run passed 19 tests.
- The complete backend run passed 348 tests and safely skipped 13 opt-in PostgreSQL and live-model tests.
- Branch-aware backend coverage measured 81.01 percent, above the enforced 75 percent floor.
- Ruff linting and formatting checks passed for all 149 Python files.

## Implementation evidence

| Deliverable | Repository location |
|---|---|
| Decision, capability, request, result, and record models | `apps/api/app/models/image_safety.py` |
| Sensitive categories and deterministic central policy | `apps/api/app/policies/sensitive_news.py` |
| Pre-provider evaluation and recording service | `apps/api/app/services/image_safety.py` |
| Automated tests | `apps/api/tests/test_image_safety.py` |
| Technical documentation | `docs/image-safety-policy.md` |

## Limitations and human review

- Keyword rules cannot understand every news topic, euphemism, language, person, or deceptive intent.
- A non-sensitive classification is not a guarantee that an image is safe.
- Prompt rules and provider moderation cannot guarantee compliant output.
- NFA-49 does not inspect pixels, detect copied images, recognise faces, verify content credentials, or compare an output with restricted source assets.
- NFA-49 does not add a provider, endpoint, database table, user interface, image storage, or publishing capability.
- Human review must confirm accuracy, non-deception, dignity, rights, accessibility, AI designation, and suitability before use.
- Future model-assisted classification must use conservative thresholds, preserve deterministic rules, record its version, and route uncertainty to review.
- Live CNN material remains blocked by ADR-001 until written authorisation and a revised Go decision exist.

NFA-49 is implemented and ready for Mashood Ogunbiyi's review. Move the Jira issue to Done only after the pull request is merged and final GitHub evidence is attached.
