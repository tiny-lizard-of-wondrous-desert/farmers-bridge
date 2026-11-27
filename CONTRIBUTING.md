# Contributing

Thanks for helping improve Farmer's Bridge. Keep the rules engine independent from all interfaces.

## Development setup

```bash
uv sync --all-extras
```

Use a feature branch and make focused changes. Do not commit real player data, PINs, secrets, local databases or virtual environments.

## Architecture rules

- Put game rules and state transitions in `cardgame/engine.py` or `cardgame/models.py`.
- Put reusable interaction workflows in `cardgame/workflows.py`; interfaces should adapt prompts, not reimplement bid/trick logic.
- Keep Pygame and Streamlit imports optional and out of the base package import path.
- Validate bids and tricks separately before committing a round.
- A completed game is represented by `game.is_complete` / `game.current_round is None`; normal completion must not use exceptions for control flow.
- Do not expose another player's private hand in any online API response.
- Preserve old CSV data when changing schemas; add a migration and tests.

## Before submitting

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

For broad compatibility testing:

```bash
uv run tox
```

Add tests for new rules, invalid input, normal completion, and relevant interface/storage integration. Update README and CHANGELOG for user-visible changes. Add/update docstrings for public functions and classes.

## Pull request checklist

- [ ] The shared engine remains interface-independent.
- [ ] Bid and trick workflows are not duplicated.
- [ ] Validation handles invalid and boundary inputs.
- [ ] Tests pass and lint/format checks pass.
- [ ] CSV migrations preserve historical records.
- [ ] Documentation and changelog are updated.
- [ ] No secrets, player PINs or personal records are committed.


## Dependency groups and pre-commit

The project uses uv dependency groups:

```powershell
uv sync --group dev
uv sync --group local
uv sync --group online
uv run pre-commit install
```

The pre-commit hook updates `uv.lock` and exports `requirements.txt` (online),
`requirements-local.txt` (local) and `requirements-dev.txt` (dev) before every commit.
Do not edit generated requirement exports by hand; edit the corresponding group in
`pyproject.toml` instead.

## Private player data

Player names, history CSVs, SQLite room state and recovery checkpoints are local data
and must not be committed to the public source repository. If any data files were
previously tracked, untrack them without deleting local copies:

```powershell
git rm --cached data/players.csv data/game_history.csv
git rm --cached -r data/saves
git commit -m "Stop tracking local player data"
```

Use pseudonymous usernames rather than real names, emails or other personal details.
For Streamlit persistence, use the separate private backup repository described in
`ONLINE_PLAY.md`; keep its token in Streamlit Secrets.
