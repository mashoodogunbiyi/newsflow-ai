# NFA-56 - Frontend Application Shell

## Purpose

NFA-56 establishes the reusable authenticated layout for the NewsFlow AI frontend. It gives the dashboard, post-creation area, content library, and account area one responsive navigation system and a consistent set of interface components.

The implementation is a foundation. It does not invent article, generation, editing, or library functionality that belongs to later Jira tasks.

## Protected route structure

Next.js route groups let these pages share a layout without adding the group name to their public URLs:

```text
app/
└── (workspace)/
    ├── layout.tsx
    ├── loading.tsx
    ├── error.tsx
    ├── dashboard/page.tsx
    ├── generate/page.tsx
    ├── library/page.tsx
    └── account/page.tsx
```

| Route | Purpose | Current state |
|---|---|---|
| `/dashboard` | Workspace overview and workflow status | Working foundation |
| `/generate` | Future authorised source selection and generation workflow | Honest disabled scaffold |
| `/library` | Future owner-scoped saved content | Empty-state scaffold |
| `/account` | Session and ownership security summary | Working foundation |

## Authentication and privacy

The existing E2 authentication flow remains the authority. NFA-56 does not create another login or session system.

Protection is applied in layers:

1. `proxy.ts` checks whether the HTTP-only session cookie is present before allowing navigation to any workspace route.
2. The `(workspace)` server layout calls the existing `getAuthenticationState()` function.
3. FastAPI validates the session through `/api/v1/auth/me` before the shell receives the user's email or renders private children.
4. Missing or invalid sessions redirect to `/login?reason=authentication_required`.
5. A backend outage shows a safe connection message without rendering workspace children.
6. FastAPI must still enforce authorisation for every future private data request. Navigation visibility never grants data access.

The session identifier remains in an HTTP-only cookie and is not passed to client components. The shell receives only the email already returned by the current-user endpoint.

## Application shell

`components/layout/app-shell.tsx` provides:

- a persistent desktop sidebar;
- a compact mobile header;
- NewsFlow AI branding;
- fixture-mode status;
- active workspace navigation;
- signed-in account context;
- logout access on desktop and mobile;
- a skip link to the main content; and
- one consistent responsive content container.

### Responsive behaviour

- Desktop at the Tailwind `lg` breakpoint uses a sticky sidebar and a separate main content column.
- Tablet and mobile use a compact sticky header and an explicit navigation menu button.
- The mobile control exposes `aria-expanded` and `aria-controls`, closes after navigation, and closes with the Escape key.
- Content cards move from one column to two or three columns only when sufficient width is available.
- The minimum supported viewport remains 320 pixels.

## Navigation

`components/layout/app-navigation.tsx` defines one route list used by desktop and mobile navigation:

- Dashboard
- Create Post
- Content Library
- Account

`usePathname()` identifies the current item. The active link receives `aria-current="page"`, a distinct background, and a visible status marker. All links and menu controls use native interactive elements and visible keyboard focus styles.

## Shared interface components

| Component | Responsibility |
|---|---|
| `PageHeader` | Page eyebrow, heading, description, and optional action area |
| `Button` and `buttonStyles` | Primary, secondary, quiet, and danger treatments for buttons and links |
| `Input` | Labelled input with help text, validation state, and accessible descriptions |
| `Card` | Default, muted, and dark content surfaces |
| `StatusBadge` | Success, warning, and neutral status labels |
| `LoadingState` | Polite accessible loading feedback with reduced-motion support |
| `ErrorState` | Safe recovery message that does not expose technical error details |

## Visual conventions

- Emerald is the primary navigation and action colour.
- Amber identifies fixture mode, attention, and numbered workflow markers.
- Stone is the application canvas, while white cards separate working areas.
- Major content cards use rounded corners, a subtle border, and restrained shadow.
- Page headings use tight tracking and balanced wrapping.
- Body text uses a maximum readable width and consistent line height.
- Page spacing increases at the `sm` and `lg` breakpoints.
- Controls use at least an 44-pixel interaction height and visible focus outlines.
- Reduced-motion preferences disable unnecessary animation and smooth scrolling.

## Loading and error handling

The shared `loading.tsx` provides an accessible pending state during protected navigation. The shared `error.tsx` is a Next.js client error boundary that displays a generic recovery message and retry action. It deliberately does not render the original exception message or sensitive technical detail.

Expected authentication failures are handled separately by the server layout so they do not become unexpected rendering errors.

## Automated evidence

The NFA-56 tests verify:

- active navigation and `aria-current`;
- the shared shell and private child area;
- mobile menu button state and Escape-key closure;
- reusable button, input, card, status, loading, and error components;
- safe error content and retry behavior;
- all four workspace routes in the optimistic protection policy;
- exact route matching that does not protect similarly named public paths;
- redirect before private children render;
- safe behavior when FastAPI is unavailable; and
- shell rendering only after the backend confirms the session.

Run from `apps/web`:

```bash
npm run lint
npm run format:check
npm run typecheck
npm test
npm run build
```

## Verification record

Verified locally on 1 November 2026:

- ESLint passed.
- Prettier formatting passed.
- TypeScript passed after generating current Next.js route types.
- All 29 frontend tests passed across 7 test files.
- The Next.js production build passed.
- The build identified `/dashboard`, `/generate`, `/library`, and `/account` as dynamic server-rendered routes.
- A temporary local server returned HTTP 307 redirects from all four protected routes to `/login?reason=authentication_required` when no session cookie was supplied.
- No test used a live account, CNN information, OpenAI request, or production credential.

Automated component tests cover responsive behavior and accessibility state. A manual browser review at mobile, tablet, and desktop widths remains part of the human review because an interactive browser surface was unavailable during this local run.

## Known limitations

- Create Post is a disabled scaffold until the authorised article and generation interface is implemented.
- Content Library is an empty state until private content-management endpoints are connected.
- Account management currently shows security status and logout; profile editing and password recovery are separate work.
- The frontend shell cannot replace FastAPI object-level authorisation.
- Live CNN access remains disabled under ADR-001.

## Review status

- Jira issue: NFA-56
- Implementation status: Ready for review
- Approval status: Pending Mashood Ogunbiyi's review

