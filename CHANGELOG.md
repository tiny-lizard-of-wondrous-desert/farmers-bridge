# Farmer's Bridge Changelog

Notable changes to gameplay, scoring, interfaces and developer tooling.

## 0.2.0 — 2026-11-25 to 2026-11-xx

### Added
- Shared `workflows.py` for bid/trick collection, review and correction across interfaces.
- Separate `validate_bids()` and `validate_tricks()` engine validation methods.
- Normal game-completion state via `is_complete` and `current_round is None`.
- `Suit` enum, immutable slotted `Card` model and card-rule unit tests; no third-party card library was added because the available candidates are small/limited-maintenance projects.
- Three-mode setup: in-person, local Pygame pass-and-play, and a Streamlit multi-browser online-play MVP with room PINs, private hand display, bidding, trick play, corrections, scoring and CSV export.
- CSV fields for starting/ending hand size and competition-style player rank.
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
- Tied winners receive rank 1, with competition ranking for subsequent players.
- CSV schema updates no longer discard previously recorded game rows.

### Documentation
- Replaced the template contributing guide with development and architecture rules.
- Added setup, optional dependency, test, lint, formatting and tox instructions.
- Added `ONLINE_PLAY.md` with local setup, free-hosting guidance and the remaining production hardening steps.

## Pre-0.2.0
- Initial score calculations and round/dealer progression.
- Added player directory and CSV game history.
- Added manual score entry and local Pygame pass-and-play prototype.
