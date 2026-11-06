"""Verify the NFA-89 technical report and portfolio case study."""

from __future__ import annotations

import json
import re
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs" / "technical-report.md"
CASE_STUDY = ROOT / "docs" / "portfolio-case-study.md"
README = ROOT / "README.md"
TESTING = ROOT / "docs" / "testing.md"
EVALUATION = ROOT / "apps" / "api" / "evaluations" / "reports" / "nfa-78-baseline.json"
SCREENSHOTS = (
    ROOT / "docs" / "screenshots" / "homepage.png",
    ROOT / "docs" / "screenshots" / "article-dashboard.png",
    ROOT / "docs" / "screenshots" / "generation-workspace.png",
    ROOT / "docs" / "screenshots" / "content-library.png",
)


class TechnicalReportVerificationError(RuntimeError):
    """Raised when a report claim no longer matches repository evidence."""


def read_text(path: Path) -> str:
    if not path.is_file():
        raise TechnicalReportVerificationError(f"Missing required file: {path}")
    return path.read_text(encoding="utf-8")


def require_fragments(label: str, text: str, fragments: tuple[str, ...]) -> None:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        formatted = ", ".join(repr(item) for item in missing)
        raise TechnicalReportVerificationError(f"{label} is missing: {formatted}")


def verify_report_structure() -> None:
    report = read_text(REPORT)
    require_fragments(
        "Technical report sections",
        report,
        (
            "# NewsFlow AI Technical Report",
            "## 1. Executive summary",
            "## 2. Project background",
            "## 3. Problem statement",
            "## 4. Project objectives",
            "## 5. Requirements analysis",
            "## 6. System architecture",
            "## 7. Technology stack",
            "## 8. Database design",
            "## 9. Article ingestion, normalisation, and provenance",
            "## 10. AI text generation",
            "## 11. AI image generation",
            "## 12. Frontend implementation",
            "## 13. Authentication, authorisation, and security",
            "## 14. Content persistence and lifecycle",
            "## 15. Testing and evaluation",
            "## 16. Key engineering decisions",
            "## 17. Challenges and solutions",
            "## 18. Measurable outcomes",
            "## 19. Known limitations",
            "## 20. Future improvements",
            "## 21. Conclusion",
            "## 22. Technical claim references",
        ),
    )
    require_fragments(
        "Technical report accuracy statements",
        report,
        (
            "Live CNN integration | No-Go - not authorised",
            "provider-neutral boundary",
            "Argon2id",
            "CSRF",
            "Fifteen version-controlled Alembic revisions",
            "489 tests",
            "173 tests across 36 files",
            "13 Playwright Chromium scenarios",
            "10 grounding cases, 7 image-safety cases, and 12 claims",
            "not evidence of production performance",
            "The application never publishes it automatically.",
            "A forgotten-password workflow is planned but not implemented.",
        ),
    )


def verify_case_study_structure() -> None:
    case_study = read_text(CASE_STUDY)
    require_fragments(
        "Portfolio case-study sections",
        case_study,
        (
            "# NewsFlow AI Portfolio Case Study",
            "## Project overview",
            "## Problem",
            "## Solution",
            "## Technology stack",
            "## Architecture",
            "## Key features",
            "## Data engineering work",
            "## Software engineering work",
            "## AI integration and safety",
            "## Engineering challenges",
            "## Testing, security, and measurable results",
            "## Results",
            "## Lessons learned",
            "## Known limitations and next steps",
            "## GitHub repository and demonstration",
            "## CV-ready summary",
        ),
    )
    require_fragments(
        "Portfolio skills and limits",
        case_study,
        (
            "Python, FastAPI, Next.js, TypeScript, PostgreSQL, OpenAI service interfaces and Docker",
            "validation, normalisation, deduplication, provenance, rights metadata",
            "GitHub Actions, Git and Jira",
            "489 backend tests passed",
            "live CNN and public production release remain No-Go",
            "Nothing is published automatically.",
        ),
    )


def local_link_targets(path: Path) -> list[str]:
    return re.findall(r"!?(?:\[[^\]]*\])\(([^)]+)\)", read_text(path))


def verify_links() -> None:
    for document in (REPORT, CASE_STUDY):
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
                raise TechnicalReportVerificationError(
                    f"{document.relative_to(ROOT)} has a missing local link: {target}"
                )

    repository_url = "https://github.com/mashoodogunbiyi/newsflow-ai"
    for document in (REPORT, CASE_STUDY):
        if repository_url not in read_text(document):
            raise TechnicalReportVerificationError(
                f"{document.relative_to(ROOT)} does not link the GitHub repository."
            )


def png_dimensions(path: Path) -> tuple[int, int]:
    if not path.is_file():
        raise TechnicalReportVerificationError(f"Missing screenshot: {path}")
    with path.open("rb") as image:
        header = image.read(24)
    if len(header) != 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
        raise TechnicalReportVerificationError(f"Invalid PNG screenshot: {path}")
    return struct.unpack(">II", header[16:24])


def verify_screenshots() -> None:
    combined = read_text(REPORT) + read_text(CASE_STUDY)
    for screenshot in SCREENSHOTS:
        relative = screenshot.relative_to(ROOT / "docs").as_posix()
        if relative not in combined:
            raise TechnicalReportVerificationError(
                f"The report package does not reference {relative}."
            )
        width, height = png_dimensions(screenshot)
        if width < 1200 or height < 700:
            raise TechnicalReportVerificationError(
                f"{screenshot.name} is too small for portfolio use: {width}x{height}"
            )


def verify_repository_contracts() -> None:
    package = json.loads(read_text(ROOT / "apps" / "web" / "package.json"))
    dependencies = package.get("dependencies", {})
    if not dependencies.get("next", "").startswith("16"):
        raise TechnicalReportVerificationError("The report expects Next.js 16.")
    if not dependencies.get("react", "").startswith("19"):
        raise TechnicalReportVerificationError("The report expects React 19.")

    migration_count = len(
        tuple((ROOT / "apps" / "api" / "migrations" / "versions").glob("*.py"))
    )
    if migration_count != 15:
        raise TechnicalReportVerificationError(
            f"The report records 15 Alembic revisions, but found {migration_count}."
        )

    require_fragments(
        "Provider factory",
        read_text(ROOT / "apps" / "api" / "app" / "providers" / "factory.py"),
        (
            'settings.news_source_mode == "fixture"',
            "FixtureNewsProvider()",
            "raise SourceNotAuthorisedError",
        ),
    )
    require_fragments(
        "Authentication and hashing",
        read_text(ROOT / "apps" / "api" / "app" / "security" / "passwords.py"),
        ("Argon2", "class Argon2PasswordHasher", "def hash", "def verify"),
    )
    require_fragments(
        "Generation preferences",
        read_text(ROOT / "apps" / "web" / "types" / "generation.ts"),
        (
            'label: "Professional"',
            'label: "Conversational"',
            'label: "Analytical"',
            'label: "English"',
            'label: "French"',
            'label: "Spanish"',
        ),
    )


def verify_evaluation_claims() -> None:
    report = json.loads(read_text(EVALUATION))
    if report.get("status") != "automated_pass_human_review_pending":
        raise TechnicalReportVerificationError("The NFA-78 baseline is not passing.")
    case_counts = report.get("case_counts", {})
    if case_counts.get("grounding") != 10:
        raise TechnicalReportVerificationError("Expected 10 NFA-78 grounding cases.")
    if case_counts.get("image_safety") != 7:
        raise TechnicalReportVerificationError("Expected 7 NFA-78 image cases.")
    if case_counts.get("evaluated_claims") != 12:
        raise TechnicalReportVerificationError("Expected 12 NFA-78 evaluated claims.")
    percentages = [
        value
        for name, value in report.get("metrics", {}).items()
        if name.endswith("_percentage")
    ]
    if not percentages or any(value != 100.0 for value in percentages):
        raise TechnicalReportVerificationError(
            "A recorded NFA-78 percentage no longer matches the report."
        )


def verify_test_evidence() -> None:
    testing = read_text(TESTING)
    require_fragments(
        "NFA-89 verification record",
        testing,
        (
            "## NFA-89 technical report and portfolio case-study verification",
            "489 tests, skipped 16 safety-gated tests, and deselected the optional live-model test",
            "173 tests across 36 files",
            "13 Chromium scenarios",
        ),
    )


def verify_readme_and_ci() -> None:
    readme = read_text(README)
    require_fragments(
        "README report links",
        readme,
        (
            "## Technical report and portfolio case study",
            "docs/technical-report.md",
            "docs/portfolio-case-study.md",
            "python3 scripts/verify_technical_report.py",
        ),
    )
    workflow = read_text(ROOT / ".github" / "workflows" / "quality.yml")
    if "python3 scripts/verify_technical_report.py" not in workflow:
        raise TechnicalReportVerificationError(
            "GitHub Actions does not verify the NFA-89 report contract."
        )


def verify_no_exaggeration() -> None:
    combined = (read_text(REPORT) + read_text(CASE_STUDY)).lower()
    forbidden = (
        "live cnn integration is implemented",
        "production deployment is complete",
        "automatically publishes to linkedin",
        "guarantees factual accuracy",
        "fully wcag compliant",
    )
    present = [phrase for phrase in forbidden if phrase in combined]
    if present:
        raise TechnicalReportVerificationError(
            "The report contains an unsupported claim: " + ", ".join(present)
        )


def verify_ascii_hyphens() -> None:
    disallowed = {"\u2010", "\u2011", "\u2012", "\u2013", "\u2014", "\u2212"}
    for path in (REPORT, CASE_STUDY):
        found = sorted(set(read_text(path)) & disallowed)
        if found:
            codepoints = ", ".join(f"U+{ord(value):04X}" for value in found)
            raise TechnicalReportVerificationError(
                f"{path.relative_to(ROOT)} contains non-ASCII dash characters: {codepoints}"
            )


def main() -> None:
    verify_report_structure()
    verify_case_study_structure()
    verify_links()
    verify_screenshots()
    verify_repository_contracts()
    verify_evaluation_claims()
    verify_test_evidence()
    verify_readme_and_ci()
    verify_no_exaggeration()
    verify_ascii_hyphens()
    print("NFA-89 technical report and portfolio case-study verification passed.")


if __name__ == "__main__":
    try:
        main()
    except TechnicalReportVerificationError as exc:
        raise SystemExit(f"NFA-89 verification failed: {exc}") from exc
