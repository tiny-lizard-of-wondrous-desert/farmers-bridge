"""Regenerate lockfile and pip requirement exports before each commit."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(*args: str) -> None:
    subprocess.run(args, cwd=ROOT, check=True)


def main() -> None:
    uv = "uv"
    run(uv, "lock")
    exports = {
        "online": "requirements.txt",
        "local": "requirements-local.txt",
        "dev": "requirements-dev.txt",
    }
    for group, output in exports.items():
        run(
            uv, "export", "--locked", "--no-hashes", "--no-emit-project",
            "--only-group", group, "--output-file", output,
        )
    run("git", "add", "uv.lock", *exports.values())


if __name__ == "__main__":
    try:
        main()
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        print(f"Dependency export failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
