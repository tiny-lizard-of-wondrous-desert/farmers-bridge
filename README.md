# Farmer's Bridge

A Python implementation of Farmer's Bridge with a shared game engine and three intended gameplay modes.

## Project layout

- `cardgame/models.py`: `Suit` enum, `Card`, `Player`, legal plays and trick winner. The standard-library enum is used instead of a third-party card package to avoid relying on a small, lightly maintained dependency.
- `cardgame/engine.py`: round schedule, dealer rotation, bid/trick validation, dealing, scoring and rankings.
- `cardgame/workflows.py`: shared bid/trick collection and correction workflows.
- `cardgame/interfaces/manual.py`: in-person mode; players use physical cards and enter totals.
- `cardgame/interfaces/pygame_ui.py`: local pass-and-play card interface.
- `cardgame/storage.py`: player directory and game-history CSV persistence.
- `streamlit_app.py` and `cardgame/online.py`: cross-session room, private hands, bidding, card play, trick calculation and scoring using a shared SQLite room store.
- `tests/`: unit, component integration and full-game integration tests.

## Requirements and setup

Python 3.11 or newer. Install [uv](https://docs.astral.sh/uv/):

```bash
uv sync
uv pip install -r requirements-dev.txt
```

Optional interfaces (install only what you plan to use):

```bash
uv pip install -r requirements-pygame.txt  # Pygame pass-and-play
uv pip install -r requirements-web.txt     # Streamlit online play
```

The `requirements-dev.txt` file installs pytest, coverage, Ruff and tox. The base project has no runtime third-party dependencies. `requirements.txt` is the Streamlit Community Cloud dependency file for deploying the web app.

Run the in-person game:

```bash
uv run python main.py
```

Run the Pygame app by choosing mode 2 during setup. Run the Streamlit lobby separately:

```bash
uv pip install -r requirements-web.txt
uv run streamlit run streamlit_app.py
```

## Tests, lint and formatting

```bash
uv run pytest
uv run pytest --cov=cardgame --cov-report=term-missing
uv run ruff check .
uv run ruff format --check .
uv run ruff format .
uv run tox
```

`tox` runs tests across Python 3.11, 3.12 and 3.13 (those interpreters must be available or provisioned). Its `lint` environment runs Ruff. `uv.lock` pins the base project environment; optional interface and developer tools are listed in separate requirements files.

## Gameplay modes

1. **In person:** players use a physical deck of cards. The program records bids and each player's total tricks; it does not deal cards or determine trump.
2. **Pygame pass-and-play:** the program deals cards, reveals trump, enforces follow-suit and calculates trick winners. It is a shared-device local interface, not online multiplayer.
3. **Online web:** `streamlit_app.py` supports room creation, player PINs, separate browser sessions, private hands, bidding, legal card play, trick calculation, game mat and scores. It is an MVP using SQLite; see [ONLINE_PLAY.md](ONLINE_PLAY.md) for hosting and production limitations.

## Rules implemented

- Bidding starts left of dealer; dealer bids last and cannot make the total bids equal the number of tricks.
- The first lead is left of dealer; subsequent tricks are led by the previous trick winner.
- Players must follow suit if possible, otherwise may play any card.
- Highest trump wins if any trump is played; otherwise highest card of the led suit wins.
- Rank order is 2–10, J, Q, K, A.
- A standard 52-card deck is shuffled each round; one remaining card is turned up as trump in Pygame mode.
- The round schedule is generated once at game creation.
- A tied score gives all tied players a shared rank (the highest); competition ranking is not used (e.g. [1, 1, 2, 3]; [1, 2, 2, 3]; etc.).

## Data

`data/players.csv` stores historical players. `data/game_history.csv` stores one row per player per game, including game date/number, start/end hand size, round count, bids, tricks, final score, rank and winner flag. Older CSV headers are migrated by preserving existing rows and adding new columns.

## Documentation

See [CONTRIBUTING.md](CONTRIBUTING.md), [CHANGELOG.md](CHANGELOG.md), and [ONLINE_PLAY.md](ONLINE_PLAY.md).
