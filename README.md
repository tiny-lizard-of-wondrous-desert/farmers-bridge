# Farmer's Bridge

A Python implementation of Farmer's Bridge with a shared game engine and three intended gameplay modes.

## Project layout

- `cardgame/models.py`: `Suit` enum, `Card`, `Player`, legal plays and trick winner. The game engine keeps its own lightweight domain-card model; Pygame artwork comes from the `pygame-cards` standard 52-card set.
- `cardgame/engine.py`: round schedule, dealer rotation, bid/trick validation, dealing, scoring and rankings.
- `cardgame/workflows.py`: shared bid/trick collection and correction workflows.
- `cardgame/interfaces/manual.py`: in-person mode; players use physical cards and enter totals.
- `cardgame/interfaces/pygame_ui.py`: local pass-and-play card interface.
- `cardgame/storage.py`: player directory, game-history CSV persistence and local recovery checkpoints.
- `cardgame/backup.py`: optional standard-library backup/restore to a separate private GitHub repository.
- `streamlit_app.py` and `cardgame/online.py`: cross-session room, private hands, bidding, card play, trick calculation and scoring using a shared SQLite room store.
- `tests/`: unit, component integration and full-game integration tests.

## Requirements and setup

Python 3.11 or newer. Install [uv](https://docs.astral.sh/uv/), then from the project directory:

```powershell
uv lock
uv sync --no-default-groups                  # in-person mode, standard library only
uv sync --no-default-groups --group local    # Pygame pass-and-play (pygame-cards)
uv sync --no-default-groups --group online  # Streamlit online play
uv sync --group dev                         # tests, coverage, Ruff, tox and pre-commit
```

The base engine uses only the Python standard library. No optional group is installed by default.
Optional dependencies are grouped in `pyproject.toml`: `local`, `online` and `dev`. `requirements.txt` is the generated Streamlit
Community Cloud export for the `online` group; `requirements-local.txt` and
`requirements-dev.txt` are generated exports for the other groups. The older
`requirements-pygame.txt` and `requirements-web.txt` remain as compatibility aliases.

Run the in-person game after the base environment is synced:

```bash
uv run --no-sync python main.py
```

Run the Pygame app by choosing mode 2 during setup. Run the Streamlit lobby separately:

```bash
uv sync --no-default-groups --group online
uv run --no-sync streamlit run streamlit_app.py
```

## Tests, lint and formatting

```bash
uv run pytest
uv run pytest --cov=cardgame --cov-report=term-missing
uv run ruff check .
uv run ruff format --check .
uv run ruff format .
uv run tox
uv run pre-commit install
```

`tox` runs tests across Python 3.11, 3.12 and 3.13 (those interpreters must be available or provisioned). Its `dev` and `lint` environments run Ruff. `uv.lock` pins all dependency groups. A pre-commit hook runs `uv lock` and exports all three
requirement files before each commit, then stages the updated lock and exports. Install the hook
once with `uv run pre-commit install`.

## Gameplay modes

1. **In person:** players use a physical deck of cards. The program records bids and each player's total tricks; it does not deal cards or determine trump.
2. **Pygame pass-and-play:** the program deals cards, reveals trump, enforces follow-suit and calculates trick winners. It is a shared-device local interface, not online multiplayer.
3. **Online web:** `streamlit_app.py` supports room creation, optional player PINs, separate browser sessions, private hands, bidding, legal card play, trick calculation, a live-refreshing game mat and scores. It uses standard-library SQLite and CSV; see [ONLINE_PLAY.md](ONLINE_PLAY.md) for durable hosting.

## Rules implemented

- Bidding starts left of dealer; dealer bids last and cannot make the total bids equal the number of tricks.
- The first lead is left of dealer; subsequent tricks are led by the previous trick winner.
- Players must follow suit if possible, otherwise may play any card.
- Highest trump wins if any trump is played; otherwise highest card of the led suit wins.
- Rank order is 2–10, J, Q, K, A.
- A standard 52-card deck is shuffled each round; one remaining card is turned up as trump in Pygame mode.
- The round schedule is generated once at game creation.
- Rankings use dense ranking: ties share a rank and the next distinct score increments by one (e.g. [1, 1, 2, 3] and [1, 2, 2, 3, 4]).

## Data

`data/players.csv` stores stable player IDs and usernames. `data/game_history.csv` stores one row per player per game, including date/number, hand-size range, round count, bids, tricks, final score, dense rank and winner flag. Older CSV headers are migrated without discarding rows. These files, SQLite databases and recovery checkpoints are ignored by Git; keep usernames pseudonymous and never commit real player data.

## Documentation

See [CONTRIBUTING.md](CONTRIBUTING.md), [CHANGELOG.md](CHANGELOG.md), and [ONLINE_PLAY.md](ONLINE_PLAY.md).


## Recovery and cloud persistence

- In-person games automatically checkpoint after each completed round.
- Pygame games checkpoint after every card play and trick, so the current hand and partial trick can be restored.
- Online rooms persist each state transition in SQLite. Players reconnect with their room code, username and (if enabled) PIN.
- For Streamlit hosting, configure the optional private GitHub backup in `ONLINE_PLAY.md`. It snapshots the SQLite room database and player/history CSV files after changes. This uses Python's standard library; no Postgres or Supabase dependency is required.
