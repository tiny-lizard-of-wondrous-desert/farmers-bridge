# Farmer's Bridge

A Python implementation of Farmer's Bridge with a shared game engine and three intended gameplay modes.


## To-dos for "Ready"

First considerations

- [x] Make "lobby" mode show who's joined so far vs who's still coming.
- [x] Make player names entered by each player when they join, rather than having the host create every player's identity. The host enters their own username and chooses the number of seats.
- [x] At the end of a trick, show a popup announcing who won and the cards played.
- [x] Display ranks 11–13 as J, Q, K (and 14 as A) rather than numbers.
- [x] Sort "your hand" by suit, then rank.
- [x] Add cumulative score to the bids/tricks table; keep "Current scores" for the round-by-round score view.

## Next

Recommended implementation order:

1. Add the current trick's cards directly to the player table, with a small "led" marker beside the player who led.
2. Keep the current trick visible until the next trick begins; preserve the previous-trick history as a collapsible section.
3. Use the same compact card notation in the hand, table and trick history (`7♠`, `J♥`, etc.) so players can scan the table quickly.
4. On mobile, replace the side-by-side layout with a Hand / Game Mat tab or segmented switch, keeping the current-turn and score summary visible above it.

This keeps the table as the primary shared view without duplicating card information in multiple places.

## Possible considerations (design options; not yet implemented)

- Reorder the player table from the player who leads to the last player in the current bidding/play order. The first row should carry a small "LEAD" label; the current player should be highlighted independently.
- Add a "Card played" column and highlight the player currently winning the trick. Keep the played card in that player's row until the trick resolves.
- Highlight the current player's row according to the active phase: next bidder during bidding, next player during card play.
- Keep the hand visually close to the game mat on desktop; on mobile, use a dedicated hand/game-mat switch rather than forcing two narrow columns.
- Put the bid selector in the player's table row only if it remains usable on narrow screens. Otherwise keep the bid control above the hand/table.
- Card presentation options to compare:
  - **Card face:** use the `pygame-cards` artwork style (white card, rounded border, corner rank/suit, large central suit pip).
  - **Compact notation:** use a text card such as `7♠` for every card, with suit-aware color and consistent sizing. This is lighter, faster and more mobile-friendly.

These are proposals only; choose a layout before implementing them.

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
Optional dependencies are grouped in `pyproject.toml`: `local`, `online` and `dev`.
`requirements.txt` is the single generated export containing every group for tools
that require a pip requirements file. For normal development, select only the
needed groups with `uv sync --group ...`; do not install the combined export unless
you want every optional dependency.

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
uv run --group dev pytest
uv run --group dev pytest --cov=cardgame --cov-report=term-missing
uv run --group dev ruff check .
uv run --group dev ruff format --check .
uv run --group dev ruff format .
uv run --group dev tox
uv run --group dev pre-commit install
```

`tox` delegates dependency selection to uv: `dev` runs tests and Ruff, `local`
tests the Pygame dependency group, and `online` tests the Streamlit group.
`uv.lock` pins all dependency groups. A pre-commit hook runs `uv lock` and exports
all groups into the single `requirements.txt` before each commit, then stages the
updated lock and export. Install the hook once with `uv run --group dev pre-commit install`.

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

### Online lobby usernames and player count

The host can start an open lobby once at least two players have joined; there is no fixed seat count. Additional players may join until the host starts the game. The standard 52-card deck still limits the number of players for a selected maximum hand size. Usernames are normalized to letters, numbers, spaces, and common punctuation/emoticon symbols (for example `:)` and `<3`) before being saved. In the Streamlit hand panel, card faces are shown when the panel has enough width; compact rank/suit notation is used in narrow split-screen layouts.
