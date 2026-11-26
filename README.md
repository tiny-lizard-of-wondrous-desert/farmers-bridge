# Trick-taking card game project

This project separates the **game engine**, **manual interface**, **Pygame interface**, and **CSV persistence**.

## Files

- `cardgame/models.py` — Card and Player models; follow-suit and trick-winner rules.
- `cardgame/engine.py` — round schedule, dealer rotation, validation, scoring, and dealing.
- `cardgame/interfaces/manual.py` — Jupyter/terminal score-entry workflow.
- `cardgame/interfaces/pygame_ui.py` — optional local pass-and-play card interface.
- `cardgame/storage.py` — historical player directory and game history CSVs.
- `main.py` — setup and mode selection.

## Run

From this folder:

```bash
python main.py
```

For Pygame mode, install the optional dependency:

```bash
python -m pip install pygame
```

Then choose `P` at game setup. Manual mode requires only Python's standard library and works in a Jupyter notebook/terminal.

## CSV records

The program creates a `data/` folder:

- `players.csv`: persistent player directory. Choose existing players or add new names.
- `game_history.csv`: one row per player per completed game, including date, game number for that date, participants, round bids/tricks, final score, and winner status.

Do not delete or rename the CSV headers if you want the program to keep reading the files.

## Rules currently implemented

- Bids and the first lead begin immediately left of the dealer.
- The dealer bids last and cannot make total bids equal the number of tricks in the round.
- Players must follow the led suit if they have it.
- If void in the led suit, a player may play any card.
- Highest led-suit card wins unless one or more trump cards are played; highest trump wins.
- Ranks: 2–10, J, Q, K, A.
- A fresh standard 52-card deck is shuffled for each round; one remaining card is turned up to establish trump.
- Correct nonzero bid scores 10 + bid; correct zero bid scores 10 points before round 5 and 15 from round 5 onward; incorrect bid loses the absolute difference.
- Trick totals in manual mode must equal the number of tricks in the round.

## Important scope notes

- The Pygame interface is **local pass-and-play**, not online multiplayer. It hides the hand between players by showing a handoff screen. Players should physically turn away while another player enters a bid or plays a card.
- The current Pygame screen uses text card faces rather than card artwork. The game engine is independent of Pygame, so graphics or a networked interface can be added later.
- In Pygame mode, cards are dealt and tricks are calculated automatically. Bids and trick-count corrections are separate prompts before the round is scored.
- The initial dealer is selected by position in the chosen player list; after each round the dealer rotates to the next player.
