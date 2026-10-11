# NFA-4 - CNN Data Access Research

## 1. Document control

| Field | Value |
|---|---|
| Project | NewsFlow AI |
| Jira issue | NFA-4 |
| Project-plan task | T0.2 - Investigate CNN access options |
| Version | 1.0 candidate |
| Status | Research complete - ready for review |
| Research date | 11 October 2026 |
| Researcher | Mashood Ogunbiyi |
| Related baseline | [NFA-3 - Baseline Requirements and Acceptance Criteria](NFA-3.md) |
| Repository path | `docs/jira/NFA-4.md` |

### Revision history

| Version | Date | Change | Author |
|---|---|---|---|
| 1.0 candidate | 11 October 2026 | Initial investigation of CNN APIs, RSS, licensing, third-party providers, permitted fields, limitations, and recommended approach | Mashood Ogunbiyi |

## 2. Purpose

This document records the research completed for Jira issue NFA-4. It evaluates possible ways for NewsFlow AI to retrieve CNN news information without unauthorised scraping or access-control bypass.

This is a technical and project compliance assessment, not legal advice. A public URL or technically accessible feed is not, by itself, permission to copy, store, send to an AI provider, transform, or republish content. Written licensing terms must define the final permitted use.

## 3. Executive conclusion

The research reached the following conclusions:

- No publicly documented, self-service CNN article API was found on CNN's current public, help, commercial, or Newsource websites.
- CNN does offer licensed content access and syndication through CNN International Commercial and CNN Newsource. This is the strongest direct and authoritative route, but it requires contact with CNN and a written agreement.
- Older public CNN RSS endpoints still respond, but the feeds are stale. The most recent item found in the `cnn_latest.rss` feed was dated 22 August 2024. No current CNN statement was found granting NewsFlow AI permission to use those feeds for automated AI processing or derivative LinkedIn content.
- CNN Newsource documentation describes credentialed article, video, and bundle feeds. Access to specific assets is controlled by the customer's licence. These feeds are not a public API.
- LexisNexis Nexis Data+ is a possible licensed third-party route. Its public material describes licensed news APIs and lists CNN among broadcast transcript sources, but it does not prove that current CNN.com article content or NewsFlow AI's intended generative-AI use is included. Contract confirmation is required.
- NewsAPI and search-generated feeds can help discover links, but they do not provide CNN content rights. NewsAPI also states that it does not provide full article content.
- Direct CNN website scraping, custom scraping feeds, paywall bypass, access-control bypass, and copying CNN images are rejected.

### Recommendation

Use a two-route licensing investigation:

1. Contact CNN International Commercial or CNN Newsource first and request a licensed feed or service whose written terms expressly cover NewsFlow AI's use case.
2. In parallel, request a proposal from LexisNexis Nexis Data+ and require written confirmation of current CNN article coverage, permitted fields, OpenAI processing, storage, derivative content, attribution, and retention.

Do not select or enable a live CNN adapter until NFA-5 records written authorisation. Development may continue with synthetic fixtures that contain no copied CNN article text.

## 4. Research method and decision rules

The investigation used the following rules:

- Prefer current, first-party CNN and provider documentation.
- Treat historical product documents as evidence of a possible service, not proof of a current entitlement.
- Separate technical availability from legal permission.
- Reject any approach that depends on scraping, bypassing restrictions, or assuming that public availability equals reuse permission.
- Require a written answer for any right that is essential to NewsFlow AI.

The following questions were applied to each option:

- Is the source operated by CNN or a provider authorised to license the content?
- Is the source current and technically reliable?
- Which fields and media types are included?
- May the data be stored, cached, and retained?
- May the data be sent to OpenAI for automated processing?
- May original derivative LinkedIn posts be generated and used externally?
- What attribution, link, deletion, volume, and rate requirements apply?
- Is further authorisation, a paid contract, or credentials required?

## 5. Access methods evaluated

### 5.1 Public official CNN API

**Finding:** No public, self-service CNN article API or current public developer portal was found.

CNN's public commercial pages direct organisations that want to license content to CNN International Commercial. CNN Newsource describes a syndication platform for publishers and newsrooms, rather than an open developer API.

**Limitations:**

- There is no public API documentation, public sign-up flow, published schema, rate limit, pricing, or general-purpose API key process to implement against.
- Search results cannot prove that no private or partner API exists.
- A private feed or integration may be offered after commercial review.

**Decision:** Not available as a public implementation route. Ask CNN whether a licensed API or feed is available for this use case.

**Additional authorisation required:** Yes.

### 5.2 Public CNN RSS feeds

Example legacy endpoints include:

- `http://rss.cnn.com/rss/edition.rss`
- `http://rss.cnn.com/rss/cnn_latest.rss`
- `http://rss.cnn.com/rss/cnn_topstories.rss`

**Technical finding:** The endpoints can still return XML over HTTP, but they are not a current news source. A direct inspection on 11 October 2026 found that `cnn_latest.rss` had no item newer than 22 August 2024. An independent feed review updated in September 2026 also reported that the old CNN feeds had not received new stories since 2024.

**Permission finding:** No current first-party RSS licence was found that expressly permits NewsFlow AI to store feed content, send it to OpenAI, generate derivative posts, or use it commercially. RSS is a delivery format, not a grant of copyright or reuse rights.

**Limitations:**

- The feeds are stale and cannot satisfy the requirement for recent news.
- The old CNN RSS information page no longer provides a current feed directory.
- Available fields are too limited for reliable factual grounding in many cases.
- Feed availability, categories, schemas, and update behaviour are not supported by a current service commitment.
- The absence of clear AI-processing and derivative-use permission creates an unacceptable rights risk.

**Decision:** Reject as the NewsFlow AI production source.

**Additional authorisation required:** Yes, even if CNN resumes a public feed.

### 5.3 CNN International Commercial and CNN Newsource

CNN International Commercial states that it licenses news, programming, and archive material. It identifies CNN Newsource as a service that syndicates CNN and partner content. CNN Newsource describes digital news services for publishers, including text, photos, graphics, and other content.

Older CNN Newsource technical documentation describes credentialed Media RSS feeds for articles, videos, and bundles. It also states that the assets visible to a customer depend on the licences in place. This supports the conclusion that Newsource is a licensed, controlled service rather than an open feed.

Potential fields shown in historical Newsource article-feed documentation include:

- Provider identifier or GUID.
- Headline and mobile headline.
- First published and modified dates.
- Categories.
- Dateline and article information.
- Images and other linked assets where separately licensed.

**Limitations:**

- A commercial agreement, credentials, eligibility review, and likely fees are required.
- Public documents do not state the current price, rate limits, complete schema, service-level terms, or retention rules.
- The historical feed documentation must not be treated as the current contract or current technical specification.
- CNN may license text, images, video, and publishing rights separately.
- A standard syndication right may not automatically permit use with a generative-AI provider or the creation of derivative social-media posts.
- CNN Newsource mainly serves news organisations and publishers, so NewsFlow AI's eligibility must be confirmed.

**Decision:** Preferred direct route, subject to written confirmation of the complete NewsFlow AI use case.

**Additional authorisation required:** Yes. A signed agreement or other written permission and access credentials are required.

### 5.4 LexisNexis Nexis Data+

LexisNexis describes Nexis Data+ as a global news API with licensed news, current and historical content, and provider-supported data access. Its public news-data page lists CNN among broadcast transcript sources.

This makes Nexis Data+ a credible provider to investigate, but the public page does not confirm that a NewsFlow AI subscription would include current CNN.com articles. It also does not, by itself, grant the right to send content to OpenAI or publish generated derivatives.

**Limitations:**

- Product access is commercial and pricing is not publicly fixed for this use case.
- CNN may be available only for particular content types, such as broadcast transcripts, territories, or date ranges.
- Rights vary by dataset, source, contract, user count, use case, and output type.
- A licence for search, monitoring, or internal analytics may not permit generative-AI processing or external social-media output.
- Storage, caching, excerpting, attribution, deletion, and model-processing rights must be written into the agreement.
- LexisNexis Newsdesk terms are limited to media monitoring and current awareness and must not be assumed to cover NewsFlow AI. The correct product and contract must be confirmed.

**Decision:** Viable secondary candidate only after a written rights and coverage review.

**Additional authorisation required:** Yes. A suitable Nexis Data+ contract and credentials are required.

### 5.5 NewsAPI and similar aggregators

NewsAPI aggregates information about publicly available web pages. Its terms state that third-party content may be protected by intellectual property rights and may not be used without a licence or other legal permission. Its pricing FAQ also states that full article content is not provided.

**Limitations:**

- Payment for the API does not purchase CNN reuse rights.
- CNN availability and fields can change.
- Results may contain only a headline, source, time, short description, image URL, and link.
- Full content is not provided.
- NewsAPI's suggestion that customers can scrape linked pages is not acceptable for this project because NewsFlow AI explicitly prohibits unauthorised scraping.
- Limited metadata may be insufficient for a grounded LinkedIn post.

**Decision:** Do not use as the production CNN content source. At most, reconsider it later for link discovery after separate CNN permission is obtained, but it would add little value if the licensed provider already supports discovery.

**Additional authorisation required:** Yes, from both the API provider for production use and the relevant content rights holder for the intended CNN use.

### 5.6 Google News feeds, custom feed tools, and direct scraping

Google News search feeds and custom feed tools can surface CNN links. They do not provide a CNN content licence. A custom feed built by monitoring CNN pages is functionally a scraping method and is outside the project's approved boundaries.

**Decision:** Reject as an ingestion method.

**Additional authorisation required:** Not applicable because this approach will not be implemented.

### 5.7 Synthetic development fixtures

Synthetic fixtures can model the proposed article schema without retrieving or copying live CNN content. They allow architecture, UI, database, grounding, and OpenAI integration work to continue while licensing is unresolved.

**Limitations:**

- Fixtures do not prove live-provider compatibility.
- Fixtures must be clearly labelled as synthetic and must not imitate or reproduce a CNN article.
- A live release remains blocked.

**Decision:** Approved for development and automated testing until NFA-5 records a live-source authorisation.

**Additional authorisation required:** No, provided the fixtures are original and contain no copied CNN content.

## 6. Comparison matrix

| Access method | Current content | Rights clarity | AI use confirmed | Key limitation | Result |
|---|---|---|---|---|---|
| Public CNN API | No public service found | None | No | No public implementation route | Not available |
| Legacy CNN RSS | No | Unclear | No | Stale since 2024 and no clear licence for this use | Rejected |
| CNN Newsource or direct CNN licence | Expected under contract | High after contract | Must be negotiated | Eligibility, cost, terms, and technical access unknown | Preferred candidate |
| LexisNexis Nexis Data+ | Provider-dependent | High after contract | Must be confirmed for the selected dataset | CNN article coverage and output rights unconfirmed | Secondary candidate |
| NewsAPI | Metadata only | Does not clear CNN rights | No | No full text and separate rights required | Rejected as primary source |
| Google News or custom feeds | Link discovery | Does not clear CNN rights | No | Not an authorised content licence | Rejected |
| Direct website scraping | Potentially current | Unauthorised | No | Violates the project constraint and may breach terms or controls | Prohibited |
| Synthetic fixtures | Deliberately not live | Clear if original | Yes for test content | Cannot support a live release | Approved for development only |

## 7. Field-level rights decision

The question is not only which fields a service can technically return. The contract must state which fields NewsFlow AI may retrieve and what may be done with each one.

### Current baseline before written authorisation

No live CNN field is approved for automated retrieval or OpenAI processing yet. Only original synthetic fixture fields are approved for development.

### Fields to request in a licence

| Field or operation | Why it is needed | Required permission or control | Current status |
|---|---|---|---|
| Provider article ID or GUID | Deduplication and traceability | Retrieval and internal storage | Not yet authorised |
| Headline | Article discovery and user selection | Retrieval, display, storage, and OpenAI input if used in generation | Not yet authorised |
| Canonical CNN URL | Attribution and access to the original source | Storage, display, and linking | Not yet authorised |
| Published and modified dates | Recency, ordering, and provenance | Retrieval and storage | Not yet authorised |
| Category or tags | Filtering and classification | Retrieval, normalisation, display, and storage | Not yet authorised |
| Description or provider summary | Discovery and possible fact-pack input | Retrieval, display, storage, and OpenAI input | Not yet authorised |
| Byline or author | Attribution | Retrieval, display, and storage with required wording | Not yet authorised |
| Article body or wire text | Sufficient facts for grounded generation | Explicit retrieval, storage, OpenAI processing, transformation, excerpting, retention, and deletion rights | Not yet authorised |
| Quotations | Accurate attribution where necessary | Explicit permitted length, context, attribution, and output rules | Not yet authorised |
| Images, captions, thumbnails, or video | Possible display or source context | Separate media rights, transformations, storage, delivery, credit, territory, and expiry rules | Excluded unless explicitly licensed |
| Licence or rights metadata | Automated policy enforcement | Retrieval and persistent storage | Required in the selected data contract |
| Sending permitted fields to OpenAI | AI generation | Express permission for automated processing by a third-party AI subprocessor | Not yet authorised |
| Generated LinkedIn draft | Product output | Express permission to create and externally use an original derivative summary or commentary | Not yet authorised |

### Minimum requested data

Request the smallest dataset capable of supporting the product:

- Provider ID.
- Headline.
- Canonical URL.
- Publication and modification times.
- Category.
- A licensed summary or sufficient licensed article text for factual grounding.
- Byline and mandatory attribution fields.
- Machine-readable rights, expiry, and deletion information where available.

CNN photographs, CNN branding, video, and other rich media are not required for the MVP. NewsFlow AI will generate a separate original illustration and will not use CNN media as an image-generation reference.

## 8. Required written permissions

NFA-5 must obtain evidence that answers all of the following before live integration is enabled:

- Does the service include current CNN International or CNN.com news articles suitable for the required categories?
- Which exact fields, content types, territories, languages, and date ranges are included?
- May NewsFlow AI retrieve the data automatically through an API, RSS, MRSS, FTP, or another feed?
- May NewsFlow AI store and cache each field, and for how long?
- Must an article or field be removed when the provider deletes, corrects, expires, or withdraws it?
- May permitted source data be sent to the OpenAI API for automated processing?
- May NewsFlow AI use the source facts to create an original LinkedIn draft for external publication?
- Are summaries, quotations, or excerpts allowed in the output, and what limits apply?
- What CNN attribution, link, copyright notice, logo, or brand wording is required or prohibited?
- May generated posts be saved indefinitely by the user, or must source-derived parts expire?
- Are generated posts limited to internal use, or may users publish them publicly on LinkedIn?
- What request limits, concurrency limits, update frequency, security controls, audit requirements, and service levels apply?
- May the project display provider-supplied images or thumbnails? The preferred answer for the MVP is to exclude them.
- Does the licence permit a development, test, demonstration, portfolio, and production environment?
- What fees, user limits, and termination duties apply?

An email, proposal, order form, contract, or licence schedule may provide the evidence. Secrets, credentials, private commercial terms, personal contact details, and confidential contract text must not be committed to GitHub. The repository should contain only a safe decision record that identifies the evidence owner and storage location.

## 9. Recommended implementation gate

The application should enforce the decision in configuration rather than relying on memory or process alone.

Recommended states:

- `fixture` - allowed now. Uses only original synthetic records.
- `disabled` - default for live CNN access.
- `cnn_newsource` - may be enabled only after NFA-5 approves a CNN agreement.
- `licensed_provider` - may be enabled only after NFA-5 approves the named provider and dataset.

Each live source configuration should record:

- Access-method decision ID.
- Provider and product name.
- Permitted fields.
- Permitted processing purposes.
- OpenAI-processing permission.
- External-output permission.
- Retention and deletion rules.
- Attribution requirements.
- Effective and expiry dates.
- Evidence owner and non-secret evidence location.

If the source lacks permission for article text or a sufficiently detailed licensed summary, the system must return `INSUFFICIENT_SOURCE` rather than generate a post from model memory.

## 10. Proposed licensing enquiry

The following text can be adapted for CNN International Commercial or a licensed provider. It is a draft only and has not been sent.

> NewsFlow AI is a software project that allows a user to discover recent CNN news, select an article, and create an original professional LinkedIn draft and an original AI-generated illustration. The product would retrieve only licensed source fields, show attribution and a canonical CNN link, and require human review before any external publication. We need written confirmation of available API or feed access, included article fields, storage and retention rights, permission to send licensed text to the OpenAI API for automated processing, permission to create and publish original derivative summaries or commentary on LinkedIn, attribution requirements, rate limits, territories, fees, and deletion duties. We do not intend to scrape CNN pages, reproduce CNN photographs or branding, or republish full articles.

Official enquiry routes:

- [CNN International Commercial contact form](https://commercial.cnn.com/contact-us/)
- [CNN International Commercial content sales](https://commercial.cnn.com/our-solutions/content-sales/)
- [CNN Newsource](https://www.cnnnewsource.com/)
- [LexisNexis Nexis Data+ news and media data](https://www.lexisnexis.com/en-sg/products/data/data-sets/news-media)

## 11. Test approach and result

| Test | Evidence reviewed | Result |
|---|---|---|
| Public API discovery | Current CNN help, commercial, Newsource, and public search results | No public self-service CNN article API found |
| Public RSS currency | Direct inspection of legacy feeds on 11 October 2026 and an independent September 2026 feed review | Failed - feeds are stale and unsuitable for current news |
| Public-use permission | CNN terms and available RSS evidence | Failed - no express permission found for the intended AI and derivative-output use |
| Direct licensed route | CNN International Commercial, CNN Newsource site, and Newsource support documents | Candidate - licensed access exists, but the exact use must be contracted |
| Third-party licensed route | Nexis Data+ product material and product-specific terms | Candidate - licensed APIs exist, but CNN article coverage and exact use rights remain unconfirmed |
| Generic aggregator route | NewsAPI terms and pricing FAQ | Failed as primary source - it does not clear third-party rights or provide full article content |
| No-scraping constraint | All evaluated approaches | Passed - the recommendation requires no scraping or bypass |

## 12. Acceptance-criteria traceability

| Acceptance criterion | Evidence in this document | Result |
|---|---|---|
| Investigate whether CNN provides an official API | Section 5.1 | Complete |
| Investigate CNN RSS feeds and permitted uses | Section 5.2 | Complete |
| Research CNN content licensing and reuse requirements | Sections 5.3, 7, and 8 | Complete |
| Identify authorised third-party news providers | Section 5.4 | Complete, subject to contract verification |
| Determine which article fields can legally be retrieved and processed | Section 7 | Complete - no live fields are approved until a contract defines them |
| Document limitations of each access method | Sections 5 and 6 | Complete |
| Recommend an appropriate data-access approach | Sections 3 and 9 | Complete |
| Record whether additional authorisation is required | Sections 5 and 8 | Complete - written authorisation is required |
| Review against published terms and licensing conditions | Sections 5, 11, and 14 | Complete for public evidence; contract review remains an NFA-5 dependency |

## 13. Decision and next Jira action

NFA-4's research deliverable is complete and ready for review. It does not itself grant permission to use live CNN content.

After this document is approved:

1. Move NFA-4 to Done in Jira.
2. Start NFA-5 - Obtain and record authorisation.
3. Contact CNN International Commercial or CNN Newsource using the questions in Section 8.
4. Optionally contact LexisNexis for a comparable licensed proposal.
5. Keep live ingestion disabled and continue development only with synthetic fixtures.
6. Record the final evidence and go or no-go decision without committing secrets or confidential contract terms.

## 14. Sources and evidence log

All web sources were accessed on 11 October 2026 unless noted otherwise.

### First-party CNN sources

- [CNN International Commercial - Content Sales](https://commercial.cnn.com/our-solutions/content-sales/) - States that CNN licenses news and programming and provides Newsource syndication.
- [CNN International Commercial - Contact Us](https://commercial.cnn.com/contact-us/) - Official contact route for content licensing enquiries.
- [CNN International Commercial - Terms of Use](https://commercial.cnn.com/terms-of-use/) - States that site material is protected and restricts copying, republication, transmission, and non-personal use without prior written consent. These terms apply to the commercial site and do not replace a NewsFlow AI licence.
- [CNN Help - CNN privacy and terms](https://help.cnn.com/us/Answer/Detail/000001025) - Points users to the current CNN.com Terms of Use.
- [CNN.com Terms of Use](https://www.cnn.com/terms) - Current terms link identified by CNN Help. Automated research access was blocked, so it must be reviewed manually again during NFA-5 before approval.
- [CNN Newsource](https://www.cnnnewsource.com/) - Describes a syndication platform delivering CNN and partner content to publishers and newsrooms.
- [CNN Newsource FAQ](https://newsource-cdn-static.ns.cnn.com/prd/help/content/faq.pdf) - States that content visibility is controlled by the licences in place and that media types may be separately licensed.
- [CNN Newsource historical feed FAQ](https://newsource-cdn-static.ns.cnn.com/prd/help/content/FAQ%20for%20VAN%20Nov%202018%20Upgrade.pdf) - Historical evidence of credentialed article, video, and bundle feeds and example fields. It is not proof of the current product specification.

### Provider sources

- [LexisNexis Nexis Data+ - News and Media Data](https://www.lexisnexis.com/en-sg/products/data/data-sets/news-media) - Describes a global news API, licensed news, and CNN among listed transcript sources.
- [LexisNexis Newsdesk Terms](https://www.lexisnexis.com/en-us/terms/newsdesk/terms.page) - Demonstrates that rights are product-specific and that Newsdesk use is limited to media monitoring and current awareness.
- [NewsAPI Terms](https://newsapi.org/terms) - States that third-party content rights remain relevant and protected material requires a licence or other legal permission.
- [NewsAPI Pricing FAQ](https://newsapi.org/pricing) - States that full article content is not available.

### Supporting technical observation

- [Feeder - CNN RSS feeds list](https://feeder.co/knowledge-base/rss-content/cnn-rss-feeds/) - Independent September 2026 check reporting that legacy CNN news feeds remain accessible but have not updated since 2024. This supports, but does not replace, the direct feed inspection.

## 15. Unresolved questions

These are not gaps in the NFA-4 investigation. They require commercial answers and therefore move to NFA-5:

- Will CNN accept NewsFlow AI as a Newsource or content-licensing customer?
- Is a current CNN article feed available, and which exact articles and fields does it include?
- Will CNN permit licensed content to be sent to the OpenAI API?
- Will CNN permit original LinkedIn drafts generated from the licensed source facts?
- What attribution, retention, deletion, territory, volume, and fee rules will apply?
- Can LexisNexis supply current CNN.com articles, rather than only transcripts or other CNN content, under an AI-compatible licence?
- Which route offers sufficient factual detail, reasonable cost, and acceptable operational limits for the MVP?
