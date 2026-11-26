"""Cross-component integration and complete-game smoke tests."""
from cardgame import CSVStore, Game, Player

def test_full_manual_game_and_persistence(tmp_path):
    players = [Player("A", "a"), Player("B", "b"), Player("C", "c")]
    game = Game.create(players, 1, 2, False)
    # round 1: valid bids total 0; tricks total 1
    game.accept_round({"A": 0, "B": 0, "C": 0}, {"A": 1, "B": 0, "C": 0})
    # round 2: bids total 1 (not 2); tricks total 2
    game.accept_round({"A": 1, "B": 0, "C": 0}, {"A": 1, "B": 1, "C": 0})
    # Descending schedule returns to the starting hand size.
    game.accept_round({"A": 0, "B": 0, "C": 0}, {"A": 1, "B": 0, "C": 0})
    assert game.is_complete
    store = CSVStore(tmp_path)
    game_id, game_number = store.record_game(game, "2026-11-26")
    assert game_id and game_number == 1
    assert len(store.load_history()) == 3
    assert all(row["rounds_played"] == "3" for row in store.load_history())
    assert all(row["start_round"] == "1" and row["end_round"] == "2"
               for row in store.load_history())
