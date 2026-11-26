from cardgame import Game, Player, CSVStore
from cardgame.interfaces.manual import run_manual_game
import math


def choose_players(store):
    """
    Function to choose players for a game.
    It allows the user to select from previously saved players or create new ones.
    The function ensures that at least two players are selected before proceeding.

    Inputs:
    - store [dict*****: CSVStore class instance]: An instance of CSVStore to load and save player data.

    Outputs:
    - selected [list:Player class instances]: A list of Player instances representing the selected players for the game.
    """
    records = store.load_players()
    selected = []
    print("\nPlayer directory:")
    if records:
        for i, row in enumerate(records, 1):
            print(f"  {i}. {row['name']}")
    else:
        print("  No saved players yet.")

    while True:
        raw = input("Choose player number from previous players above;"
                    "NEW for new player;"
                    "or DONE if you are finished selecting players: ").strip()
        if raw.lower() in ("done", "d"):
            if len(selected) >= 2:
                return selected
            print("Choose at least two players.")
        elif raw.lower() in ("new", "n"):
            name = input("New player's name: ").strip()
            try:
                row = store.add_player(name)
            except ValueError as exc:
                print(exc)
                continue
            if any(p.player_id == row["player_id"] for p in selected):
                print("That player is already selected.")
                continue
            selected.append(Player(row["name"], row["player_id"]))
            print(f"Added {row['name']} to this game.")
        elif raw.isdigit() and 1 <= int(raw) <= len(records):
            row = records[int(raw) - 1]
            if any(p.player_id == row["player_id"] for p in selected):
                print("That player is already selected.")
                continue
            print(f"Player {row['name']} selected.")
            selected.append(Player(row["name"], row["player_id"]))
        else:
            print("Enter a listed number, N, or DONE.")


def main():
    store = CSVStore()
    players = choose_players(store)

    max_round = math.floor(51/len(players))
    print("Minimum hand size possible is 1.")
    print(f"Maximum hand size possible is {max_round}.")
    start_round = int(input("Starting hand size [default: 1]: ") or "1")
    end_round = int(input(f"Maximum hand size [default: 7]: ") or "7")
    double_max = (input("Play the maximum twice? (yes/no) [default: yes]: ").strip().lower() or "y") in {"y", "yes"}
    mode = input("Mode: M=manual scores, P=Pygame card play [default: M]: ").strip().lower() or "m"
    dealer = int(input(f"Dealer position (1-{len(players)}) [default: 1]: ") or "1") - 1

    game = Game.create(players, start_round, end_round, double_max, dealer)

    if mode == "p":
        from cardgame.interfaces.pygame_ui import PygameTable
        PygameTable(game).run()
    else:
        run_manual_game(game)

    game_id, game_number = store.record_game(game)
    winners, high_score = game.winners()
    print(f"\nSaved game #{game_number} for {game_id}.")
    print(f"Winner(s): {', '.join(winners)} with {high_score} points.")


if __name__ == "__main__":
    main()
