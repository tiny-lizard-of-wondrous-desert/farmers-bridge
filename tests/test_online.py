import pytest

from cardgame.online import OnlineRoomStore


def test_online_room_full_one_trick_game(tmp_path):
    store = OnlineRoomStore(tmp_path / "rooms.sqlite3")
    code, pins = store.create_room(["Ada", "Bea"], 1, 1, False)
    assert store.authenticate(code, "Ada", pins["Ada"])
    assert store.authenticate(code, "Bea", pins["Bea"])
    assert not store.authenticate(code, "Ada", "000000")
    store.start_game(code, "Ada")
    state = store.load(code)
    assert state["status"] == "bidding"
    # Left of dealer bids first; dealer (Ada) bids last.
    store.submit_bid(code, "Bea", 0)
    store.submit_bid(code, "Ada", 0)
    assert store.load(code)["status"] == "bids_review"
    store.correct_bid(code, "Bea", 0)
    store.confirm_bids(code, "Ada")
    assert store.load(code)["status"] == "playing"
    # Play the current player's first card, then the next player's.
    for _ in range(2):
        state = store.load(code)
        index = state["current_turn"]
        player = state["players"][index]["name"]
        suit, rank = state["hands"][str(index)][0]
        store.play_card(code, player, suit, rank)
    assert store.load(code)["status"] == "round_review"
    state = store.load(code)
    winner = next(player for player, count in state["tricks"].items() if count == 1)
    store.correct_trick_count(code, "Ada", winner, 0)
    with pytest.raises(ValueError, match="Trick counts must add up"):
        store.finalize_round(code, "Ada")
    store.correct_trick_count(code, "Ada", winner, 1)
    store.finalize_round(code, "Ada")
    assert store.load(code)["status"] == "complete"
    store.save_to_history(code, "Ada", tmp_path / "history")
    rows = (
        __import__("cardgame.storage", fromlist=["CSVStore"])
        .CSVStore(tmp_path / "history")
        .load_history()
    )
    assert len(rows) == 2
    assert {row["players_rank"] for row in rows} == {"1", "2"}


def test_online_rejects_out_of_turn_bid(tmp_path):
    store = OnlineRoomStore(tmp_path / "rooms.sqlite3")
    code, _ = store.create_room(["Ada", "Bea"], 1, 1, False)
    store.start_game(code, "Ada")
    with pytest.raises(ValueError, match="not your turn"):
        store.submit_bid(code, "Ada", 0)


def test_online_bid_review_rejects_dealer_forbidden_total(tmp_path):
    store = OnlineRoomStore(tmp_path / "rooms.sqlite3")
    code, _ = store.create_room(["Ada", "Bea"], 1, 1, False)
    store.start_game(code, "Ada")
    store.submit_bid(code, "Bea", 1)
    with pytest.raises(ValueError, match="[Dd]ealer's bid"):
        store.submit_bid(code, "Ada", 0)


def test_optional_player_pins_and_stable_ids(tmp_path):
    store = OnlineRoomStore(tmp_path / "optional-pins.sqlite3")
    ids = ["saved-user-ada", "saved-user-bea"]
    code, pins = store.create_room(["Ada", "Bea"], 1, 1, False, player_ids=ids, require_pins=False)
    assert pins == {"Ada": "", "Bea": ""}
    assert store.authenticate(code, "Ada", "")
    assert not store.authenticate(code, "Ada", "123456")
    assert store.load(code)["players"][0]["player_id"] == ids[0]
