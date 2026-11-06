"""Verify that NFA-86 diagrams remain aligned with repository architecture."""

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARCHITECTURE_DIRECTORY = ROOT / "docs" / "architecture"
DOCUMENTS = {
    "system": ARCHITECTURE_DIRECTORY / "system-architecture.md",
    "flows": ARCHITECTURE_DIRECTORY / "data-flow.md",
    "decisions": ARCHITECTURE_DIRECTORY / "architecture-decisions.md",
}


class ArchitectureVerificationError(RuntimeError):
    """Raised when architecture documentation is missing or inaccurate."""


def read_text(path: Path) -> str:
    if not path.is_file():
        raise ArchitectureVerificationError(f"Missing required file: {path}")
    return path.read_text(encoding="utf-8")


def require_fragments(label: str, text: str, fragments: tuple[str, ...]) -> None:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        joined = ", ".join(repr(fragment) for fragment in missing)
        raise ArchitectureVerificationError(f"{label} is missing: {joined}")


def mermaid_blocks(text: str) -> list[str]:
    return re.findall(r"```mermaid\n(.*?)```", text, flags=re.DOTALL)


def verify_mermaid_contract(label: str, text: str, minimum: int) -> None:
    blocks = mermaid_blocks(text)
    if len(blocks) < minimum:
        raise ArchitectureVerificationError(
            f"{label} must contain at least {minimum} Mermaid diagrams; found {len(blocks)}."
        )
    for index, block in enumerate(blocks, start=1):
        first_line = block.strip().splitlines()[0]
        if not first_line.startswith(("flowchart ", "sequenceDiagram")):
            raise ArchitectureVerificationError(
                f"{label} Mermaid diagram {index} has an unsupported opening: {first_line}"
            )


def route_prefix(path: Path) -> str:
    tree = ast.parse(read_text(path))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if not any(
            isinstance(target, ast.Name) and target.id == "router"
            for target in node.targets
        ):
            continue
        if not isinstance(node.value, ast.Call):
            continue
        for keyword in node.value.keywords:
            if (
                keyword.arg == "prefix"
                and isinstance(keyword.value, ast.Constant)
                and isinstance(keyword.value.value, str)
            ):
                return keyword.value.value
    raise ArchitectureVerificationError(f"Could not find router prefix in {path}")


def verify_route_contract(flow_text: str) -> None:
    route_directory = ROOT / "apps" / "api" / "app" / "api" / "routes"
    route_expectations = {
        "articles.py": "/api/articles",
        "article_sync.py": "/api/v1/admin/articles",
        "auth.py": "/api/v1/auth",
        "generations.py": "/api/generations",
        "image_regeneration.py": "/api/images",
        "saved_drafts.py": "/api/v1/drafts",
    }
    for filename, expected in route_expectations.items():
        actual = route_prefix(route_directory / filename)
        if actual != expected:
            raise ArchitectureVerificationError(
                f"{filename} prefix changed from {expected} to {actual}; update diagrams."
            )

    documented_endpoints = (
        "/api/v1/admin/articles/sync",
        "/api/generations",
        "/api/images",
        "/api/v1/drafts",
    )
    require_fragments("Data-flow route contract", flow_text, documented_endpoints)


def verify_repository_evidence() -> None:
    evidence = {
        ROOT / "apps/api/app/providers/factory.py": (
            'settings.news_source_mode == "fixture"',
            "FixtureNewsProvider()",
            "raise SourceNotAuthorisedError",
        ),
        ROOT / "apps/api/app/api/dependencies.py": (
            "require_authenticated_session",
            "require_csrf_authenticated_session",
            'SESSION_COOKIE_NAME = "newsflow_session"',
        ),
        ROOT / "apps/api/app/services/image_storage.py": (
            "class PrivateImageStorage",
            "class LocalPrivateImageStorage",
        ),
        ROOT / "apps/api/app/core/config.py": (
            'if self.app_env in {"staging", "production"}',
            "Configure an approved private object-storage adapter before deployment.",
        ),
        ROOT / "apps/web/app/api/generations/route.ts": ("proxyGenerationRequest",),
        ROOT / "apps/web/app/api/images/route.ts": ("proxyImageGenerationRequest",),
        ROOT / "apps/web/app/api/drafts/route.ts": ("proxyDraftCreation",),
    }
    for path, fragments in evidence.items():
        require_fragments(str(path.relative_to(ROOT)), read_text(path), fragments)


def verify_ascii_hyphens() -> None:
    disallowed = {"\u2010", "\u2011", "\u2012", "\u2013", "\u2014", "\u2212"}
    for path in DOCUMENTS.values():
        found = sorted(set(read_text(path)) & disallowed)
        if found:
            codepoints = ", ".join(f"U+{ord(value):04X}" for value in found)
            raise ArchitectureVerificationError(
                f"{path} contains non-ASCII dash characters: {codepoints}"
            )


def verify_local_links() -> None:
    for path in DOCUMENTS.values():
        for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", read_text(path)):
            local_target = target.split("#", maxsplit=1)[0]
            if not local_target or "://" in local_target:
                continue
            resolved = (path.parent / local_target).resolve()
            if not resolved.is_relative_to(ROOT) or not resolved.exists():
                raise ArchitectureVerificationError(
                    f"{path} contains a missing local link target: {target}"
                )


def main() -> None:
    texts = {name: read_text(path) for name, path in DOCUMENTS.items()}

    require_fragments(
        "System architecture",
        texts["system"],
        (
            "Next.js 16 and React 19",
            "FastAPI",
            "PostgreSQL 16",
            "OpenAI APIs",
            "Synthetic fixture provider",
            "Local private image storage",
            "Live CNN integration",
            "Blocked - not authorised",
            "Authentication and authorisation boundary",
            "External provider trust boundary",
            "Proposed - release blocker",
        ),
    )
    require_fragments(
        "Data flows",
        texts["flows"],
        (
            "Article ingestion flow",
            "LinkedIn text generation flow",
            "Image generation and secure delivery flow",
            "Draft saving and content library flow",
            "Content export flow",
            "Production scheduler",
            "Proposed - not implemented",
            "Live CNN adapter",
            "Blocked",
            "human review",
        ),
    )
    require_fragments(
        "Architecture decisions",
        texts["decisions"],
        tuple(f"AD-{number:02d}" for number in range(1, 11))
        + (
            "ADR-001",
            "Open decisions",
            "Production release stays No-Go",
        ),
    )

    verify_mermaid_contract("System architecture", texts["system"], minimum=4)
    verify_mermaid_contract("Data flows", texts["flows"], minimum=7)
    verify_route_contract(texts["flows"])
    verify_repository_evidence()
    verify_ascii_hyphens()
    verify_local_links()

    readme = read_text(ROOT / "README.md")
    for path in DOCUMENTS.values():
        relative = path.relative_to(ROOT).as_posix()
        if relative not in readme:
            raise ArchitectureVerificationError(
                f"README does not link to required document: {relative}"
            )

    print("NFA-86 architecture documentation verification passed.")


if __name__ == "__main__":
    try:
        main()
    except ArchitectureVerificationError as exc:
        raise SystemExit(f"NFA-86 verification failed: {exc}") from exc
