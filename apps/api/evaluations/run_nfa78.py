"""Run the deterministic NFA-78 evaluation package without external services."""

from pathlib import Path

from app.evaluation import (
    GroundingCaseDataset,
    ImageSafetyCaseDataset,
    SyntheticArticleDataset,
    build_content_safety_report,
)

EVALUATION_DIRECTORY = Path(__file__).parent
FIXTURE_DIRECTORY = EVALUATION_DIRECTORY / "fixtures"


def build_report():
    """Load validated fixtures and return the current evaluation report."""

    articles = SyntheticArticleDataset.model_validate_json(
        (FIXTURE_DIRECTORY / "synthetic_articles.json").read_text(encoding="utf-8")
    )
    grounding_cases = GroundingCaseDataset.model_validate_json(
        (FIXTURE_DIRECTORY / "expected_claims.json").read_text(encoding="utf-8")
    )
    image_cases = ImageSafetyCaseDataset.model_validate_json(
        (FIXTURE_DIRECTORY / "sensitive_news_cases.json").read_text(encoding="utf-8")
    )
    return build_content_safety_report(
        articles=articles,
        grounding_cases=grounding_cases,
        image_cases=image_cases,
    )


def main() -> int:
    """Print machine-readable evidence and fail when a release gate is missed."""

    report = build_report()
    print(report.model_dump_json(indent=2))
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
