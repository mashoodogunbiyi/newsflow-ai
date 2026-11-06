"""Verify the NFA-88 demonstration package against executable repository contracts."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEMO_ROOT = ROOT / "docs" / "demonstration"
DOCUMENTS = (
    DEMO_ROOT / "README.md",
    DEMO_ROOT / "demo-script.md",
    DEMO_ROOT / "rehearsal-checklist.md",
    DEMO_ROOT / "fallback-plan.md",
    DEMO_ROOT / "evidence.md",
)
EXPECTED_DEMO_URL = "https://example.invalid/newsflow/synthetic-clean-energy"


class DemonstrationVerificationError(RuntimeError):
    """Raised when the demonstration package no longer matches the application."""


def read_text(path: Path) -> str:
    if not path.is_file():
        raise DemonstrationVerificationError(f"Missing required file: {path}")
    return path.read_text(encoding="utf-8")


def require_fragments(label: str, text: str, fragments: tuple[str, ...]) -> None:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        formatted = ", ".join(repr(item) for item in missing)
        raise DemonstrationVerificationError(f"{label} is missing: {formatted}")


def verify_documents() -> None:
    overview = read_text(DOCUMENTS[0])
    require_fragments(
        "Demonstration overview",
        overview,
        (
            "## 2. Audience",
            "## 3. Objectives",
            "npm run demo",
            "owner@example.com",
            "TestPassword123!",
            EXPECTED_DEMO_URL,
            "CNN or OpenAI request",
            "Live CNN integration is not authorised",
            "does not publish directly to LinkedIn",
        ),
    )

    require_fragments(
        "Presenter script",
        read_text(DOCUMENTS[1]),
        (
            "## 4. Part 2 - Authentication and protected workspace",
            "## 5. Part 3 - Article discovery and rights boundary",
            "## 6. Part 4 - Configure and generate a LinkedIn draft",
            "## 8. Part 6 - Image generation and safety",
            "## 9. Part 7 - Save, reopen, copy, and download",
            "## 10. Part 8 - Architecture explanation",
            "mocked, not a live OpenAI result",
        ),
    )

    require_fragments(
        "Rehearsal checklist",
        read_text(DOCUMENTS[2]),
        (
            "## 2. Preflight",
            "## 3. Main journey",
            "## 4. Technical explanation",
            "## 5. Safety and accuracy",
            "## 6. Fallback readiness",
            "## 7. Closeout",
            "manual rehearsal",
        ),
    )

    require_fragments(
        "Fallback plan",
        read_text(DOCUMENTS[3]),
        (
            "## 2. Preferred fallback order",
            "## 3. Failure playbook",
            "## 4. Prepared offline evidence",
            "## 6. Abort conditions",
            "mocked output",
            "docker compose down",
        ),
    )

    require_fragments(
        "Evidence record",
        read_text(DOCUMENTS[4]),
        (
            "## 2. Automated workflow coverage",
            "## 3. Verification record",
            "## 4. Screenshot record",
            "## 5. Defect record",
            "## 6. Known limitations",
            "Human narrated rehearsal",
        ),
    )


def local_link_targets(path: Path) -> list[str]:
    return re.findall(r"!?(?:\[[^\]]*\])\(([^)]+)\)", read_text(path))


def verify_links() -> None:
    for document in DOCUMENTS:
        for raw_target in local_link_targets(document):
            target = raw_target.strip().strip("<>")
            local_target = target.split("#", maxsplit=1)[0]
            if (
                not local_target
                or "://" in local_target
                or local_target.startswith("mailto:")
            ):
                continue
            resolved = (document.parent / local_target).resolve()
            if not resolved.is_relative_to(ROOT) or not resolved.exists():
                raise DemonstrationVerificationError(
                    f"{document.relative_to(ROOT)} has a missing local link: {target}"
                )


def verify_launcher() -> None:
    package = json.loads(read_text(ROOT / "apps" / "web" / "package.json"))
    if package.get("scripts", {}).get("demo") != "node scripts/start-demonstration.mjs":
        raise DemonstrationVerificationError(
            "Frontend package must expose the documented npm run demo command."
        )

    launcher = read_text(ROOT / "apps" / "web" / "scripts" / "start-demonstration.mjs")
    require_fragments(
        "Demonstration launcher",
        launcher,
        (
            'const applicationUrl = "http://127.0.0.1:3100"',
            'const mockApiUrl = "http://127.0.0.1:4100"',
            '"e2e/support/mock-api.mjs"',
            'await fetch(`${mockApiUrl}/__test/reset`',
            "owner@example.com",
            "TestPassword123!",
            EXPECTED_DEMO_URL,
            "Press Ctrl+C",
        ),
    )


def verify_fixture_and_journey() -> None:
    fixture = read_text(ROOT / "apps" / "web" / "e2e" / "support" / "mock-api.mjs")
    require_fragments(
        "Synthetic mock API",
        fixture,
        (
            'server.listen(PORT, "127.0.0.1"',
            '"owner@example.com"',
            'body.password !== "TestPassword123!"',
            EXPECTED_DEMO_URL,
            '"mock-openai-text-model"',
        ),
    )

    component = read_text(
        ROOT / "apps" / "web" / "components" / "articles" / "article-url-resolver.tsx"
    )
    if f'const DEMO_ARTICLE_URL = "{EXPECTED_DEMO_URL}"' not in component:
        raise DemonstrationVerificationError(
            "The dashboard demonstration URL does not match the package fixture."
        )

    seed = read_text(ROOT / "apps" / "api" / "app" / "database" / "seed.py")
    if f'SEED_ARTICLE_URL = "{EXPECTED_DEMO_URL}"' not in seed:
        raise DemonstrationVerificationError(
            "The Docker demonstration seed URL does not match the package fixture."
        )

    journey = read_text(ROOT / "apps" / "web" / "e2e" / "content-workflow.spec.ts")
    require_fragments(
        "Browser demonstration journey",
        journey,
        (
            EXPECTED_DEMO_URL,
            'name: "Generate LinkedIn draft"',
            'name: "Generate image"',
            'name: "Regenerate image"',
            'name: "Save to library"',
            'name: "Copy Post"',
            'name: "Download Image"',
            'name: "Delete draft"',
        ),
    )


def verify_readme_and_ci() -> None:
    readme = read_text(ROOT / "README.md")
    require_fragments(
        "Main README demonstration section",
        readme,
        (
            "## Demonstration",
            "docs/demonstration/README.md",
            "npm run demo",
        ),
    )

    workflow = read_text(ROOT / ".github" / "workflows" / "quality.yml")
    if "python3 scripts/verify_demonstration_package.py" not in workflow:
        raise DemonstrationVerificationError(
            "CI must verify the demonstration documentation contract."
        )


def verify_ascii_hyphens() -> None:
    disallowed = {"\u2010", "\u2011", "\u2012", "\u2013", "\u2014", "\u2212"}
    paths = (
        *DOCUMENTS,
        ROOT / "apps" / "web" / "scripts" / "start-demonstration.mjs",
    )
    for path in paths:
        found = sorted(set(read_text(path)) & disallowed)
        if found:
            codepoints = ", ".join(f"U+{ord(value):04X}" for value in found)
            raise DemonstrationVerificationError(
                f"{path.relative_to(ROOT)} contains non-ASCII dash characters: {codepoints}"
            )


def main() -> None:
    verify_documents()
    verify_links()
    verify_launcher()
    verify_fixture_and_journey()
    verify_readme_and_ci()
    verify_ascii_hyphens()
    print("NFA-88 demonstration package verification passed.")


if __name__ == "__main__":
    try:
        main()
    except DemonstrationVerificationError as exc:
        raise SystemExit(f"NFA-88 verification failed: {exc}") from exc

