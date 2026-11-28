# Farmer's Bridge

A Python implementation of Farmer's Bridge with a shared game engine and three intended gameplay modes.


## To-dos for "Ready"

### First considerations fixes

Implemented in the online Streamlit interface:

- [x] "Trick complete" popup formats J/Q/K/A as letters and uses compact rank/suit notation.
- [x] Only the host can correct bids during the explicit bid-review phase. The host selects the player, makes a correction, and can repeat the review before confirming all bids.
- [x] Players click an enabled card in their hand to play it. Illegal cards are disabled; the dropdown has been removed.
- [x] Current-trick cards are shown in the same player table as bids and tricks.
- [x] Trump is displayed as a card face or compact rank/suit label.
- [x] The round/direction heading appears below the panel resize control.
- [x] Round-by-round scores show each player's bid, tricks won, points earned and cumulative score.
- [x] A card-face preference checkbox controls the hand display; narrow panels automatically use compact notation.
- [x] The game mat uses four visually separated player-table groups: Player; Cumulative score/Bid/Tricks; Current card/markers; Last-trick card/markers.
- [x] Current markers can appear together: LEAD, TURN and WILL WIN. WILL WIN identifies the current highest card in the in-progress trick, not a forecast of the game result.
- [x] The last-trick group identifies the card played, who led (LED) and who won (WON); it does not show a turn marker.
- [x] Once all bids are submitted, the game mat reports whether the round is overcalled or undercalled.
- [x] Players choose a color when creating/joining a room. Colors are unique within a room, stored with the player, and used consistently in the lobby and player table.

### Next

Implemented where compatible with the current split-screen layout:

- [x] Add the current trick's cards directly to the player table, with a "LEAD" marker and current winning-trick marker.
- [x] Keep the previous trick visible while the next trick is in progress; all completed tricks remain available in the history expander.
- [x] On detected mobile browsers, replace the side-by-side layout with a Hand / Game Mat switch, keeping round, current-turn and score summaries above it.
- [x] Add a "Card played" column and highlight the player currently winning the trick. The played card stays in that player's row until the trick resolves.
- [x] Highlight the current player independently of the leader: next bidder during bidding, next player during card play.
- [x] Keep bid correction controls above the hand/table rather than embedding them in the player rows, so they remain usable on narrow screens.

### Possible considerations (reviewed)

Both suggestions are now covered by the implementation above:

- The player table is ordered from the current leader, with a separate "LEAD" marker and independent current-player marker. This makes play order easier to follow. The trade-off is that row positions move when the leader changes; keeping a fixed seat order would be more spatially consistent but harder to follow during a trick.
- Desktop keeps the hand close to the game mat in an adjustable split view; detected mobile browsers use a Hand / Game Mat switch. This avoids narrow side-by-side panels on phones. User-agent detection can misclassify tablets or unusual browsers, so the desktop full-panel controls remain available as a fallback.

No additional behavior was added for this section because the existing fixes and "Next" items already implement both suggestions without introducing another competing layout mode.

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
