"""Regenerate the uv lockfile and one pip requirements export before each commit."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(*args: str) -> None:
    subprocess.run(args, cwd=ROOT, check=True)


def main() -> None:
    uv = shutil.which("uv")
    if uv is None:
        candidates = [
            ROOT / ".venv" / "Scripts" / "uv.exe",
            ROOT / ".venv" / "bin" / "uv",
        ]
        uv = next((str(path) for path in candidates if path.is_file()), None)
    if uv is None:
        raise FileNotFoundError(
            "uv was not found on PATH or in the project .venv. Install uv and reopen the terminal."
        )
    run(uv, "lock")
    run(
        uv, "export", "--locked", "--all-groups", "--no-hashes",
        "--no-emit-project", "--output-file", "requirements.txt",
    )
    run("git", "add", "uv.lock", "requirements.txt")


if __name__ == "__main__":
    try:
        main()
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        print(f"Dependency export failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
