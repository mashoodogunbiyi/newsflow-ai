"""Verify NFA-87 documentation from an isolated candidate checkout."""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class CleanCheckoutVerificationError(RuntimeError):
    """Raised when the isolated documentation verification cannot complete."""


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
        raise CleanCheckoutVerificationError("Git did not return any candidate files.")

    with tempfile.TemporaryDirectory(prefix="newsflow-readme-") as temporary:
        checkout = Path(temporary)
        for relative in files:
            source = ROOT / relative
            if not source.is_file():
                continue
            destination = checkout / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination, follow_symlinks=False)

        verifier = checkout / "scripts" / "verify_readme_documentation.py"
        if not verifier.is_file():
            raise CleanCheckoutVerificationError(
                "README verifier was not copied into the isolated checkout."
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
            raise CleanCheckoutVerificationError(detail)

    print("NFA-87 isolated candidate checkout verification passed.")


if __name__ == "__main__":
    try:
        main()
    except (CleanCheckoutVerificationError, subprocess.CalledProcessError) as exc:
        raise SystemExit(f"NFA-87 clean-checkout verification failed: {exc}") from exc
