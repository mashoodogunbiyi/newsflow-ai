"""Verify the NFA-87 README and developer-documentation contract."""

from __future__ import annotations

import json
import re
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
SUPPORTING_DOCUMENTS = (
    ROOT / "docs" / "developer-guide.md",
    ROOT / "docs" / "api-reference.md",
    ROOT / "docs" / "screenshots" / "README.md",
)
SCREENSHOTS = (
    ROOT / "docs" / "screenshots" / "homepage.png",
    ROOT / "docs" / "screenshots" / "article-dashboard.png",
    ROOT / "docs" / "screenshots" / "generation-workspace.png",
    ROOT / "docs" / "screenshots" / "content-library.png",
)


class ReadmeVerificationError(RuntimeError):
    """Raised when the portfolio documentation no longer matches the project."""


def read_text(path: Path) -> str:
    if not path.is_file():
        raise ReadmeVerificationError(f"Missing required file: {path}")
    return path.read_text(encoding="utf-8")


def require_fragments(label: str, text: str, fragments: tuple[str, ...]) -> None:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        formatted = ", ".join(repr(item) for item in missing)
        raise ReadmeVerificationError(f"{label} is missing: {formatted}")


def verify_readme_sections(text: str) -> None:
    headings = (
        "# NewsFlow AI",
        "## Overview",
        "## Problem statement",
        "## Implemented features",
        "## Technology stack",
        "## System architecture",
        "## Repository structure",
        "## Getting started",
        "## Running with Docker",
        "## Running services manually",
        "## Database migrations and seed data",
        "## Running tests",
        "## API documentation",
        "## Screenshots",
        "## Security and privacy",
        "## Source rights and AI safety",
        "## Known limitations",
        "## Future improvements",
        "## Project status",
        "## Documentation",
        "## Contributing workflow",
        "## Licence",
    )
    require_fragments("README headings", text, headings)

    require_fragments(
        "README status and safety statements",
        text,
        (
            "Public production release and live CNN integration remain **No-Go**.",
            "The application never automatically publishes to LinkedIn.",
            "Live CNN access is not authorised.",
            "synthetic fixture source",
            "Generated text may contain mistakes",
            "No software licence has been selected.",
        ),
    )

    require_fragments(
        "README setup and quality commands",
        text,
        (
            "cp .env.example .env",
            "docker compose up --build --detach --wait",
            "docker compose down",
            'python -m pip install -e ".[dev]"',
            "alembic upgrade head",
            "fastapi dev app/main.py",
            "npm ci",
            "npm run dev",
            'pytest -m "not live_ai"',
            "npm run test:e2e",
            "python3 scripts/scan_secrets.py",
        ),
    )

    require_fragments(
        "README API documentation",
        text,
        (
            "http://localhost:8000/docs",
            "http://localhost:8000/redoc",
            "http://localhost:8000/openapi.json",
            "docs/api-reference.md",
        ),
    )


def local_link_targets(path: Path) -> list[str]:
    return re.findall(r"!?(?:\[[^\]]*\])\(([^)]+)\)", read_text(path))


def verify_local_links() -> None:
    for document in (README, *SUPPORTING_DOCUMENTS):
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
                raise ReadmeVerificationError(
                    f"{document.relative_to(ROOT)} has a missing local link: {target}"
                )


def png_dimensions(path: Path) -> tuple[int, int]:
    if not path.is_file():
        raise ReadmeVerificationError(f"Missing required screenshot: {path}")
    with path.open("rb") as image:
        header = image.read(24)
    if len(header) != 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
        raise ReadmeVerificationError(f"Screenshot is not a valid PNG: {path}")
    return struct.unpack(">II", header[16:24])


def verify_screenshots(readme_text: str) -> None:
    manifest = read_text(SUPPORTING_DOCUMENTS[-1])
    for path in SCREENSHOTS:
        relative = path.relative_to(ROOT).as_posix()
        if relative not in readme_text:
            raise ReadmeVerificationError(f"README does not display {relative}")
        if path.name not in manifest:
            raise ReadmeVerificationError(
                f"Screenshot manifest does not list {path.name}"
            )
        width, height = png_dimensions(path)
        if width < 1200 or height < 700:
            raise ReadmeVerificationError(
                f"{path.name} is too small for documentation: {width}x{height}"
            )

    require_fragments(
        "Screenshot provenance",
        manifest,
        (
            "deterministic local Playwright API fixture",
            "synthetic accounts, articles, drafts, and images",
            "no live provider key or network request",
            "npm run screenshots:docs",
        ),
    )


def verify_frontend_contract() -> None:
    package = json.loads(read_text(ROOT / "apps" / "web" / "package.json"))
    scripts = package.get("scripts", {})
    required_scripts = {
        "dev",
        "build",
        "lint",
        "performance:bundle",
        "screenshots:docs",
        "format:check",
        "test",
        "test:e2e",
        "typecheck",
    }
    missing = sorted(required_scripts - scripts.keys())
    if missing:
        raise ReadmeVerificationError(
            "Frontend package is missing documented scripts: " + ", ".join(missing)
        )

    dependencies = package.get("dependencies", {})
    if not dependencies.get("next", "").startswith("16"):
        raise ReadmeVerificationError("README stack expects Next.js 16.")
    if not dependencies.get("react", "").startswith("19"):
        raise ReadmeVerificationError("README stack expects React 19.")


def verify_backend_contract() -> None:
    require_fragments(
        "Backend package contract",
        read_text(ROOT / "apps" / "api" / "pyproject.toml"),
        (
            'requires-python = ">=3.10,<3.15"',
            '"fastapi[standard-no-fastapi-cloud-cli]',
            '"openai>=',
            '"SQLAlchemy[asyncio]',
            '"alembic>=',
            '"Pillow>=',
        ),
    )

    require_fragments(
        "FastAPI documentation configuration",
        read_text(ROOT / "apps" / "api" / "app" / "main.py"),
        ('docs_url="/docs"', 'redoc_url="/redoc"', 'openapi_url="/openapi.json"'),
    )


def verify_runtime_contract() -> None:
    compose = read_text(ROOT / "compose.yaml")
    require_fragments(
        "Docker Compose",
        compose,
        ("database:", "migrate:", "backend:", "frontend:", "postgres_data:"),
    )

    require_fragments(
        "Authorised article provider factory",
        read_text(ROOT / "apps" / "api" / "app" / "providers" / "factory.py"),
        (
            'settings.news_source_mode == "fixture"',
            "FixtureNewsProvider()",
            "raise SourceNotAuthorisedError",
        ),
    )

    require_fragments(
        "Environment template",
        read_text(ROOT / ".env.example"),
        (
            "NEWS_SOURCE_MODE=fixture",
            "OPENAI_API_KEY=your_openai_api_key_here",
            "IMAGE_STORAGE_BACKEND=local",
        ),
    )


def verify_ascii_hyphens() -> None:
    disallowed = {"\u2010", "\u2011", "\u2012", "\u2013", "\u2014", "\u2212"}
    for path in (README, *SUPPORTING_DOCUMENTS):
        found = sorted(set(read_text(path)) & disallowed)
        if found:
            codepoints = ", ".join(f"U+{ord(value):04X}" for value in found)
            raise ReadmeVerificationError(
                f"{path.relative_to(ROOT)} contains non-ASCII dash characters: {codepoints}"
            )


def main() -> None:
    readme_text = read_text(README)
    for document in SUPPORTING_DOCUMENTS:
        read_text(document)

    verify_readme_sections(readme_text)
    verify_local_links()
    verify_screenshots(readme_text)
    verify_frontend_contract()
    verify_backend_contract()
    verify_runtime_contract()
    verify_ascii_hyphens()

    print("NFA-87 README documentation verification passed.")


if __name__ == "__main__":
    try:
        main()
    except ReadmeVerificationError as exc:
        raise SystemExit(f"NFA-87 verification failed: {exc}") from exc
