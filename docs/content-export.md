# NFA-71 - User-Controlled Content Export

## Purpose

NFA-71 lets a user deliberately copy the current edited LinkedIn draft and download the currently selected AI-generated illustration. NewsFlow AI does not connect to LinkedIn, publish content, schedule posts, or make an export decision for the user.

## Copy Post

`Copy Post` reads the current React editor state at the moment the user activates the button. It does not read the original generation or an earlier saved version.

The browser Clipboard API receives the exact plain-text string. Paragraph breaks, line breaks, punctuation, and hashtags are preserved. HTML-like text remains text and is not executed.

The control:

- Is disabled when the draft contains no visible characters.
- Shows an accessible progress label while copying.
- Announces success through a polite live region.
- Shows a clear alert if clipboard support is unavailable or permission is denied.
- Does not change, save, or publish the editor state.

## Download Image

The download action is enabled only when an image is selected. The browser requests:

```text
GET /api/images/{image_id}/download
```

This is a same-origin Next.js route. It validates the UUID, forwards only the `newsflow_session` cookie, and calls the existing E5 FastAPI download endpoint. FastAPI remains authoritative for authentication, owner-scoped authorisation, storage retrieval, integrity verification, media type, and availability.

The gateway permits only PNG, JPEG, and WebP responses. It returns private no-store headers, prevents MIME sniffing, and creates a controlled filename:

```text
newsflow-ai-illustration-{image_id}.{approved_extension}
```

Client-supplied filenames, backend storage keys, filesystem paths, credentials, unrestricted object URLs, and backend error details are never accepted or exposed. The browser creates a short-lived local object URL only after a complete authorised response and revokes it immediately after starting the download.

## Failure behaviour

| Situation                              | User-facing behaviour                                    |
| -------------------------------------- | -------------------------------------------------------- |
| Empty draft                            | Copy is disabled with guidance to add reviewed text.     |
| Clipboard unsupported                  | The browser-support limitation is announced.             |
| Clipboard denied                       | The user is asked to check browser clipboard permission. |
| No selected image                      | Download is disabled with image-selection guidance.      |
| Missing or differently owned image     | The same safe unavailable message is shown.              |
| Expired session                        | The user is told to sign in again.                       |
| Invalid MIME type or filename          | The response is rejected and no file is created.         |
| Storage, integrity, or network failure | A controlled retry message is shown.                     |

There are no expiring public image links. An expired authenticated session is treated as expired access and cannot download the private image.

## Rights and review

The preview continues to display the authorised source title, URL, attribution, grounding status, and human-review warning beside the export controls. The interface also states that selected illustrations are AI-generated and require human review before external use.

Only generated illustrations that passed the E5 validation and private-delivery checks can be downloaded. The task does not add CNN photography, third-party photographs, bulk exports, LinkedIn credentials, automatic publication, or scheduled posting.

## Accessibility

Both actions use native buttons and therefore support keyboard activation. Loading states disable repeat activation. Success and normal guidance use status regions, while failures use alert semantics. Button labels remain explicit rather than relying on icons.

## Verification

Automated frontend tests cover:

- Copying the latest edited text rather than the original generation.
- Exact paragraph and line-break preservation.
- Empty-content prevention.
- Clipboard success, unsupported-browser, and permission-failure states.
- Secure download gateway cookie minimisation.
- Owner-authorised image delivery through the existing E5 endpoint.
- Missing image, expired session, unsupported MIME type, and network failures.
- Safe controlled filenames and media formats.
- AI-image, source-attribution, and human-review notices.
- Absence of LinkedIn publishing requests.

Existing backend E5 tests continue to prove owner isolation, identical missing and cross-owner responses, integrity checking, safe filenames, and approved image formats.

Run the NFA-71 checks from `apps/web`:

```bash
npm test -- --run __tests__/content-export.test.tsx __tests__/image-download-proxy.test.ts
npm test
npm run lint
npm run typecheck
npm run format:check
npm run build
```
