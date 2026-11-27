"""Interactive entry point for all three gameplay modes."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from cardgame import CSVStore, Game, Player
from cardgame.interfaces.manual import run_manual_game

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def choose_players(store: CSVStore) -> list[Player]:
    """Select saved players or add new names for the next game."""
    records, selected = store.load_players(), []
    while True:
        print("\nSaved players:")
        for number, row in enumerate(records, 1):
            stats = store.get_player_stats(row["player_id"])
            print(
                f"  {number}. {row['name']} ({stats['games_played']} games, {stats['wins']} wins)"
            )
        raw = input("Choose number, NEW, or DONE: ").strip().casefold()
        if raw in {"done", "d"} and len(selected) >= 2:
            return selected
        if raw in {"new", "n"}:
            row = store.add_player(input("New player's username: "))
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
                [sys.executable, "-m", "streamlit", "run", str(PROJECT_ROOT / "streamlit_app.py")],
                check=False,
                cwd=PROJECT_ROOT,
            )
        except FileNotFoundError as exc:
            raise RuntimeError(
                "Install online dependencies with `uv sync --group online`."
            ) from exc
        return
    if mode not in {"1", "2"}:
        raise ValueError("Choose gameplay mode 1, 2 or 3.")

    store = CSVStore()
    game = store.load_checkpoint()
    if game is not None:
        resume = (
            input(
                f"Found an unfinished game ({len(game.results)} completed rounds). "
                "Resume it? [Y/n]: "
            )
            .strip()
            .casefold()
        )
        if resume not in {"n", "no", "f", "false"}:
            print("Resuming the saved game.")
        else:
            store.clear_checkpoint()
            game = None
    if game is not None and game.active_round is not None and mode != "2":
        print(
            "This checkpoint contains an unfinished Pygame round. Restart and choose mode 2 to resume it."
        )
        return
    if game is None:
        players = choose_players(store)
        max_round = 51 // len(players)
        start_round = int(input("Starting hand size [1]: ") or "1")
        end_round = int(input(f"Maximum hand size [{max_round}]: ") or str(max_round))
        double_max = (input("Play maximum twice? [y/n]: ").strip().casefold() or "y") not in {
            "n",
            "no",
            "f",
            "false",
        }
        dealer = int(input(f"Initial dealer position (1-{len(players)}) [1]: ") or "1") - 1
        game = Game.create(players, start_round, end_round, double_max, dealer)
        store.save_checkpoint(game)

    if mode == "2":
        try:
            from cardgame.interfaces.pygame_ui import PygameTable
        except ImportError as exc:
            print(exc)
            return
        completed = PygameTable(game, on_round_complete=store.save_checkpoint).run()
        if not completed:
            print("Game closed before completion; no completed-game record was written.")
            return
    else:
        run_manual_game(game, on_round_complete=store.save_checkpoint)

    game_id, game_number = store.record_game(game)
    store.clear_checkpoint()
    winners, high_score = game.winners()
    print(f"\nSaved game #{game_number} ({game_id}).")
    print(f"Winner(s): {', '.join(winners)} with {high_score} points.")


if __name__ == "__main__":
    main()
