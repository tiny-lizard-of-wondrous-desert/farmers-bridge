"""In-person interface: players handle cards and report bids/trick totals."""

from __future__ import annotations

from ..workflows import enter_round_totals


class ConsolePrompts:
    """Terminal implementation of the shared workflow prompt protocol."""

    def number(self, message: str, maximum: int) -> int:
        while True:
            raw = input(f"{message}: ").strip()
            try:
                value = int(raw)
            except ValueError:
                print("Enter a whole number.")
                continue
            if 0 <= value <= maximum:
                return value
            print(f"Enter a number from 0 to {maximum}.")

    def yes_no(self, message: str) -> bool:
        while True:
            answer = input(f"{message} [y/n]: ").strip().casefold()
            if answer in {"y", "yes"}:
                return True
            if answer in {"n", "no"}:
                return False
            print("Please enter y or n.")

    def message(self, message: str) -> None:
        print(message)


def play_manual_round(game, ui=None):
    """Play a round with physical cards and manually entered results."""
    if game.is_complete:
        return None
    ui = ui or ConsolePrompts()
    print(
        f"\nRound {len(game.results) + 1}: {game.current_round} card(s) per player "
        f"({game.round_direction})"
    )
    print("Current game table:")
    print(f"  Dealer: {game.dealer.name}")
    for player in sorted(game.players, key=lambda p: p.score, reverse=True):
        print(f"  {player.name}: {player.score}")
    bids, tricks = enter_round_totals(game, ui)
    return game.accept_round(bids, tricks)


def run_manual_game(game, ui=None, on_round_complete=None):
    """Run all rounds; a completed game is a normal return, not an exception."""
    ui = ui or ConsolePrompts()
    while not game.is_complete:
        result = play_manual_round(game, ui)
        if result is None:
            break
        if on_round_complete:
            on_round_complete(game)
        print("\nRound points:")
        for name, points in result.points.items():
            print(f"  {name}: {points:+}")
        print("Current game table:")
        next_round = game.current_round
        if next_round is None:
            print("  Game complete")
        else:
            print(f"  Next round: {next_round} cards ({game.round_direction})")
        for player in sorted(game.players, key=lambda p: p.score, reverse=True):
            print(f"  {player.name}: {player.score}")
