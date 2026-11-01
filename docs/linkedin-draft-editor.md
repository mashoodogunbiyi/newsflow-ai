# NFA-62 - LinkedIn Draft Editor

## Purpose

NFA-62 adds a responsive, accessible editor for reviewing and modifying a generated LinkedIn draft before it is saved, copied, exported, or used.

The editor treats every generated result as an AI-assisted draft. It does not describe automated checks as factual verification, does not execute user-entered HTML, does not publish content, and does not add persistent saving before E7.

## User journey

1. An authenticated user selects an authorised article and requests a LinkedIn draft.
2. The existing generation boundary validates the FastAPI response before it reaches the editor.
3. The editor loads the generated text, source reference, configured length, grounding status, and validation warnings.
4. The user edits the draft in a native multiline textarea.
5. The NFA-63 LinkedIn-inspired content preview updates immediately without another backend or OpenAI request.
6. The user reviews the source and every warning before later save or export features are used.

## Component structure

| File | Responsibility |
|---|---|
| `apps/web/types/draft.ts` | Defines the editor document and configurable application length guidance. |
| `apps/web/hooks/use-draft-editor.ts` | Owns editable text, dirty state, incoming-draft protection, and unsaved-navigation warnings. |
| `apps/web/components/editor/linkedin-editor.tsx` | Provides the responsive editor, preview, source reference, review messages, and replacement choice. |
| `apps/web/components/editor/character-counter.tsx` | Displays the current character count and configured word guidance without claiming a LinkedIn platform limit. |
| `apps/web/components/editor/grounding-warning.tsx` | Keeps backend validation warnings visible and explains the need for human fact-checking. |
| `apps/web/components/generation/generation-controls.tsx` | Retains the last valid generated response and supplies it to the editor. |

## Editor state

The editor keeps these values locally:

- The active validated generation document.
- The original generated text.
- The current edited text.
- Whether the current text differs from the generated text.
- A newer generated document waiting for the user's decision.

Normal React rerenders do not reset the textarea. Edits do not trigger an API request and are not stored in browser storage.

## Preventing unexpected overwrites

If another generation result arrives while the editor has no changes, the new validated result becomes the active draft.

If another result arrives after the user has edited the draft, the editor keeps the local text and displays two explicit choices:

- `Replace my edits` loads the newer generated draft.
- `Keep my edits` dismisses the newer result and preserves the current text.

The application never silently replaces modified text.

## Unsaved-change behaviour

The status changes from `Generated draft loaded` to `Unsaved local edits` after the user modifies the text.

While local edits exist:

- Reloading or closing the page uses the browser's standard unsaved-change warning.
- A normal same-tab link that leaves the current editor asks the user to confirm discarding the local changes.
- Modified link clicks and links that open the source in a new tab are not blocked because they do not replace the editor page.

Persistent saving and draft history remain E7 work. NFA-62 does not present a Save button that cannot persist data.

## Text and preview safety

- The editor uses a controlled native `textarea` with an accessible label and instructions.
- Multiline text and line breaks are preserved with `white-space: pre-wrap` in the preview.
- React renders the edited value as text. HTML-like input is not inserted with `dangerouslySetInnerHTML` and cannot create executable markup.
- The preview is labelled as AI-assisted and requiring human review.
- The selected source title, source name, attribution, and validated HTTPS link remain separate from editable text.
- Validation warnings remain visible after edits because editing may introduce or fail to correct unsupported claims.
- An empty editor displays a controlled explanation and remains editable.
- A missing editor document displays a controlled unavailable state.

## Character and length guidance

The editor displays the current number of characters. It also uses the existing application configuration:

| Configured length | Application guidance |
|---|---|
| Short | Approximately 80 to 120 words |
| Medium | Approximately 130 to 200 words |
| Long | Approximately 220 to 320 words |

This is NewsFlow AI writing guidance. The interface does not claim that the character count is LinkedIn's current platform limit.

## Accessibility and responsive behaviour

- The textarea is keyboard editable and connected to visible and screen-reader instructions.
- Dirty state uses a polite status announcement.
- A waiting newer result uses an alert and native buttons.
- Empty and missing states are communicated with status or alert semantics.
- Source links have descriptive text and open safely with `noopener noreferrer`.
- The editor and preview stack on smaller screens and use a two-column layout on wide screens.
- Text wraps and long source information can break without forcing horizontal page scrolling.

## Automated verification

`apps/web/__tests__/linkedin-editor.test.tsx` covers:

- Loading generated text and source details.
- Editing, character counting, and immediate preview synchronisation.
- Empty draft handling.
- Persistent grounding warnings.
- State preservation during normal rerenders.
- Protection against a newer result overwriting local edits.
- Navigation confirmation for unsaved work.
- Literal rendering of HTML-like input.
- Native keyboard editing and configured length guidance.
- Missing generation document handling.

The existing generation-control suite confirms that a validated successful response opens the editor with the returned draft.

Run the focused checks from `apps/web`:

```bash
npm test -- --run \
  __tests__/linkedin-editor.test.tsx \
  __tests__/generation-controls.test.tsx \
  __tests__/generate-page.test.tsx
```

Run the complete frontend quality gate:

```bash
npm run lint
npm run format:check
npm run typecheck
npm test
npm run build
```

All tests use synthetic responses and local events. They do not contact CNN, OpenAI, or another external provider.

## Known limitations and next steps

- Edits are local to the mounted page and are not yet stored in PostgreSQL.
- Persistent saving, version history, copying, and exporting belong to E7 and later tasks.
- The NFA-63 preview now supports a selected private AI-generated illustration while retaining a documented no-image state. It does not attempt to reproduce every LinkedIn interface detail.
- Users must still compare the edited draft with the selected source.
- Live CNN access remains blocked by ADR-001.

## Acceptance status

- Jira issue: NFA-62
- Implementation status: Ready for review
- Approval status: Pending Mashood Ogunbiyi's review
