"""NFA-75 security threat-model completeness and traceability checks."""

import re
from pathlib import Path

THREAT_MODEL = Path(__file__).resolve().parents[3] / "docs" / "security-threat-model.md"


def _document() -> str:
    return THREAT_MODEL.read_text(encoding="utf-8")


def _threat_rows(document: str) -> list[list[str]]:
    rows = []
    for line in document.splitlines():
        if line.startswith("| TM-"):
            rows.append([cell.strip() for cell in line.strip("|").split("|")])
    return rows


def test_threat_model_covers_architecture_assets_boundaries_and_dependencies() -> None:
    document = _document()

    required_sections = {
        "## 4. Architecture and data flows",
        "## 5. Sensitive assets",
        "## 6. Trust boundaries",
        "## 7. External services and dependencies",
        "## 8. Threat register",
        "## 9. Mitigation plan and responsible tasks",
        "## 10. Verification requirements",
        "## 11. Residual risk and release decision",
        "## 12. Review triggers and release checklist",
    }
    assert required_sections.issubset(document.splitlines())

    for component in (
        "Untrusted browser",
        "Next.js frontend",
        "FastAPI",
        "PostgreSQL",
        "OpenAI API",
        "Private image storage",
        "Article provider",
        "GitHub Actions",
    ):
        assert component in document

    for boundary_number in range(1, 8):
        assert f"TB-{boundary_number:02d}" in document
    for asset_number in range(1, 11):
        assert f"A-{asset_number:02d}" in document


def test_stride_register_has_unique_scored_and_owned_threats() -> None:
    rows = _threat_rows(_document())

    assert len(rows) >= 20
    assert all(len(row) == 12 for row in rows)
    identifiers = [row[0] for row in rows]
    assert len(identifiers) == len(set(identifiers))
    assert all(re.fullmatch(r"TM-\d{2}", identifier) for identifier in identifiers)

    categories = {row[1] for row in rows}
    assert categories == {
        "Spoofing",
        "Tampering",
        "Repudiation",
        "Information disclosure",
        "Denial of service",
        "Elevation of privilege",
    }

    for row in rows:
        likelihood = int(row[4])
        impact = int(row[5])
        assert 1 <= likelihood <= 5
        assert 1 <= impact <= 5
        expected_severity = (
            "Critical"
            if likelihood * impact >= 16
            else "High"
            if likelihood * impact >= 10
            else "Medium"
            if likelihood * impact >= 5
            else "Low"
        )
        assert row[6] == expected_severity
        assert row[7]
        assert row[8]
        assert row[9]
        assert row[10]
        assert "Owner" in row[11]


def test_every_significant_threat_has_mitigation_and_verification_traceability() -> (
    None
):
    rows = _threat_rows(_document())
    significant = [row for row in rows if row[6] in {"High", "Critical"}]

    assert significant
    for row in significant:
        mitigation = row[8]
        verification = row[9]
        assert "SEC-" in mitigation or "NFA-" in mitigation, row[0]
        assert "test_" in verification or "SEC-" in verification, row[0]
        assert any(severity in row[10] for severity in ("Low", "Medium", "High")), row[
            0
        ]


def test_required_attack_classes_and_release_gates_are_explicit() -> None:
    document = _document().lower()

    for attack_class in (
        "authentication",
        "session",
        "object-level authorisation",
        "sql",
        "cross-site request forgery",
        "cross site scripting",
        "server-side request forgery",
        "provider credential",
        "prompt injection",
        "private image",
        "unsafe file",
        "logging",
        "supply chain",
    ):
        assert attack_class in document

    for task_number in range(1, 7):
        assert f"sec-{task_number:02d}" in document
    assert "no unresolved critical risk is accepted" in document
    assert "before any staging or production release" in document
    assert "live cnn access remains blocked" in document


def test_document_contains_no_real_secret_material() -> None:
    document = _document()

    assert not re.search(r"\bsk-[A-Za-z0-9_-]{16,}\b", document)
    assert "postgresql://" not in document
    assert "BEGIN PRIVATE KEY" not in document
    assert "YOUR_CHOSEN_PASSWORD" not in document
