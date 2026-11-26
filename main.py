"""Interactive entry point for all three gameplay modes."""
from __future__ import annotations
import subprocess
import sys
from cardgame import CSVStore, Game, Player
from cardgame.interfaces.manual import run_manual_game


def choose_players(store: CSVStore) -> list[Player]:
    """Select saved players or add new names for the next game."""
    records, selected = store.load_players(), []
    while True:
        print("\nSaved players:")
        for number, row in enumerate(records, 1):
            print(f"  {number}. {row['name']}")
        raw = input("Choose number, NEW, or DONE: ").strip().casefold()
        if raw in {"done", "d"} and len(selected) >= 2:
            return selected
        if raw in {"new", "n"}:
            row = store.add_player(input("New player's name: "))
            if any(p.player_id == row["player_id"] for p in selected):
                print("Already selected.")
            else:
                selected.append(Player(row["name"], row["player_id"]))
        elif raw.isdigit() and 1 <= int(raw) <= len(records):
            row = records[int(raw) - 1]
            if any(p.player_id == row["player_id"] for p in selected):
                print("Already selected.")
            else:
                selected.append(Player(row["name"], row["player_id"]))
        else:
            print("Select at least two distinct players; enter a valid number, NEW or DONE.")


def main() -> None:
    """Select the mode, run a game, and persist completed local games."""
    print("\nGameplay mode: 1) In person  2) Pygame pass-and-play  3) Online web")
    mode = input("Choose 1, 2 or 3 [1]: ").strip() or "1"
    if mode == "3":
        try:
            subprocess.run(
                [sys.executable, "-m", "streamlit", "run", "streamlit_app.py"],
                check=False,
            )
        except FileNotFoundError as exc:
            raise RuntimeError(
                "Install online dependencies with `uv pip install -r requirements-web.txt`."
            ) from exc
        return
    if mode not in {"1", "2"}:
        raise ValueError("Choose gameplay mode 1, 2 or 3.")

    store = CSVStore()
    players = choose_players(store)
    max_round = 51 // len(players)
    start_round = int(input("Starting hand size [1]: ") or "1")
    end_round = int(input(f"Maximum hand size [{max_round}]: ") or str(max_round))
    double_max = (input("Play maximum twice? [y/n]: ").strip().casefold() or "y") not in {"n", "no", "f", "false"}
    dealer = int(input(f"Initial dealer position (1-{len(players)}) [1]: ") or "1") - 1
    game = Game.create(players, start_round, end_round, double_max, dealer)

    if mode == "2":
        try:
            from cardgame.interfaces.pygame_ui import PygameTable
        except ImportError as exc:
            print(exc)
            return
        completed = PygameTable(game).run()
        if not completed:
            print("Game closed before completion; no completed-game record was written.")
            return
    else:
        run_manual_game(game)

    game_id, game_number = store.record_game(game)
    winners, high_score = game.winners()
    print(f"\nSaved game #{game_number} ({game_id}).")
    print(f"Winner(s): {', '.join(winners)} with {high_score} points.")


if __name__ == "__main__":
    main()
