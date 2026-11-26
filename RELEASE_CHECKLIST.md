# Release checklist

- [ ] `uv sync --all-extras` succeeds on a clean environment.
- [ ] `uv run pytest` passes.
- [ ] `uv run ruff check .` passes.
- [ ] `uv run ruff format --check .` passes.
- [ ] Pygame tested manually on Windows/macOS/Linux.
- [ ] CSV migration tested against a copy of real historical data.
- [ ] Game completion and early window-close behavior verified.
- [ ] README, CHANGELOG and CONTRIBUTING updated.
- [ ] Online mode security, authentication and persistent database reviewed before public deployment.
