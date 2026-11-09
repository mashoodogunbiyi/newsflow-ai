"""Verify the NFA-91 project closure package against repository evidence."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLOSURE = ROOT / "docs" / "project-closure"
DOCUMENTS = (
    CLOSURE / "README.md",
    CLOSURE / "project-closure-report.md",
    CLOSURE / "epic-review.md",
    CLOSURE / "deliverable-inventory.md",
    CLOSURE / "outstanding-work-register.md",
    CLOSURE / "retrospective.md",
)


class ProjectClosureVerificationError(RuntimeError):
    """Raised when closure evidence is incomplete or contradicts the repository."""


def read_text(path: Path) -> str:
    if not path.is_file():
        raise ProjectClosureVerificationError(f"Missing required file: {path}")
    return path.read_text(encoding="utf-8")


def require_fragments(label: str, text: str, fragments: tuple[str, ...]) -> None:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        formatted = ", ".join(repr(item) for item in missing)
        raise ProjectClosureVerificationError(f"{label} is missing: {formatted}")


def verify_closure_structure() -> None:
    overview = read_text(DOCUMENTS[0])
    require_fragments(
        "Closure overview",
        overview,
        (
            "Project completed with documented limitations",
            "14c97464be98d7d6a4275158b7215401122974c7",
            "## 3. Package contents",
            "## 4. Closure boundary",
            "## 5. Jira closure rule",
            "Public production release | No-Go",
            "Live CNN integration | No-Go",
        ),
    )

    report = read_text(DOCUMENTS[1])
    require_fragments(
        "Closure report",
        report,
        (
            "## 2. Original objectives",
            "## 4. Final scope",
            "## 5. Epic review summary",
            "## 6. Delivered functionality",
            "## 8. Testing and quality results",
            "## 9. Release-readiness and demonstration review",
            "## 10. Security, privacy and source-rights status",
            "## 11. Known limitations and remaining risks",
            "## 12. Project achievements",
            "## 13. Engineering challenges",
            "## 14. Lessons learned",
            "## 15. Future improvements",
            "## 16. Final project decision",
            "Project completed with documented limitations",
            "489 deterministic backend tests passed",
            "173 frontend tests passed across 36 files",
            "13 Playwright Chromium scenarios passed",
            "82 merged pull requests before closure",
        ),
    )

    epic_review = read_text(DOCUMENTS[2])
    headings = re.findall(r"^### (E[0-9]) - ", epic_review, flags=re.MULTILINE)
    expected = [f"E{number}" for number in range(10)]
    if headings != expected:
        raise ProjectClosureVerificationError(
            f"Epic review must contain E0 through E9 once and in order; found {headings}."
        )
    require_fragments(
        "Epic review boundaries",
        epic_review,
        (
            "live CNN No-Go",
            "fixture-only scope",
            "password reset",
            "human UAT",
            "production storage",
            "NFA-91 review, merge and evidence comment",
        ),
    )

    inventory = read_text(DOCUMENTS[3])
    require_fragments(
        "Deliverable inventory",
        inventory,
        (
            "82 merged pull requests",
            "Live CNN adapter | Not delivered by design",
            "Human UAT execution | Not completed",
            "Project closure and retrospective | NFA-91 technical candidate",
        ),
    )

    outstanding = read_text(DOCUMENTS[4])
    for number in range(1, 15):
        identifier = f"OW-{number:02d}"
        if identifier not in outstanding:
            raise ProjectClosureVerificationError(
                f"Outstanding-work register is missing {identifier}."
            )
    require_fragments(
        "Outstanding-work status",
        outstanding,
        (
            "No unresolved Critical or High software defect is confirmed",
            "Human UAT has not run",
            "Open external dependency",
            "Open production gate",
            "Must be completed manually in Jira",
        ),
    )

    retrospective = read_text(DOCUMENTS[5])
    require_fragments(
        "Retrospective",
        retrospective,
        (
            "## 2. What went well",
            "## 3. What was difficult",
            "## 4. What could be improved",
            "## 5. Lessons learned",
            "## 6. Achievements to carry forward",
            "## 7. Recommended next phase",
            "outdated article-pipeline expectation",
            "Docker may preserve old database credentials",
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
                raise ProjectClosureVerificationError(
                    f"{document.relative_to(ROOT)} has a missing local link: {target}"
                )


def verify_repository_evidence() -> None:
    package = json.loads(read_text(ROOT / "apps" / "web" / "package.json"))
    if package.get("version") != "0.1.0":
        raise ProjectClosureVerificationError("Closure expects frontend version 0.1.0.")

    pyproject = read_text(ROOT / "apps" / "api" / "pyproject.toml")
    if 'version = "0.1.0"' not in pyproject:
        raise ProjectClosureVerificationError("Closure expects backend version 0.1.0.")

    migration_count = len(
        tuple((ROOT / "apps" / "api" / "migrations" / "versions").glob("*.py"))
    )
    if migration_count != 15:
        raise ProjectClosureVerificationError(
            f"Closure records 15 migrations, but found {migration_count}."
        )

    require_fragments(
        "Active rights decision",
        read_text(ROOT / "docs" / "jira" / "NFA-8.md"),
        (
            "Decision | No-Go for live CNN integration",
            "Fixture-based development decision | Go",
        ),
    )
    require_fragments(
        "Release readiness boundary",
        read_text(ROOT / "docs" / "release-readiness-quality-signoff.md"),
        (
            "Conditional Go for controlled synthetic demonstration",
            "No-Go for public release",
        ),
    )
    require_fragments(
        "Handover evidence",
        read_text(ROOT / "docs" / "handover" / "reproducibility-results.md"),
        (
            "489 tests passed",
            "173 tests across 36 files",
            "Passed all 13 Chromium scenarios",
        ),
    )
    require_fragments(
        "UAT status",
        read_text(ROOT / "docs" / "uat" / "retest-and-acceptance.md"),
        (
            "No UAT retest has been performed",
            "Decision: **Pending**",
        ),
    )


def verify_repository_integration() -> None:
    readme = read_text(ROOT / "README.md")
    require_fragments(
        "README closure integration",
        readme,
        (
            "## Project closure",
            "docs/project-closure/README.md",
            "Project completed with documented limitations",
            "scripts/verify_project_closure.py",
        ),
    )

    plan = read_text(ROOT / "PROJECT_PLAN.md")
    require_fragments(
        "Project-plan closure status",
        plan,
        (
            "Plan version:** 1.1",
            "Last updated:** 9 November 2026",
            "Project completed with documented limitations",
            "docs/project-closure/README.md",
        ),
    )

    workflow = read_text(ROOT / ".github" / "workflows" / "quality.yml")
    require_fragments(
        "CI closure verification",
        workflow,
        (
            "Verify the NFA-91 project closure package",
            "python3 scripts/verify_project_closure.py",
        ),
    )


def verify_no_unsupported_claims() -> None:
    combined = "\n".join(read_text(document) for document in DOCUMENTS)
    forbidden = (
        "Live CNN integration | Done",
        "Public production release | Done",
        "Human UAT execution | Delivered",
        "production-ready application",
        "automatic LinkedIn publishing is implemented",
    )
    found = [claim for claim in forbidden if claim in combined]
    if found:
        raise ProjectClosureVerificationError(
            "Closure package contains unsupported claims: " + ", ".join(found)
        )


def verify_ascii_hyphens() -> None:
    disallowed = {"\u2010", "\u2011", "\u2012", "\u2013", "\u2014", "\u2212"}
    paths = (*DOCUMENTS, Path(__file__))
    for path in paths:
        found = sorted(set(read_text(path)) & disallowed)
        if found:
            codepoints = ", ".join(f"U+{ord(value):04X}" for value in found)
            raise ProjectClosureVerificationError(
                f"{path.relative_to(ROOT)} contains non-ASCII dash characters: {codepoints}"
            )


def main() -> None:
    verify_closure_structure()
    verify_links()
    verify_repository_evidence()
    verify_repository_integration()
    verify_no_unsupported_claims()
    verify_ascii_hyphens()
    print("NFA-91 project closure verification passed.")


if __name__ == "__main__":
    try:
        main()
    except ProjectClosureVerificationError as exc:
        raise SystemExit(f"NFA-91 verification failed: {exc}") from exc
