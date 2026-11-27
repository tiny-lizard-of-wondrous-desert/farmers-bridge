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



def test_lobby_players_join_with_own_usernames_and_host_waits(tmp_path):
    store = OnlineRoomStore(tmp_path / "joining.sqlite3")
    code, _ = store.create_room(
        ["Host"], 1, 1, False, require_pins=False, expected_players=3
    )
    assert store.load(code)["expected_players"] == 3
    with pytest.raises(ValueError, match="Waiting for all player seats"):
        store.start_game(code, "Host")
    assert store.join_lobby(code, "Player Two")
    assert store.join_lobby(code, "Player Three")
    state = store.load(code)
    assert [player["name"] for player in state["players"]] == [
        "Host", "Player Two", "Player Three"
    ]
    assert all(player["joined"] for player in state["players"])
    store.start_game(code, "Host")
    assert store.load(code)["status"] == "bidding"


def test_lobby_rejects_duplicate_or_excess_players(tmp_path):
    store = OnlineRoomStore(tmp_path / "joining-limits.sqlite3")
    code, _ = store.create_room(
        ["Host"], 1, 1, False, require_pins=False, expected_players=2
    )
    with pytest.raises(ValueError, match="already in this lobby"):
        store.join_lobby(code, "host")
    store.join_lobby(code, "Guest")
    with pytest.raises(ValueError, match="lobby is full"):
        store.join_lobby(code, "Late")



def test_lobby_joiner_sets_private_pin(tmp_path):
    store = OnlineRoomStore(tmp_path / "joining-pins.sqlite3")
    code, host_credentials = store.create_room(
        ["Host"], 1, 1, False, require_pins=True, expected_players=2
    )
    assert store.authenticate(code, "Host", host_credentials["Host"])
    with pytest.raises(ValueError, match="choose a PIN"):
        store.join_lobby(code, "Guest")
    store.join_lobby(code, "Guest", "246810", "stable-guest-id")
    assert store.authenticate(code, "Guest", "246810")
    assert not store.authenticate(code, "Guest", "000000")
    assert store.load(code)["players"][1]["player_id"] == "stable-guest-id"


def test_open_lobby_allows_any_number_of_players_until_host_starts(tmp_path):
    store = OnlineRoomStore(tmp_path / "open-lobby.sqlite3")
    code, _ = store.create_room(["Host"], 1, 2, False, require_pins=False)
    assert store.load(code)["expected_players"] is None
    with pytest.raises(ValueError, match="At least two"):
        store.start_game(code, "Host")
    for name in ("Guest 1", "Guest 2", "Guest 3"):
        assert store.join_lobby(code, name)
    assert len(store.load(code)["players"]) == 4
    store.start_game(code, "Host")
    assert store.load(code)["status"] == "bidding"


def test_open_lobby_respects_physical_deck_capacity(tmp_path):
    store = OnlineRoomStore(tmp_path / "deck-capacity.sqlite3")
    code, _ = store.create_room(["Host"], 1, 13, False, require_pins=False)
    store.join_lobby(code, "Guest 1")
    store.join_lobby(code, "Guest 2")
    with pytest.raises(ValueError, match="Too many players"):
        store.join_lobby(code, "Guest 3")


def test_usernames_keep_letters_numbers_and_common_symbols(tmp_path):
    from cardgame.names import clean_player_name
    from cardgame.storage import CSVStore

    assert clean_player_name("  Alex<script> :) <3 !!!  ") == "Alexscript :) <3 !!!"
    store = CSVStore(tmp_path / "players")
    record = store.add_player("  Alex<script> :) <3 !!!  ")
    assert record["name"] == "Alexscript :) <3 !!!"
    assert store.add_player("Alex<script> :) <3 !!!")["player_id"] == record["player_id"]
