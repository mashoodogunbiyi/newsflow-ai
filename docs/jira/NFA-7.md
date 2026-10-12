# NFA-7 - Privacy, Copyright, and AI Safety Review

## 1. Document control

| Field | Value |
|---|---|
| Project | NewsFlow AI |
| Jira issue | NFA-7 |
| Project-plan task | T0.5 - Complete privacy, copyright, and AI safety review |
| Version | 1.0 |
| Status | Approved risk and safeguards baseline |
| Review date | 12 October 2026 |
| Approved | 12 October 2026 |
| Owner | Mashood Ogunbiyi |
| Requirements baseline | [NFA-3 - Baseline Requirements and Acceptance Criteria](NFA-3.md) |
| Access research | [NFA-4 - CNN Data Access Research](NFA-4.md) |
| Authorisation decision | [NFA-5 - CNN Authorisation Record](NFA-5.md) |
| Source data contract | [NFA-6 - Source Data Contract](NFA-6.md) |
| Repository path | `docs/jira/NFA-7.md` |

### Revision history

| Version | Date | Change | Author |
|---|---|---|---|
| 1.0 | 12 October 2026 | Reviewed privacy, copyright, hallucination, and generated-image risks and approved the required safeguards | Mashood Ogunbiyi |

### Approval

Mashood Ogunbiyi has reviewed and approved this risk and safeguards baseline as the project and document owner. The approval permits continued development with original synthetic fixtures under the controls in this document.

This approval does not authorise live CNN retrieval, storage, OpenAI processing, or derivative publication. NFA-5 remains the controlling authorisation decision. A live-source approval requires written permission, a revised source contract, and a new review of the affected risks.

| Role | Name | Decision | Date |
|---|---|---|---|
| Project and document owner | Mashood Ogunbiyi | Approved | 12 October 2026 |
| Technical reviewer | Mashood Ogunbiyi | Self-reviewed and accepted for the current solo phase | 12 October 2026 |

## 2. Purpose

This document identifies privacy, copyright, and AI-related risks created when NewsFlow AI retrieves news information and generates LinkedIn posts and supporting images. It records the safeguards required before implementation and defines the conditions that block live use or release.

The review covers:

- Copyright, content licensing, attribution, and reuse.
- Personal information in news, user accounts, prompts, outputs, logs, and saved content.
- Hallucination, factual distortion, false quotation, and prompt injection.
- AI-generated image safety, originality, disclosure, and sensitive-news treatment.
- Technical, product, review, and governance safeguards.

This document is a project risk assessment and is not legal advice. Professional legal or data-protection advice may be required before a public or commercial live-source release.

## 3. Review outcome

The current decision is a conditional go for synthetic-fixture development and a no-go for live CNN content.

| Area | Decision |
|---|---|
| Original synthetic fixtures | Approved for development and testing |
| Live CNN retrieval | Blocked by NFA-5 |
| Live CNN content sent to OpenAI | Not authorised |
| Generated LinkedIn drafts | Allowed only from approved synthetic fixtures during development |
| AI-generated images | Allowed only with the image safeguards in this document |
| Automatic LinkedIn publishing | Prohibited |
| Manual user review | Required before copy, download, or external publication |
| Public release | Blocked until all release safeguards and go/no-go conditions pass |

No safeguard in this document converts technical access into content permission. Written rights and a provider-specific contract remain mandatory for live use.

## 4. Review method and rating scale

Each risk is assessed using likelihood and impact scores from 1 to 5.

| Score | Likelihood | Impact |
|---:|---|---|
| 1 | Rare | Negligible |
| 2 | Unlikely | Minor |
| 3 | Possible | Moderate |
| 4 | Likely | Major |
| 5 | Almost certain | Severe |

Risk score equals likelihood multiplied by impact.

| Score | Rating | Required response |
|---:|---|---|
| 1 to 4 | Low | Record and monitor |
| 5 to 9 | Medium | Implement planned safeguards and test them |
| 10 to 15 | High | Safeguards are mandatory before release |
| 16 to 25 | Critical | Stop the affected activity until the risk is reduced |

Residual ratings in this document assume every listed safeguard is implemented and verified. If a safeguard is missing or fails, use the initial rating and block the affected operation where required.

## 5. Copyright and content reuse review

### 5.1 Requirements reviewed

CNN International Commercial states that its site material, including text, images, illustrations, audio, and video, is protected by copyright, trademark, and other intellectual-property rights. Its published terms restrict copying, modification, republication, transmission, and distribution without prior written consent, and state that permitted copying must preserve required attribution, trademark, and copyright notices.

For NewsFlow AI, this means:

- Public availability is not permission for automated retrieval or reuse.
- A link to CNN does not grant the right to copy article text or images.
- Attribution is mandatory when required, but attribution alone does not grant permission.
- Rights may differ between titles, descriptions, article text, quotations, photographs, logos, video, and other media.
- Permission to store content does not automatically include permission to send it to OpenAI or create an externally published derivative.
- The project must use the smallest licensed content set capable of supporting grounded generation.
- CNN photographs, logos, watermarks, and trade dress are excluded unless separately and explicitly licensed.
- Generated posts must be original summaries or commentary, not substitutes for or substantial reproductions of the source.
- Licence expiry, correction, withdrawal, retention, and deletion rules must be enforceable in the application.

### 5.2 Copyright and reuse risks

| ID | Risk | Initial rating | Mandatory safeguards | Residual rating |
|---|---|---|---|---|
| CR-01 | Live CNN material is retrieved without written permission | Critical | Keep every live adapter disabled; require an approved NFA-5 decision and provider profile; reject live sync with `SOURCE_NOT_AUTHORISED` | Low |
| CR-02 | More fields or content are stored than the licence permits | High | Use the NFA-6 allowlist and rights flags; reject unknown fields; test metadata-only and content-not-permitted states | Low |
| CR-03 | CNN article wording is reproduced too closely in a LinkedIn draft | High | Generate from a bounded fact pack; prohibit substantial copying; compare outputs with supplied source text; reject suspiciously similar output; permit quotations only when licensed and verified | Medium |
| CR-04 | Attribution, byline, copyright wording, or canonical URL is missing | High | Make attribution a required structured field; block generation and export with `ATTRIBUTION_INCOMPLETE`; protect attribution from accidental deletion | Low |
| CR-05 | CNN photographs, logos, watermarks, or branding are copied into generated images | Critical | Never submit CNN media as an image reference; prohibit CNN branding in prompts; moderate and review outputs; reject lookalike branding and photograph recreation | Low |
| CR-06 | Third-party rights within a CNN item are assumed to belong to CNN | High | Treat photographs, quotations, agency material, and partner content as separately restricted unless the licence expressly covers them | Medium |
| CR-07 | A provider licence changes, expires, or is terminated while ingestion continues | High | Store licence reference and expiry; fail closed on expiry; monitor changes; stop retrieval and apply deletion duties | Low |
| CR-08 | A user adds copied or infringing material during editing | Medium | Provide acceptable-use guidance; moderate user instructions; maintain reporting and deletion controls; require user confirmation before external use | Medium |

No fixed word count or similarity percentage is treated as a legal safe harbour. The system must follow the actual licence and use conservative originality checks.

## 6. Privacy review

### 6.1 Personal-information flows

Potential personal information may appear in:

- User registration, authentication, session, and account records.
- News information about public figures, private individuals, victims, witnesses, children, patients, or alleged offenders.
- User-provided post edits and image instructions.
- Source facts, prompts, generated text, generated images, and saved content.
- Application logs, request identifiers, moderation results, and audit records.
- Data transmitted to OpenAI as a processor or service provider.

The ICO states that AI projects must assess security and privacy risks, process only personal information needed for a defined purpose, protect it against unauthorised processing or loss, and document high-risk processing through a data protection impact assessment where required. Its guidance also recommends early risk assessment, clear data flows, retention controls, and privacy by design.

OpenAI's current API data-controls documentation states that API inputs and outputs are not used to train OpenAI models unless the customer explicitly opts in. It also states that abuse-monitoring logs may contain prompts, responses, and related metadata and are normally retained for up to 30 days, subject to the documented controls and exceptions. These terms must be rechecked before release because provider behaviour and available controls can change.

### 6.2 Privacy risks

| ID | Risk | Initial rating | Mandatory safeguards | Residual rating |
|---|---|---|---|---|
| PR-01 | The project collects more user or source personal information than necessary | High | Maintain a data inventory; document each purpose; minimise fields; prohibit speculative collection; use synthetic fixtures during development | Low |
| PR-02 | Sensitive or unnecessary personal information is sent to OpenAI | High | Build prompts only from allowed fact-pack fields; redact contact details and unique identifiers when not essential; block special-category or highly sensitive data unless specifically reviewed | Medium |
| PR-03 | Users are not told how their account data and prompts are processed | High | Publish a clear privacy notice before user testing or release; state purposes, processors, retention, rights, and contact route | Low |
| PR-04 | OpenAI storage and abuse-monitoring behaviour is misunderstood | High | Record the selected endpoint and data-control configuration; use `store: false` where supported; document default provider retention; reassess before release | Medium |
| PR-05 | Prompts, source text, or outputs leak through application logs | High | Use structured redacted logs; never log full prompts by default; never log secrets; restrict log access and retention | Low |
| PR-06 | One user can access another user's drafts, images, or history | Critical | Enforce object-level authorisation on every operation; test with two users; return `403` or `404`; use private object-storage access | Low |
| PR-07 | Personal data is retained after it is no longer needed | High | Define retention by record type; implement account and content deletion; expire temporary files and provider data; test deletion | Medium |
| PR-08 | Generated content exposes private, defamatory, or unverified claims about a person | Critical | Require factual claim mapping; block unsupported personal claims; use sensitive-news review; require human approval; provide reporting and takedown processes | Medium |
| PR-09 | Stable safety identifiers expose direct personal information | Medium | Use a one-way hashed internal user identifier rather than email, name, or another direct identifier | Low |
| PR-10 | A new live use changes the privacy risk without reassessment | High | Complete DPIA screening before live testing; update the data map and this review when purpose, source, fields, processor, or audience changes | Low |

### 6.3 Privacy decisions required before release

Before real user or live-source data is processed, the project owner must:

1. Complete and record DPIA screening.
2. Identify the controller and processor roles.
3. Record a lawful basis for each personal-data purpose.
4. Publish the privacy notice and retention schedule.
5. Confirm the OpenAI endpoint, storage setting, abuse-monitoring retention, and any regional controls in use.
6. Test access, deletion, export, logging, and incident-response controls.
7. Seek appropriate specialist advice if residual risk remains high.

## 7. AI hallucination and text-generation review

### 7.1 Hallucination risks

| ID | Risk | Initial rating | Mandatory safeguards | Residual rating |
|---|---|---|---|---|
| AI-01 | The model invents a fact not present in the selected source | Critical | Generate only from an immutable bounded fact pack; require structured claim-to-fact mappings; reject unknown or unmapped facts | Medium |
| AI-02 | The model combines the selected item with facts from memory or another story | High | Instruct the model to use only supplied facts; send no unrelated articles; validate every factual claim; refuse when the source is insufficient | Medium |
| AI-03 | A quotation, number, date, name, or job title is altered | Critical | Mark exact values in structured facts; allow direct quotations only when present and permitted; compare generated values with source facts | Medium |
| AI-04 | Opinion or speculation is presented as CNN-reported fact | High | Separate `reported_fact` from `analysis`; require qualifying language; reject outputs that misattribute interpretation to CNN | Medium |
| AI-05 | A thin source produces a confident but unsupported post | High | Calculate source sufficiency before generation; return `INSUFFICIENT_SOURCE_FACTS`; do not ask the model to fill gaps | Low |
| AI-06 | Malicious instructions inside source text redirect the model | High | Treat source text as untrusted quoted data; delimit it from system instructions; remove active markup; red-team prompt injection; allow no source-controlled tools | Medium |
| AI-07 | An article correction or update does not reach an existing draft | High | Store immutable snapshot time and source version; show source date; mark affected drafts for review when corrections or withdrawals are received | Medium |
| AI-08 | Tone or hashtags make a sensitive story sensational, discriminatory, or harmful | High | Apply sensitive-topic classification; use neutral professional tone; moderate input and output; require human review | Medium |
| AI-09 | Users mistake a generated draft for approved or published journalism | Medium | Label drafts as AI-generated suggestions; show the source link; keep publishing manual; never present output as CNN-authored | Low |

### 7.2 Text safeguards

The text-generation service must:

- Use one selected immutable source snapshot per generation.
- Build a numbered fact pack from permitted fields only.
- Require structured output containing claims and supporting fact IDs.
- Reject unknown fact IDs, unmapped factual claims, altered quotations, and unsupported numbers.
- Refuse generation when evidence is missing, restricted, or insufficient.
- Keep the source and system instructions separate and treat source text as untrusted.
- Request neutral, professional wording for sensitive stories.
- Include required attribution and the canonical URL.
- Run input and output safety checks and apply project-specific rules in addition to provider moderation.
- Preserve model, prompt, contract, and source-snapshot versions for audit and evaluation.
- Require the user to review and edit the result before copying or downloading it.

## 8. AI-generated image safety review

OpenAI's image-generation documentation states that prompts and generated images are filtered under its content policy and that the API can return a moderation-blocked error. OpenAI also provides a moderation API for classifying text and images. These provider controls support the application but do not replace NewsFlow AI's own safety rules and human review.

The project must use the standard `auto` image moderation setting. The less restrictive `low` setting must not be enabled without a documented change review and approval.

### 8.1 Image risks

| ID | Risk | Initial rating | Mandatory safeguards | Residual rating |
|---|---|---|---|---|
| IMG-01 | A generated image appears to be a real photograph of a news event | Critical | Use conceptual or editorial-illustration prompts for news; avoid documentary camera language; label the preview and download as AI-generated | Medium |
| IMG-02 | A real person is shown doing something that did not happen | Critical | Default to no photorealistic identifiable people; use symbolic or non-identifiable figures; require enhanced review for any real-person reference | Medium |
| IMG-03 | The image recreates CNN photography, logos, watermarks, or visual branding | Critical | Do not provide CNN images as references; prohibit CNN branding in prompts; reject similar outputs during review | Low |
| IMG-04 | Conflict, crime, disaster, health, or death is shown graphically or exploitatively | Critical | Use abstract, respectful, non-graphic treatment; block graphic injury, bodies, humiliation, or sensational imagery | Medium |
| IMG-05 | The image reinforces stereotypes or discriminatory associations | High | Use neutral descriptions; avoid inferring protected characteristics; test diverse sensitive fixtures; review flagged outputs | Medium |
| IMG-06 | User image instructions request harassment, sexual content, violence, impersonation, or deception | High | Validate and moderate instructions before generation; reject prohibited requests; rate-limit repeated abuse | Low |
| IMG-07 | A provider moderation block is automatically retried unchanged | Medium | Handle `moderation_blocked` as a user-correctable failure; do not retry unchanged prompts; show a safe generic message and log only necessary metadata | Low |
| IMG-08 | Generated-image files expose another user's content or unsafe metadata | High | Store privately; authorise each download; use safe filenames and MIME checks; remove unnecessary metadata; apply deletion rules | Low |
| IMG-09 | A user publishes an image without understanding that it is synthetic | High | Show persistent AI-generated disclosure in preview and export workflow; require explicit user review before download | Low |

### 8.2 Image prompt requirements

Every image prompt must:

- Use only validated source facts and approved user instructions.
- Ask for an original conceptual or editorial illustration.
- Prohibit CNN logos, branding, watermarks, interfaces, and source-photograph recreation.
- Avoid unsupported factual visual details.
- Avoid photorealistic depictions of identifiable people by default.
- Use respectful non-graphic treatment for sensitive subjects.
- Avoid text that looks like an official CNN headline, label, or endorsement.
- Include no unnecessary personal information.

Every returned image must remain unavailable for download until ownership, MIME type, storage, moderation outcome, and disclosure requirements pass.

## 9. Approved safeguard baseline

| Safeguard ID | Safeguard | Verification |
|---|---|---|
| SG-01 | Live-source fail-closed control | With no approved live profile, sync returns `SOURCE_NOT_AUTHORISED` and makes no network request |
| SG-02 | Field and rights allowlist | Contract tests reject unknown, restricted, or permission-ambiguous fields |
| SG-03 | Attribution lock | Generation and export fail if source name, canonical URL, or required wording is missing |
| SG-04 | Data minimisation and privacy map | Each personal-data field has a purpose, access rule, retention rule, and deletion path |
| SG-05 | OpenAI data-control configuration | Endpoint, `store` setting, retention behaviour, region, and review date are recorded before release |
| SG-06 | Object-level authorisation | Two-user tests prove no cross-user read, edit, regenerate, download, or delete access |
| SG-07 | Grounded structured output | Every factual claim maps to valid fact IDs; invalid mappings fail validation |
| SG-08 | Source sufficiency gate | Thin or restricted fixtures refuse generation instead of filling gaps |
| SG-09 | Prompt-injection defence | Adversarial source fixtures cannot override system rules or invoke tools |
| SG-10 | Text and image moderation | Inputs and outputs are checked before display, storage, or download where applicable |
| SG-11 | Sensitive-news policy | Conflict, crime, disaster, health, election, death, and identifiable-person fixtures use neutral text and conceptual images |
| SG-12 | Human review and manual publication | No generated text or image is automatically published to LinkedIn |
| SG-13 | AI-image disclosure | Preview and export workflow clearly identify generated imagery as AI-generated |
| SG-14 | Redacted audit trail | Store request IDs, versions, outcomes, and safe error codes without secrets or full sensitive prompts |
| SG-15 | Evaluation and red-team gate | Release tests cover hallucination, copying, privacy, prompt injection, bias, unsafe imagery, and moderation failures |
| SG-16 | Incident response and takedown | Document how to disable generation, remove content, preserve evidence safely, and notify affected parties where required |

## 10. Prohibited behaviour

NewsFlow AI must not:

- Scrape CNN pages or bypass access controls.
- Enable live CNN ingestion without written permission and an approved source profile.
- Send live CNN content to OpenAI under the current NFA-5 decision.
- Reproduce substantial CNN article text or unlicensed quotations.
- Copy or regenerate CNN photographs, logos, watermarks, or branding.
- Invent missing facts, quotations, names, numbers, dates, or locations.
- Generate a post when the source is insufficient or attribution is incomplete.
- Automatically publish generated content to LinkedIn.
- Create deceptive documentary-style images of events that did not occur.
- Create unsupported depictions of identifiable people.
- Use personal information in prompts when it is not necessary and approved.
- Expose credentials, full sensitive prompts, or another user's content in logs or errors.
- Lower provider moderation settings to bypass a blocked request.

## 11. Testing and review approach

The implementation must include automated and human-reviewed tests for:

- Live-source requests while authorisation is absent.
- Metadata-only, content-missing, content-not-permitted, and expired-rights records.
- Missing attribution and altered canonical URLs.
- Outputs that copy distinctive source sentences or unlicensed quotations.
- Thin sources and requests that encourage invention.
- Altered names, dates, numbers, quotations, and job titles.
- Unmapped claims and unknown fact IDs.
- Prompt injection and unsafe markup inside source content.
- Personal contact details and unnecessary sensitive information in facts and user instructions.
- Cross-user access to drafts and images.
- Retention, deletion, and redacted logging.
- Sensitive-news tone and image treatment.
- Photorealistic event imagery, identifiable-person depictions, logos, and watermarks.
- Input moderation, output moderation, provider blocks, and safe error handling.
- Persistent AI-generated image disclosure.

Release evaluation must use original synthetic fixtures covering Technology, Business, World News, Science, thin sources, sensitive stories, and adversarial inputs. A critical failure blocks release.

## 12. Go/no-go conditions

### Development go

Development may continue when:

- Only original synthetic fixtures are used.
- The NFA-6 fixture contract is enforced.
- OpenAI requests contain no copied CNN content.
- Generated drafts and images remain development outputs subject to human review.

### Live-source no-go

Live-source implementation or testing remains blocked until:

- NFA-5 records suitable written authorisation.
- The exact permitted fields, OpenAI processing, derivative output, retention, deletion, and attribution terms are documented.
- NFA-6 is revised with an approved live-provider profile.
- DPIA screening and any required assessment are complete.
- The safeguards in Section 9 are implemented and tested.
- The NFA-8 architecture decision records a go decision.

### Release no-go

Public release is blocked if any critical risk remains unresolved, a required safeguard is missing, provider terms are unclear, or the project cannot reliably prevent unsupported factual or misleading visual output.

## 13. Monitoring and change control

This review must be updated when:

- A live provider, licence, dataset, or field changes.
- OpenAI models, endpoints, storage, data controls, moderation, or policies change.
- The application accepts new personal information, uploads, or user roles.
- Automatic publishing, additional news sources, or new output channels are proposed.
- A safety incident, complaint, takedown request, or material test failure occurs.
- A risk rating or safeguard is shown to be inaccurate or ineffective.

At minimum, the controls and external source links must be rechecked before live testing and before release.

## 14. Evidence sources

The review used the project baseline and the following first-party sources, checked on 12 October 2026:

| Source | Evidence used |
|---|---|
| [CNN International Commercial terms](https://commercial.cnn.com/terms-of-use/) | Copyright and trademark protection, reuse restrictions, written-consent requirement, and preservation of attribution and notices |
| [OpenAI image generation guide](https://developers.openai.com/api/docs/guides/image-generation) | Prompt and output filtering, image moderation settings, and blocked-request handling |
| [OpenAI moderation guide](https://developers.openai.com/api/docs/guides/moderation) | Text and image classification and use of moderation results before showing output |
| [OpenAI safety best practices](https://developers.openai.com/api/docs/guides/safety-best-practices) | Moderation, adversarial testing, prompt-injection testing, and safety identifiers |
| [OpenAI data controls](https://developers.openai.com/api/docs/guides/your-data) | API training position, abuse-monitoring retention, application state, and available data controls |
| [ICO security and data minimisation in AI](https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/artificial-intelligence/guidance-on-ai-and-data-protection/how-should-we-assess-security-and-data-minimisation-in-ai/) | Security, data-flow records, minimisation, deletion, and privacy by design |
| [ICO AI accountability and governance](https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/artificial-intelligence/guidance-on-ai-and-data-protection/what-are-the-accountability-and-governance-implications-of-ai/) | Risk assessment, DPIA screening, roles, safeguards, residual risk, and reassessment |

External terms and guidance can change. These links support this project decision but do not replace the final provider agreement or specialist advice.

## 15. Acceptance-criteria traceability

| Acceptance criterion | Evidence in this document | Result |
|---|---|---|
| Copyright and content reuse requirements reviewed | Section 5 | Complete |
| Privacy risks documented | Section 6 | Complete |
| AI hallucination risks identified | Section 7 | Complete |
| AI-generated image safety requirements documented | Section 8 | Complete |
| Recommended safeguards recorded | Section 9 | Complete |

## 16. Review and Jira decision

NFA-7 is complete and approved by Mashood Ogunbiyi for the current fixture-first project state. All five Jira acceptance criteria are satisfied by this document.

The next workflow actions are:

1. Review the Markdown preview and request any required changes.
2. Commit and merge this document and the README update through the normal GitHub workflow.
3. Add the final document, pull-request, and commit links to NFA-7 in Jira.
4. Move NFA-7 to Done after the evidence links are recorded.
5. Continue to NFA-8 - Record go/no-go ADR.
6. Keep live CNN retrieval disabled unless NFA-5, NFA-6, NFA-7, and NFA-8 are formally revised or satisfied.

The practical project state is:

- Copyright and reuse risks are reviewed.
- Privacy risks and required pre-release decisions are documented.
- Hallucination and prompt-injection controls are defined.
- AI-generated image safety and disclosure requirements are defined.
- Synthetic-fixture development may continue under the approved safeguards.
- Live CNN ingestion remains blocked.
