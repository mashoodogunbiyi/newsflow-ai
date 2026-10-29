# NFA-29 - Disabled CNN Source Adapter

## Status

NFA-29 has a safe partial implementation and remains blocked for live integration.

| Decision field | Current value |
|---|---|
| Authorisation record | `NFA-SRC-AUTH-001` in NFA-5 |
| Architecture decision | `ADR-001` in NFA-8 |
| Live CNN decision | No-Go |
| Approved CNN access method | None |
| Approved live fields | None |
| Active application source | Original synthetic fixtures only |
| Live adapter status | Disabled before networking |

The project has no written CNN permission, signed provider agreement, approved endpoint, authentication mechanism, response schema, credentials, rate limits, or usage conditions. Live behaviour cannot be implemented or marked complete until those dependencies change.

## Beginner explanation

An adapter is normally a translator. It receives information in a provider's language and converts it into NewsFlow AI's standard `NewsArticle` language.

We do not currently have an authorised CNN service or its technical language. Building a translator now would require inventing an endpoint and response format. Instead, NFA-29 installs a locked adapter boundary:

```text
NewsFlow AI requests CNN information
                  |
                  v
        CnnSourceAdapter checks
        NFA-SRC-AUTH-001 and ADR-001
                  |
                  v
       SOURCE_NOT_AUTHORISED
                  |
                  v
          No HTTP request occurs
```

The boundary proves that the application fails safely while leaving the approved fixture provider available for development.

## Implemented scope

The implementation includes:

- `CnnSourceAdapter`, which structurally implements the NFA-28 `NewsProvider` protocol.
- A stable `cnn-disabled` provider identifier.
- A non-secret decision record referencing NFA-5 and NFA-8.
- No claimed pagination or incremental-retrieval capabilities.
- Immediate `SOURCE_NOT_AUTHORISED` failures for list and detail operations.
- No endpoint, HTTP client, authentication mechanism, credential field, response parser, or CNN content fixture.
- Configuration rules that reject `NEWS_SOURCE_MODE=cnn`.
- Tests proving the HTTP client is not called.
- Tests proving proposed CNN environment values cannot enable the integration.

Relevant files:

| File | Responsibility |
|---|---|
| `apps/api/app/providers/cnn_adapter.py` | Disabled protocol implementation and decision evidence. |
| `apps/api/app/providers/factory.py` | Continues to allow only the approved fixture provider. |
| `apps/api/app/core/config.py` | Accepts only `disabled` or `fixture` source modes. |
| `apps/api/tests/test_cnn_adapter.py` | Proves fail-closed behaviour before networking. |

## Deliberately deferred live behaviour

The following NFA-29 requirements cannot be implemented without an approved agreement and current provider documentation:

- CNN endpoint and HTTP method.
- Authentication and credential format.
- Provider response validation and field mapping.
- Permitted CNN article fields.
- Pagination or incremental retrieval rules.
- Rate-limit interpretation.
- Request timeout selected for the actual service.
- Retryable status codes and bounded backoff policy.
- Retention, attribution, correction, withdrawal, and deletion behaviour.
- Mocked CNN responses matching an approved contract.

Inventing these details would produce misleading tests and could encourage unauthorised access. The project therefore does not add placeholder CNN responses or guessed network logic.

## Acceptance-criteria status

| Acceptance criterion | Result |
|---|---|
| Review the approved CNN method and permissions | Complete - NFA-5 confirms that no method is approved. |
| Confirm the E0 decision | Complete - ADR-001 records No-Go for live integration. |
| Implement the provider interface boundary | Complete as a disabled skeleton. |
| Configure endpoint and authentication | Blocked - no approved contract or documentation. |
| Retrieve and map permitted CNN fields | Blocked - no live fields are approved. |
| Implement provider pagination and incremental retrieval | Blocked - provider capabilities are unknown. |
| Implement rate limits, timeout, retries, and backoff | Blocked - service rules are unknown. |
| Handle invalid live responses | Blocked - no approved response contract exists. |
| Prevent credentials from appearing in logs | Complete for the skeleton - no credentials are accepted or stored. |
| Disable integration when authorisation is absent | Complete and automated. |
| Add mocked provider tests | Complete for the disabled boundary; live response mocks remain blocked. |
| Document configuration and limitations | Complete in this document. |

NFA-29 must remain Blocked rather than Done because its live outcome and most live acceptance criteria depend on external authorisation.

## Test evidence

Run the focused tests from `apps/api` with the virtual environment active:

```bash
pytest tests/test_cnn_adapter.py
```

The tests verify:

- The skeleton satisfies the provider interface.
- The active authorisation and architecture decisions are recorded.
- Article discovery fails before `httpx` can make a request.
- Article detail retrieval fails before `httpx` can make a request.
- A `cnn` source mode is rejected.
- Proposed CNN configuration variables do not enable access.

The tests use no CNN content, credentials, endpoint, network request, or copied provider response.

## Requirements for future activation

Before live work resumes:

1. Obtain written permission or a signed agreement from CNN or an authorised provider.
2. Store confidential evidence outside the repository and add its non-secret reference to NFA-5.
3. Revise and approve NFA-5 with the exact permitted use.
4. Revise NFA-6 with the approved provider fields and rules.
5. Reassess NFA-7 against the real data flow.
6. Replace ADR-001 with an approved Go decision.
7. Obtain current technical documentation and controlled credentials.
8. Implement and test the actual endpoint, mapping, rate limits, timeouts, retries, rights controls, and licence-expiry shutdown.

Until all gates are satisfied, `NEWS_SOURCE_MODE=fixture` is the only permitted active source.
