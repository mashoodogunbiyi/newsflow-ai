# NewsFlow AI screenshots

These screenshots show the implemented NewsFlow AI interface at a 1440 by 960 desktop viewport.

They use the deterministic local Playwright API fixture and contain only synthetic accounts, articles, drafts, and images. They do not contain live CNN content, real user information, provider credentials, private application secrets, or paid OpenAI output.

| File | Interface state |
| --- | --- |
| `homepage.png` | Public project introduction and review-first workflow |
| `article-dashboard.png` | Authenticated catalogue with one permitted synthetic article |
| `generation-workspace.png` | Human-editable generated draft and private illustration workflow |
| `content-library.png` | Authenticated personal library containing the saved synthetic draft |

## Recreate the screenshots

Install the frontend dependencies and Playwright Chromium first:

```bash
cd apps/web
npm ci
npx playwright install chromium
npm run screenshots:docs
```

The command starts the existing synthetic API fixture and a local Next.js development server on ports 4100 and 3100, captures the four states, then stops both processes. Those ports must be available.

The script deliberately uses:

- `owner@example.com`, which is a synthetic test identity;
- a clearly labelled synthetic technology article;
- a mocked LinkedIn draft;
- mocked generated-image bytes;
- no live provider key or network request.

Review every updated image before committing it. If interface text or layout changes intentionally, regenerate the screenshots and update the main README in the same pull request.
