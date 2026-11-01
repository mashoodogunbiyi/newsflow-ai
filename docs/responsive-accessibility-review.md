# NFA-65 Responsive Design and Accessibility Review

## Outcome

NFA-65 reviews the NewsFlow AI frontend against representative responsive layouts and applicable WCAG 2.2 Level AA requirements. It covers the public pages, authentication forms, authenticated shell, article discovery, source review, generation controls and states, draft editor, LinkedIn-inspired preview, and image controls.

The implementation and automated review are complete. No known release-blocking defect remains in the reviewed code. A final human browser pass at the three supported widths and a representative VoiceOver pass remain required before the Jira issue is moved to Done because native browser automation was unavailable during this workspace session.

## Supported viewports

The NFA-65 acceptance matrix uses these representative viewport widths:

| Profile |   Width | Expected layout                                                                                  |
| ------- | ------: | ------------------------------------------------------------------------------------------------ |
| Mobile  |  375 px | Single-column content, mobile navigation, stacked controls, editor followed by preview           |
| Tablet  |  768 px | Expanded spacing, two-column article cards and form groups where space permits                   |
| Desktop | 1440 px | Persistent workspace navigation, three-column article catalogue, side-by-side editor and preview |

These widths are regression checkpoints rather than the only supported device sizes. Layouts use fluid widths, wrapping, and responsive breakpoints between them. The existing application-shell contract also remains usable down to 320 px, but 375 px is the formal mobile checkpoint for this issue.

## Review scope

| Surface                        | Responsive review                                   | Accessibility review                                              |
| ------------------------------ | --------------------------------------------------- | ----------------------------------------------------------------- |
| Public homepage                | Fluid hero and preview, stacked mobile actions      | Skip link, heading order, link focus, readable text               |
| Register and login             | Single-column form and responsive supporting panel  | Labels, instructions, field errors, error focus, keyboard focus   |
| Application shell              | Mobile menu and desktop sidebar                     | Skip link, active route, Escape handling, focus return            |
| Article dashboard              | Responsive filters, cards, and pagination           | Native controls, headings, link purpose, attribution              |
| Article source panel           | Wrapping metadata, URLs, identifiers, and actions   | Description lists, headings, source link, status text             |
| Generation controls and states | Stacked mobile controls and wrapping status content | Fieldsets, labels, disabled state, status and alert announcements |
| Draft editor                   | Full-width textarea and desktop split layout        | Native editable control, instructions, character output, warnings |
| LinkedIn-inspired preview      | Fluid card, wrapping draft and source content       | Meaningful regions, image alternative text, AI designation        |
| Image controls                 | Stacked mobile preferences and full-width action    | Labelled choices, keyboard-native controls, request status        |

## Accessibility target

WCAG 2.2 Level AA is the target where its success criteria apply to this frontend. Automated checks support the review, but they do not establish complete conformance. Human keyboard, visual, and screen-reader checks remain necessary.

The following implementation rules now apply across the reviewed interface:

- Interactive elements receive a consistent visible `:focus-visible` outline.
- Skip links move keyboard users to the main page or workspace content.
- Mobile navigation moves focus into the opened menu and returns focus to its toggle when Escape closes it.
- Client validation associates an error with its field and focuses the first invalid field.
- Form-level authentication failures receive programmatic focus.
- Important request progress and success use polite status announcements.
- Failures use alert semantics where immediate attention is required.
- Statuses use text as well as colour.
- Generated illustrations have descriptive alternative text and a visible AI-generated designation.
- Long identifiers, URLs, draft text, and preview text can wrap without forcing page-level horizontal scrolling.
- Secondary text uses reviewed contrast tokens rather than low-opacity text.
- Reduced-motion preferences suppress smooth scrolling and non-essential animation.

## Defect record

The review found and resolved the following defects. These are recorded here as the NFA-65 defect evidence. A separate Jira Bug is not required for a defect found and fixed inside this issue before acceptance unless the team wants separate reporting metrics.

| ID            | Severity | Defect                                                                                                        | Resolution                                                                                                | Status   |
| ------------- | -------- | ------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- | -------- |
| NFA65-A11Y-01 | Major    | Some homepage and brand links did not have a consistent visible keyboard focus indicator.                     | Added a global focus-visible rule and explicit high-contrast link focus styles.                           | Resolved |
| NFA65-A11Y-02 | Major    | Closing the mobile navigation with Escape did not return focus to the menu toggle.                            | Added managed focus on open and Escape focus restoration.                                                 | Resolved |
| NFA65-A11Y-03 | Major    | Client-side authentication validation did not move focus to the first invalid field or a returned form error. | Added field refs, error associations, and deliberate focus management.                                    | Resolved |
| NFA65-A11Y-04 | Major    | Several secondary labels and supporting messages used opacity values that were difficult to read.             | Raised reviewed text tokens and added deterministic WCAG contrast checks.                                 | Resolved |
| NFA65-A11Y-05 | Major    | Reduced-motion preferences stopped smooth scrolling but did not consistently stop repeated animations.        | Added reduced animation duration and iteration rules.                                                     | Resolved |
| NFA65-SEM-01  | Moderate | The authentication marketing heading could appear before the page's main heading in the document outline.     | Changed the supporting marketing heading to descriptive text so the page title remains the first heading. | Resolved |
| NFA65-READ-01 | Moderate | Demonstration labels included text smaller than the reviewed minimum supporting-text size.                    | Replaced custom micro-text sizes with the standard `text-xs` token.                                       | Resolved |
| NFA65-RESP-01 | Major    | Nested grid content and long identifiers could create avoidable overflow pressure at narrow widths.           | Added `min-width: 0`, safe wrapping, and long-identifier breaks at the affected boundaries.               | Resolved |

No unresolved defect identified by the code and automated review is currently classified as release blocking.

## Automated evidence

### Accessibility audit

`apps/web/__tests__/accessibility-audit.test.tsx` runs axe-core against representative rendered interfaces:

- Homepage.
- Authentication shell and credentials form.
- Authenticated workspace shell and navigation.
- Article discovery filters and article card.
- Source panel, draft editor, image controls, and preview.

The axe colour-contrast rule is disabled only in jsdom because jsdom does not calculate layout, canvas, or final painted colours. Contrast is not ignored: `apps/web/__tests__/contrast-and-motion.test.ts` independently calculates the WCAG contrast ratio for the normal text tokens used on light and dark surfaces.

### Responsive regression

`apps/web/__tests__/responsive-review.test.tsx` checks the layout contracts that support the 375 px, 768 px, and 1440 px matrix:

- Mobile and desktop navigation visibility rules.
- Fluid workspace content widths and responsive gutters.
- Tablet and desktop dashboard grid changes.
- Responsive dashboard-filter layout.
- Long article identifiers, draft text, and preview text wrapping.
- Stacked mobile image action and side-by-side desktop editor and preview.

Existing component tests continue to cover article cards, filtering, source selection, generation states, draft editing, preview states, image controls, and mobile navigation.

### Focus, semantics, and announcements

- `workspace-components.test.tsx` verifies mobile-menu focus entry and Escape focus return.
- `auth-interface.test.tsx` verifies invalid fields expose `aria-invalid`, link to their error, and receive focus.
- Generation, editor, preview, and image tests verify labelled controls, statuses, alerts, alternative text, and safe fallbacks.
- The full component suite queries the interface through accessible roles and names, which detects missing semantic labels used by the tests.

### Local results

Verified on 1 November 2026:

| Check                       | Result                                                               |
| --------------------------- | -------------------------------------------------------------------- |
| Focused NFA-65 tests        | 26 passed across 5 files                                             |
| Complete frontend tests     | 129 passed across 26 files                                           |
| ESLint                      | Passed with no warnings or errors                                    |
| Prettier                    | Passed                                                               |
| TypeScript                  | Passed                                                               |
| Next.js production build    | Passed                                                               |
| Production HTTP smoke test  | `/`, `/login`, and `/register` returned 200                          |
| Protected route smoke test  | `/dashboard` returned 307 to the authentication-required login route |
| Live CNN or OpenAI requests | None                                                                 |

## Contrast evidence

The deterministic checks use the sRGB relative-luminance formula required for WCAG contrast evaluation.

| Use                         | Foreground and background                 |                 Ratio | AA normal text |
| --------------------------- | ----------------------------------------- | --------------------: | -------------- |
| Primary text                | `#0e2b22` on `#f7f6f2`                    |    Greater than 4.5:1 | Pass           |
| Muted light-surface text    | 70 percent `#0e2b22` blended on `#f7f6f2` |  Approximately 5.51:1 | Pass           |
| Secondary dark-surface text | 75 percent white blended on `#022c22`     |  Approximately 9.04:1 | Pass           |
| Emerald link text           | `#047857` on `#f7f6f2`                    |  Approximately 5.07:1 | Pass           |
| Error text                  | `#991b1b` on `#fef2f2`                    |  Approximately 7.60:1 | Pass           |
| Warning text                | `#451a03` on `#fffbeb`                    | Approximately 14.44:1 | Pass           |

This table covers the reviewed shared text tokens. A final browser inspection should still confirm the rendered states, focus outlines, disabled controls, and any browser-specific anti-aliasing differences.

## Manual acceptance checklist

Complete this short pass before moving NFA-65 to Done.

### Responsive browser review

For each width, open the homepage, register, login, dashboard, and one selected article's Create Post page.

1. Open browser developer tools and set the viewport to 375 px.
2. Confirm there is no page-level horizontal scrollbar.
3. Open and close the mobile menu and confirm its content remains visible.
4. Review dashboard filters, article cards, source panel, generation controls, editor, preview, and image controls.
5. Repeat at 768 px.
6. Repeat at 1440 px and confirm the sidebar and editor-preview split are readable.
7. Test one long draft and confirm its text wraps inside the preview.

Record each result as Pass or create a Jira Bug with the viewport, route, steps, expected result, actual result, screenshot, severity, and NFA-65 link.

### Keyboard-only review

1. Reload the page and use Tab and Shift+Tab without a mouse.
2. Confirm the skip link appears and moves focus to main content.
3. Confirm every required link, button, radio control, select, input, and textarea is reachable.
4. Open the mobile menu and press Escape. Confirm focus returns to Open navigation.
5. Submit an invalid registration form. Confirm focus moves to the first invalid field.
6. Confirm focus is always visible and no keyboard trap occurs.
7. Confirm Space or Enter activates buttons and links as expected.

### Representative VoiceOver review on macOS

1. Turn on VoiceOver with Command+F5.
2. Navigate the login page and confirm the page title, main heading, field labels, help text, and errors are understandable.
3. Navigate the dashboard by headings, landmarks, links, and form controls.
4. On Create Post, confirm the source headings, tone and length labels, generation statuses, editor label, warning messages, preview region, illustration description, and AI designation are announced.
5. Trigger one controlled validation error and one generation error. Confirm both are announced without relying on colour.
6. Turn VoiceOver off with Command+F5 and record the result below.

## Manual review record

| Review                           | Reviewer | Date    | Result  | Evidence or defect link |
| -------------------------------- | -------- | ------- | ------- | ----------------------- |
| 375 px browser review            | Pending  | Pending | Pending | Pending                 |
| 768 px browser review            | Pending  | Pending | Pending | Pending                 |
| 1440 px browser review           | Pending  | Pending | Pending | Pending                 |
| Keyboard-only journey            | Pending  | Pending | Pending | Pending                 |
| VoiceOver representative journey | Pending  | Pending | Pending | Pending                 |

## Known limitations

- The workspace browser-control connection was unavailable during implementation, so this record does not claim that a live viewport inspection was performed.
- A screen reader is a human interaction tool. Automated role and axe checks do not replace the pending VoiceOver journey.
- jsdom cannot calculate the final painted colour contrast, element geometry, clipping, or horizontal scrolling. Deterministic token tests and responsive class checks reduce regression risk but do not replace the browser pass.
- Authenticated generation and image journeys require FastAPI, PostgreSQL, a fixture user, and permitted fixture content. The component suite exercises those interface states with synthetic data without making paid or external requests.
- Accessibility is an ongoing product requirement. New frontend work must preserve the automated checks and repeat the relevant manual review.

## Review decision

- Implementation status: Ready for review.
- Automated quality status: Passed.
- Release-blocking defects found by this review: None unresolved.
- Manual acceptance status: Pending Mashood Ogunbiyi's responsive, keyboard, and VoiceOver review.
- Jira status recommendation: Keep NFA-65 in Review until the manual review record is completed, then move it to Done if no release-blocking defect is found.
