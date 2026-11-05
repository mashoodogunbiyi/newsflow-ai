"""Verify that NFA-85 deployment documentation matches repository contracts."""

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEPLOYMENT_DIRECTORY = ROOT / "docs" / "deployment"
DOCUMENTS = {
    "deployment": DEPLOYMENT_DIRECTORY / "deployment-guide.md",
    "environment": DEPLOYMENT_DIRECTORY / "environment-configuration.md",
    "operations": DEPLOYMENT_DIRECTORY / "operations-runbook.md",
    "recovery": DEPLOYMENT_DIRECTORY / "backup-and-recovery.md",
}


class DocumentationVerificationError(RuntimeError):
    """Raised when deployment documentation is missing or inconsistent."""


def read_text(path: Path) -> str:
    if not path.is_file():
        raise DocumentationVerificationError(f"Missing required document: {path}")
    return path.read_text(encoding="utf-8")


def require_fragments(label: str, text: str, fragments: tuple[str, ...]) -> None:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        formatted = ", ".join(repr(item) for item in missing)
        raise DocumentationVerificationError(
            f"{label} is missing required repository contract text: {formatted}"
        )


def settings_environment_names() -> set[str]:
    config_path = ROOT / "apps" / "api" / "app" / "core" / "config.py"
    tree = ast.parse(read_text(config_path))
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "Settings":
            return {
                item.target.id.upper()
                for item in node.body
                if isinstance(item, ast.AnnAssign)
                and isinstance(item.target, ast.Name)
                and not item.target.id.startswith("_")
            }
    raise DocumentationVerificationError("Could not locate the Settings class.")


def verify_environment_reference(text: str) -> None:
    documented_names = set(re.findall(r"`([A-Z][A-Z0-9_]*)`", text))
    expected_names = settings_environment_names() | {
        "API_INTERNAL_BASE_URL",
        "BACKEND_PORT",
        "FRONTEND_PORT",
        "NEXT_PUBLIC_API_BASE_URL",
        "POSTGRES_DB",
        "POSTGRES_PASSWORD",
        "POSTGRES_PORT",
        "POSTGRES_USER",
    }
    missing = sorted(expected_names - documented_names)
    if missing:
        raise DocumentationVerificationError(
            "Environment guide is missing configured variables: " + ", ".join(missing)
        )


def verify_ascii_hyphens() -> None:
    disallowed_dashes = {"\u2010", "\u2011", "\u2012", "\u2013", "\u2014", "\u2212"}
    for path in DOCUMENTS.values():
        text = read_text(path)
        found = sorted(set(text) & disallowed_dashes)
        if found:
            codepoints = ", ".join(f"U+{ord(value):04X}" for value in found)
            raise DocumentationVerificationError(
                f"{path} contains non-ASCII dash characters: {codepoints}"
            )


def main() -> None:
    texts = {name: read_text(path) for name, path in DOCUMENTS.items()}

    require_fragments(
        "Deployment guide",
        texts["deployment"],
        (
            "Public or production release: No-Go.",
            "Live CNN ingestion: No-Go",
            "approved private object-storage adapter",
            "GET /health",
            "GET /ready",
            "alembic upgrade head",
            "Application rollback and data recovery are different operations.",
        ),
    )
    require_fragments(
        "Environment guide",
        texts["environment"],
        (
            "`APP_ENV`",
            "`DATABASE_URL`",
            "`NEWS_SOURCE_MODE`",
            "`OPENAI_API_KEY`",
            "`IMAGE_STORAGE_BACKEND`",
            "Never expose a secret through a `NEXT_PUBLIC_` setting.",
        ),
    )
    require_fragments(
        "Operations runbook",
        texts["operations"],
        (
            "Public or production release remains No-Go.",
            "`GET /api/admin/sync/health`",
            "`GET /api/admin/generations/metrics`",
            "Set `NEWS_SOURCE_MODE=disabled`",
            "Do not add `--volumes` when data must be preserved.",
        ),
    )
    require_fragments(
        "Backup and recovery guide",
        texts["recovery"],
        (
            "does not currently have a production backup system",
            "A local Docker named volume is persistent development storage. It is not a backup.",
            "PostgreSQL and private object storage do not share one atomic transaction.",
            "Reapply deletion tombstones",
            "Production release remains No-Go",
        ),
    )

    verify_environment_reference(texts["environment"])
    verify_ascii_hyphens()

    readme = read_text(ROOT / "README.md")
    for path in DOCUMENTS.values():
        relative = path.relative_to(ROOT).as_posix()
        if relative not in readme:
            raise DocumentationVerificationError(
                f"README does not link to required document: {relative}"
            )

    print("NFA-85 deployment documentation verification passed.")


if __name__ == "__main__":
    try:
        main()
    except DocumentationVerificationError as exc:
        raise SystemExit(f"NFA-85 verification failed: {exc}") from exc
