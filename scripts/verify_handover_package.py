"""Verify the NFA-90 handover package against repository contracts."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HANDOVER = ROOT / "docs" / "handover"
DOCUMENTS = (
    HANDOVER / "README.md",
    HANDOVER / "reproducibility-checklist.md",
    HANDOVER / "reproducibility-results.md",
    HANDOVER / "maintenance-guide.md",
    HANDOVER / "handover-checklist.md",
)


class HandoverVerificationError(RuntimeError):
    """Raised when the handover package no longer matches the repository."""


def read_text(path: Path) -> str:
    if not path.is_file():
        raise HandoverVerificationError(f"Missing required file: {path}")
    return path.read_text(encoding="utf-8")


def require_fragments(label: str, text: str, fragments: tuple[str, ...]) -> None:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        formatted = ", ".join(repr(item) for item in missing)
        raise HandoverVerificationError(f"{label} is missing: {formatted}")


def verify_document_structure() -> None:
    overview = read_text(DOCUMENTS[0])
    require_fragments(
        "Handover overview",
        overview,
        (
            "## 2. Handover status",
            "375cdcb2557b8953a8776654b563ae9001f0b9e2",
            "14c97464be98d7d6a4275158b7215401122974c7",
            "PR #82",
            "## 3. Package contents",
            "## 4. Reproducibility boundary",
            "## 5. First actions for a new maintainer",
            "## 6. Ownership and final acceptance",
            "Live CNN integration | No-Go",
        ),
    )

    checklist = read_text(DOCUMENTS[1])
    require_fragments(
        "Reproducibility checklist",
        checklist,
        (
            "## 3. Repository and version",
            "verify_handover_clean_checkout.py",
            "## 4. Secret and configuration safety",
            "git check-ignore -v .env",
            "## 5. Integrated Docker setup",
            "verify_docker_packaging.sh",
            "## 7. Database migration and synthetic seed data",
            "## 8. Automated verification",
            'pytest -m "not live_ai"',
            "npm run test:e2e",
            "## 9. Primary demonstration workflow",
            "## 11. Repeatability and final capture",
            "git pull --ff-only origin main",
        ),
    )

    results = read_text(DOCUMENTS[2])
    require_fragments(
        "Reproducibility results",
        results,
        (
            "## 1. Record metadata",
            "## 2. Verification environment",
            "## 3. Executed results",
            "## 4. Reproducibility conclusions",
            "## 5. Gaps and unresolved items",
            "## 6. Failure and retest record",
            "Final merged commit | `14c97464be98d7d6a4275158b7215401122974c7`",
        ),
    )

    maintenance = read_text(DOCUMENTS[3])
    require_fragments(
        "Maintenance guide",
        maintenance,
        (
            "## 2. Repository ownership map",
            "## 4. Database maintenance",
            "## 5. Authentication and authorisation maintenance",
            "## 6. Article-source and rights maintenance",
            "## 7. OpenAI and AI-safety maintenance",
            "## 9. Monitoring, backup, and recovery",
            "## 11. Outstanding maintenance information",
        ),
    )

    handover_checklist = read_text(DOCUMENTS[4])
    require_fragments(
        "Final handover checklist",
        handover_checklist,
        (
            "## 1. Technical package",
            "## 2. NFA-90 verification",
            "## 3. Final version capture after merge",
            "## 4. Owner review",
            "## 5. Explicit No-Go items",
            "## 6. Approval record",
            "PR #82",
            "Mashood Ogunbiyi | Accepted handover merge for controlled local scope",
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
                raise HandoverVerificationError(
                    f"{document.relative_to(ROOT)} has a missing local link: {target}"
                )


def verify_repository_contract() -> None:
    required = (
        ROOT / "apps" / "api",
        ROOT / "apps" / "web",
        ROOT / "docs",
        ROOT / "scripts",
        ROOT / "compose.yaml",
        ROOT / ".env.example",
        ROOT / ".gitignore",
        ROOT / "README.md",
        ROOT / "PROJECT_PLAN.md",
        ROOT / ".github" / "workflows" / "quality.yml",
    )
    missing = [str(path.relative_to(ROOT)) for path in required if not path.exists()]
    if missing:
        raise HandoverVerificationError(
            "Repository structure is missing: " + ", ".join(missing)
        )

    pyproject = read_text(ROOT / "apps" / "api" / "pyproject.toml")
    if 'version = "0.1.0"' not in pyproject:
        raise HandoverVerificationError(
            "The handover records application version 0.1.0."
        )

    package = json.loads(read_text(ROOT / "apps" / "web" / "package.json"))
    if package.get("version") != "0.1.0":
        raise HandoverVerificationError("Frontend version must match handover 0.1.0.")
    if package.get("scripts", {}).get("demo") != "node scripts/start-demonstration.mjs":
        raise HandoverVerificationError(
            "The documented npm run demo command is missing."
        )

    compose = read_text(ROOT / "compose.yaml")
    require_fragments(
        "Docker Compose contract",
        compose,
        (
            "database:",
            "migrate:",
            "demo-data:",
            "backend:",
            "frontend:",
            "postgres_data:",
            "image_storage_data:",
            "condition: service_healthy",
            "condition: service_completed_successfully",
        ),
    )

    environment = read_text(ROOT / ".env.example")
    require_fragments(
        "Environment template",
        environment,
        (
            "POSTGRES_USER=your_local_user",
            "POSTGRES_PASSWORD=your_local_password",
            "OPENAI_API_KEY=your_openai_api_key_here",
            "NEWS_SOURCE_MODE=fixture",
            "SEED_DATA_ENABLED=false",
        ),
    )
    if re.search(r"\bsk-[A-Za-z0-9_-]{16,}\b", environment):
        raise HandoverVerificationError(".env.example contains an OpenAI-like secret.")

    gitignore = read_text(ROOT / ".gitignore")
    require_fragments(
        ".gitignore",
        gitignore,
        (".env", "!.env.example", ".venv/", "node_modules/", ".local/"),
    )


def verify_readme_and_ci() -> None:
    readme = read_text(ROOT / "README.md")
    require_fragments(
        "README handover integration",
        readme,
        (
            "## Handover and reproducibility",
            "docs/handover/README.md",
            "scripts/verify_handover_package.py",
            "scripts/verify_handover_clean_checkout.py",
        ),
    )

    workflow = read_text(ROOT / ".github" / "workflows" / "quality.yml")
    require_fragments(
        "CI handover verification",
        workflow,
        (
            "Verify the NFA-90 handover package",
            "python3 scripts/verify_handover_package.py",
            "python3 scripts/verify_handover_clean_checkout.py",
        ),
    )


def verify_ascii_hyphens() -> None:
    disallowed = {"\u2010", "\u2011", "\u2012", "\u2013", "\u2014", "\u2212"}
    paths = (*DOCUMENTS, Path(__file__))
    for path in paths:
        found = sorted(set(read_text(path)) & disallowed)
        if found:
            codepoints = ", ".join(f"U+{ord(value):04X}" for value in found)
            raise HandoverVerificationError(
                f"{path.relative_to(ROOT)} contains non-ASCII dash characters: {codepoints}"
            )


def main() -> None:
    verify_document_structure()
    verify_links()
    verify_repository_contract()
    verify_readme_and_ci()
    verify_ascii_hyphens()
    print("NFA-90 handover package verification passed.")


if __name__ == "__main__":
    try:
        main()
    except HandoverVerificationError as exc:
        raise SystemExit(f"NFA-90 verification failed: {exc}") from exc
