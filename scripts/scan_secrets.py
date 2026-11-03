"""Fail when tracked project files contain high-confidence credential patterns."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
MAX_SCANNED_FILE_BYTES = 5_000_000
SECRET_PATTERNS = {
    "AWS access key": re.compile(rb"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "GitHub token": re.compile(rb"\bgh[pousr]_[A-Za-z0-9]{36,}\b"),
    "OpenAI API key": re.compile(rb"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b"),
    "private key": re.compile(rb"-----BEGIN (?:EC |OPENSSH |RSA )?PRIVATE KEY-----"),
}


def project_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
    )
    return [
        REPOSITORY_ROOT / item.decode("utf-8")
        for item in result.stdout.split(b"\0")
        if item
    ]


def scan_repository() -> list[str]:
    findings: list[str] = []
    for path in project_files():
        relative_path = path.relative_to(REPOSITORY_ROOT)
        if relative_path.name == ".env":
            findings.append(f"tracked environment file: {relative_path}")
            continue
        if not path.is_file() or path.stat().st_size > MAX_SCANNED_FILE_BYTES:
            continue
        content = path.read_bytes()
        if b"\0" in content:
            continue
        for description, pattern in SECRET_PATTERNS.items():
            if pattern.search(content):
                findings.append(f"{description}: {relative_path}")
    return findings


def main() -> int:
    findings = scan_repository()
    if findings:
        print("Potential secrets found in tracked files:")
        for finding in findings:
            print(f"- {finding}")
        return 1
    print("Project secret scan passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
