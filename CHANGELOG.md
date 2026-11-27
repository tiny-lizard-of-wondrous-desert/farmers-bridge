# Farmer's Bridge Changelog

Notable changes to gameplay, scoring, interfaces and developer tooling.

## 0.2.0 — 2026-11-25 to 2026-11-xx

### Added
- Shared `workflows.py` for bid/trick collection, review and correction across interfaces.
- Separate `validate_bids()` and `validate_tricks()` engine validation methods.
- Normal game-completion state via `is_complete` and `current_round is None`.
- `Suit` enum, immutable slotted `Card` model and card-rule unit tests; Pygame card artwork is sourced from `pygame-cards`, while the engine retains its independent lightweight card model.
- Three-mode setup: in-person, local Pygame pass-and-play, and a Streamlit multi-browser online-play MVP with room PINs, private hand display, bidding, trick play, corrections, scoring and CSV export.
- CSV fields for starting/ending hand size and dense player rank.
- Automatic migration of older CSV headers while preserving existing rows.
- pytest unit/integration tests, Ruff configuration, uv project metadata and tox environments.
- Online-play scope and free-hosting architecture notes.
- CSV export from completed online games into the shared history format.

### Changed
- Bid and trick correction now asks for overall approval and then offers individual player corrections.
- Manual and Pygame interfaces use the same bid/trick workflow functions.
- Pygame shutdown is handled through a normal close signal and `finally: pygame.quit()`.
- Round schedule remains fixed at game creation; dealer rotation and scoring stay in the engine.
- Player creation now reuses an existing case-insensitive name rather than rejecting it.

### Fixed
- Game completion no longer requires catching a `RuntimeError` from `deal_round()` or `accept_round()`.
- Bids and trick totals can be checked independently immediately after their respective entry phases.
- Tied players share a rank, and the next distinct score receives the next consecutive rank.
- CSV schema updates no longer discard previously recorded game rows.

### Documentation
- Replaced the template contributing guide with development and architecture rules.
- Added setup, optional dependency, test, lint, formatting and tox instructions.
- Added `ONLINE_PLAY.md` with local setup, free-hosting guidance and the remaining production hardening steps.


## Pre-0.2.0
- Initial score calculations and round/dealer progression.
- Added player directory and CSV game history.
- Added manual score entry and local Pygame pass-and-play prototype.


## Unreleased

- Added automatic local game checkpoints, including card-by-card Pygame recovery.
- Added optional private GitHub file backups for Streamlit SQLite and CSV persistence; no Supabase/Postgres dependency is required.
- Added automatic three-second Streamlit game-mat refresh and player win/score statistics tied to stable player IDs.
- Made online player PINs optional at room creation.
- Changed rankings to dense ranking (ties do not leave rank gaps).
- Switched Pygame card artwork to the `pygame-cards` standard 52-card set.
- Grouped optional dependencies into `dev`, `local` and `online`; added a pre-commit uv lock/export hook.
- Anchored project data and test imports to the project path rather than the current working directory.

- Updated the Streamlit landing flow so create/join is the first screen and disappears after joining a room.
- Added an adjustable hand/game-mat split, full-panel views, a score dialog and a continuously visible game table with round direction, bids, tricks, leader and turn.
- Added current-round direction and score-table context to the in-person and Pygame interfaces.
- Consolidated pip requirements into one all-groups `requirements.txt`; uv dependency groups remain independently selectable and tox uses those groups.
- Reworked online lobby registration so the host enters only their own username and selects the number of seats; each other player joins with their own username, and the host sees joined players versus open seats.
- Added a trick-winner popup showing the winning player and cards played.
- Formatted face cards as J, Q, K and A; sorted online hands by suit and rank.
- Added cumulative score to the bids/tricks table while retaining the current-scores dialog.
- Added visual/layout proposals for the next table iteration to the README.
