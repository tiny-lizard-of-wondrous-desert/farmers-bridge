from cardgame import CSVStore, Game, Player

def test_add_player_deduplicates_names(tmp_path):
    store = CSVStore(tmp_path)
    alice = store.add_player("Alice")
    assert store.add_player("alice")["player_id"] == alice["player_id"]

def test_record_game_includes_rounds_and_tied_ranks(tmp_path, players):
    store = CSVStore(tmp_path)
    game = Game.create(players, 1, 1, False)
    game.players[0].score = game.players[1].score = 20
    game.players[2].score = 5
    game.players[0].bids = [0]; game.players[1].bids = [0]; game.players[2].bids = [0]
    game.players[0].tricks = [1]; game.players[1].tricks = [0]; game.players[2].tricks = [0]
    # Add a completed result to represent the finished one-round game.
    from cardgame.engine import RoundResult
    game.results.append(RoundResult(1, {p.name: 0 for p in players},
                                    {"Alice": 1, "Bob": 0, "Casey": 0}, {}, {}))
    game.round_index = 1
    store.record_game(game, "2026-11-26")
    rows = store.load_history()
    assert {r["players_rank"] for r in rows if r["player_name"] in {"Alice", "Bob"}} == {"1"}
    assert next(r for r in rows if r["player_name"] == "Casey")["players_rank"] == "2"
    assert all(r["start_round"] == "1" and r["end_round"] == "1" for r in rows)

def test_migrate_old_history_header(tmp_path):
    path = tmp_path / "game_history.csv"
    path.write_text("game_id,date,game_number,rounds_played\ng1,2026-01-01,1,2\n", encoding="utf-8")
    store = CSVStore(tmp_path)
    row = store.load_history()[0]
    assert row["game_id"] == "g1"
    assert "players_rank" in row


def test_dense_rankings_have_no_gaps(players):
    game = Game.create(players, 1, 1, False)
    players[0].score, players[1].score, players[2].score = 100, 100, 50
    assert game.rankings() == {"Alice": 1, "Bob": 1, "Casey": 2}
    players[0].score, players[1].score, players[2].score = 100, 50, 50
    assert game.rankings() == {"Alice": 1, "Bob": 2, "Casey": 2}


def test_player_stats_persist_across_games(tmp_path):
    store = CSVStore(tmp_path)
    player = store.add_player("Ada")
    game = Game.create([Player("Ada", player["player_id"]), Player("Bea", "b")], 1, 1, False)
    game.players[0].score = 20
    game.players[1].score = 10
    from cardgame.engine import RoundResult
    game.results.append(RoundResult(
        1, {"Ada": 0, "Bea": 0}, {"Ada": 1, "Bea": 0}, {}, {}
    ))
    game.round_index = 1
    store.record_game(game, "2026-11-26")
    assert store.get_player_stats(player["player_id"]) == {
        "games_played": 1, "wins": 1, "total_points": 20, "average_points": 20.0
    }


def test_game_checkpoint_restores_round_and_active_cards(tmp_path, players):
    store = CSVStore(tmp_path)
    game = Game.create(players, 1, 2, False)
    game.players[0].score = 10
    game.active_round = {
        "hands": {"0": [["Hearts", 2]]},
        "trump_suit": "Spades",
        "trump_card": ["Spades", 14],
        "bids": {"Alice": 0},
        "tricks_won": {"Alice": 0},
        "leader": 1,
        "trick_no": 0,
        "plays": [[1, ["Clubs", 10]]],
        "next_player_offset": 1,
    }
    store.save_checkpoint(game)
    restored = store.load_checkpoint()
    assert restored is not None
    assert restored.players[0].score == 10
    assert restored.active_round == game.active_round
    store.clear_checkpoint()
    assert store.load_checkpoint() is None


def test_recording_same_game_twice_is_idempotent(tmp_path):
    store = CSVStore(tmp_path)
    players = [Player("A", "a"), Player("B", "b")]
    game = Game.create(players, 1, 1, False)
    game.accept_round({"A": 0, "B": 0}, {"A": 1, "B": 0})
    first = store.record_game(game, "2026-11-26")
    second = store.record_game(game, "2026-11-26")
    assert first == second
    assert len(store.load_history()) == 2
