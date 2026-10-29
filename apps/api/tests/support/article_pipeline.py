"""Reusable synthetic fixture loading for the NFA-36 pipeline suite."""

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures"


def synthetic_article_records(group: str) -> list[dict[str, Any]]:
    """Return an isolated copy of one valid synthetic fixture group."""

    document = _load_document("synthetic_articles.json")
    records = document.get(group)
    if not isinstance(records, list) or not records:
        raise ValueError(f"Synthetic fixture group '{group}' is missing or empty.")
    if not all(isinstance(record, dict) for record in records):
        raise ValueError(f"Synthetic fixture group '{group}' must contain objects.")
    return deepcopy(records)


def invalid_article_cases() -> list[dict[str, Any]]:
    """Return named invalid cases without exposing them to application code."""

    document = _load_document("invalid_articles.json")
    cases = document.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("Invalid article cases are missing or empty.")
    for case in cases:
        if (
            not isinstance(case, dict)
            or not isinstance(case.get("name"), str)
            or not isinstance(case.get("expected_error"), str)
            or not isinstance(case.get("record"), dict)
        ):
            raise ValueError(
                "Each invalid article case must have a safe name and record."
            )
    return deepcopy(cases)


def _load_document(filename: str) -> dict[str, Any]:
    path = FIXTURE_ROOT / filename
    with path.open(encoding="utf-8") as fixture_file:
        document = json.load(fixture_file)
    if not isinstance(document, dict):
        raise ValueError(f"Fixture document '{filename}' must contain an object.")
    return document
