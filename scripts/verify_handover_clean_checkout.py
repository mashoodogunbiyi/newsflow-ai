"""Verify NFA-90 documentation from an isolated candidate checkout."""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERIFIERS = (
    "verify_handover_package.py",
    "verify_architecture_documentation.py",
    "verify_deployment_documentation.py",
    "verify_demonstration_package.py",
    "verify_technical_report.py",
    "verify_readme_documentation.py",
)


class CleanCheckoutVerificationError(RuntimeError):
    """Raised when isolated handover verification cannot complete."""


def candidate_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return [Path(item.decode()) for item in result.stdout.split(b"\0") if item]


def main() -> None:
    files = candidate_files()
    if not files:
        raise CleanCheckoutVerificationError("Git did not return candidate files.")

    required = {
        Path("docs/handover") / path.name
        for path in (ROOT / "docs/handover").glob("*.md")
    }
    required.update(Path("scripts") / verifier for verifier in VERIFIERS)
    required.add(Path("scripts/verify_handover_clean_checkout.py"))
    candidate_set = set(files)
    missing = sorted(str(path) for path in required if path not in candidate_set)
    if missing:
        raise CleanCheckoutVerificationError(
            "Required handover files are absent from the candidate set: "
            + ", ".join(missing)
        )

    with tempfile.TemporaryDirectory(prefix="newsflow-handover-") as temporary:
        checkout = Path(temporary)
        for relative in files:
            source = ROOT / relative
            if not source.is_file():
                continue
            destination = checkout / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination, follow_symlinks=False)

        for verifier_name in VERIFIERS:
            verifier = checkout / "scripts" / verifier_name
            if not verifier.is_file():
                raise CleanCheckoutVerificationError(
                    f"Missing isolated verifier: {verifier_name}"
                )
            result = subprocess.run(
                [sys.executable, str(verifier)],
                cwd=checkout,
                check=False,
                text=True,
                capture_output=True,
            )
            if result.returncode != 0:
                detail = result.stderr.strip() or result.stdout.strip()
                raise CleanCheckoutVerificationError(
                    f"{verifier_name} failed in the isolated checkout: {detail}"
                )

    print("NFA-90 isolated candidate checkout verification passed.")


if __name__ == "__main__":
    try:
        main()
    except (CleanCheckoutVerificationError, subprocess.CalledProcessError) as exc:
        raise SystemExit(f"NFA-90 clean-checkout verification failed: {exc}") from exc
