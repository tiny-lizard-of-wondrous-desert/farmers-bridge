from __future__ import annotations


def ask_int(prompt, low, high):
    while True:
        raw = input(prompt).strip()
        try:
            value = int(raw)
        except ValueError:
            print("Enter a whole number.")
            continue
        if low <= value <= high:
            return value
        print(f"Enter a number from {low} to {high}.")


def collect_bids(game):
    round_no = game.current_round
    bids = {}
    total = 0
    for index in game.order_left_of_dealer():
        player = game.players[index]
        is_dealer = index == game.dealer_index
        while True:
            if is_dealer:
                forbidden = round_no - total
                if 0 <= forbidden <= round_no:
                    print(f"Dealer cannot bid {forbidden}.")
            bid = ask_int(f"Bid for {player.name}: ", 0, round_no)
            if not (is_dealer and total + bid == round_no):
                break
            print("That would make the total bids equal the number of tricks.")
        bids[player.name] = bid
        total += bid
    print(f"Total bids: {total}; tricks available: {round_no}.")
    return bids


def collect_tricks(game):
    round_no = game.current_round
    while True:
        tricks = {}
        for index in game.order_left_of_dealer():
            player = game.players[index]
            tricks[player.name] = ask_int(
                f"Tricks won by {player.name}: ", 0, round_no
            )
        total = sum(tricks.values())
        if total == round_no:
            return tricks
        print(f"Those entries total {total}; they must total {round_no}. Please re-enter tricks.")


def correct_bids(game, bids):
    if input("Correct bids? (y/n): ").strip().lower() not in {"y", "yes"}:
        return bids

    while True:
        corrected = {}
        for index in game.order_left_of_dealer():
            player = game.players[index]
            corrected[player.name] = ask_int(
                f"Correct bid for {player.name}: ", 0, game.current_round
            )
        if sum(corrected.values()) != game.current_round:
            return corrected
        print("Correction rejected: total bids cannot equal the number of tricks.")
        if input("Try correcting bids again? (y/n): ").strip().lower() not in {"y", "yes"}:
            return bids


def correct_tricks(game, tricks):
    if input("Correct trick counts? (y/n): ").strip().lower() not in {"y", "yes"}:
        return tricks

    while True:
        corrected = {}
        for index in game.order_left_of_dealer():
            player = game.players[index]
            corrected[player.name] = ask_int(
                f"Correct tricks for {player.name}: ", 0, game.current_round
            )
        if sum(corrected.values()) == game.current_round:
            return corrected
        print(f"Correction rejected: trick counts must total {game.current_round}.")
        if input("Try correcting tricks again? (y/n): ").strip().lower() not in {"y", "yes"}:
            return tricks


def play_manual_round(game):
    print(f"\nRound {len(game.results) + 1}: {game.current_round} card(s) per player")
    bids = collect_bids(game)
    bids = correct_bids(game, bids)
    tricks = collect_tricks(game)
    tricks = correct_tricks(game, tricks)
    return game.accept_round(bids, tricks)


def run_manual_game(game):
    while game.current_round is not None:
        result = play_manual_round(game)
        print("\nRound points:")
        for name, points in result.points.items():
            print(f"  {name}: {points:+}")
        print("Current scores:")
        for player in sorted(game.players, key=lambda p: p.score, reverse=True):
            print(f"  {player.name}: {player.score}")
