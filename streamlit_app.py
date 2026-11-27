"""Multi-browser online play with durable SQLite state and live room refresh."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from cardgame.models import Card, Suit, legal_cards  # noqa: E402
from cardgame.online import OnlineRoomStore  # noqa: E402
from cardgame.storage import CSVStore  # noqa: E402

st.set_page_config(page_title="Farmer's Bridge Online", layout="wide")
st.title("Farmer's Bridge — Online Play")
st.caption("Each player joins from their own browser. Only your own hand is displayed.")
st.caption("The shared game mat refreshes automatically every 3 seconds.")


# Optional private-repository backup settings are stored in Streamlit Secrets.
for secret_name, environment_name in (
    ("FARMERS_BRIDGE_BACKUP_REPO", "FARMERS_BRIDGE_BACKUP_REPO"),
    ("FARMERS_BRIDGE_BACKUP_TOKEN", "FARMERS_BRIDGE_BACKUP_TOKEN"),
    ("FARMERS_BRIDGE_BACKUP_BRANCH", "FARMERS_BRIDGE_BACKUP_BRANCH"),
):
    if secret_name in st.secrets:
        os.environ[environment_name] = str(st.secrets[secret_name])

data_store = CSVStore()
store = OnlineRoomStore()
if store.backup:
    st.success("Private GitHub backup is configured for player records and live rooms.")
else:
    st.warning(
        "No durable cloud backup is configured. On Streamlit hosting, local files may be "
        "lost after a restart. Configure the private backup settings described in ONLINE_PLAY.md."
    )


@st.dialog("Current scores")
def show_scores(scores: dict, dealer: str, round_results: list[dict]):
    ordered = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    unique_scores = sorted({score for _, score in ordered}, reverse=True)
    ranks = {score: index + 1 for index, score in enumerate(unique_scores)}
    st.table([
        {"Rank": ranks[score], "Player": player, "Score": score}
        for player, score in ordered
    ])
    st.caption(f"Dealer: {dealer}")
    if round_results:
        with st.expander("Round-by-round scores"):
            for result in round_results:
                st.write(
                    f"Round {result['round']} ({result['round']} cards): "
                    f"{result['scores']}"
                )


def render_landing_page():
    """The create/join choice is shown only before a player joins a room."""
    choice = st.radio(
        "What would you like to do?",
        ["Start a new game", "Join a lobby"],
        horizontal=True,
        key="landing_choice",
    )
    if choice == "Start a new game":
        st.subheader("Start a new game")
        with st.form("create_room"):
            names_text = st.text_area(
                "Player usernames (one per line)", "Player 1\nPlayer 2\nPlayer 3"
            )
            start_round = st.number_input(
                "Starting hand size", min_value=1, max_value=13, value=1
            )
            end_round = st.number_input(
                "Maximum hand size", min_value=1, max_value=13, value=7
            )
            double_max = st.checkbox("Play the maximum hand size twice", value=True)
            require_pins = st.checkbox("Require a private player PIN", value=True)
            create = st.form_submit_button("Create room", type="primary")
        if create:
            try:
                names = [line.strip() for line in names_text.splitlines() if line.strip()]
                if len(names) < 2:
                    raise ValueError("Enter at least two player usernames.")
                player_records = [data_store.add_player(player_name) for player_name in names]
                code, credentials = store.create_room(
                    names, int(start_round), int(end_round), double_max,
                    player_ids=[record["player_id"] for record in player_records],
                    require_pins=require_pins,
                )
                st.session_state.update(room_code=code, player_name=names[0])
                if require_pins:
                    st.session_state["new_room_credentials"] = credentials
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))
    else:
        st.subheader("Join an existing lobby")
        with st.form("join_room"):
            room_input = st.text_input("Room code").strip().upper()
            name_input = st.text_input("Username").strip()
            pin_input = st.text_input("Player PIN (if enabled)", type="password")
            connect = st.form_submit_button("Join lobby", type="primary")
        if connect:
            if store.authenticate(room_input, name_input, pin_input):
                st.session_state.update(room_code=room_input, player_name=name_input)
                st.rerun()
            else:
                st.error("Room, username or PIN is incorrect.")


def render_room(code: str, name: str):
    """Refresh the shared room state without requiring manual browser reloads."""
    state = store.load(code)
    if not state:
        st.error("This room no longer exists.")
        if st.button("Return to start/join"):
            st.session_state.pop("room_code", None)
            st.session_state.pop("player_name", None)
            st.rerun()
        return

    players = [player["name"] for player in state["players"]]
    is_host = name == players[0]
    st.divider()
    head_left, head_right = st.columns([3, 1])
    with head_left:
        st.header(f"Room {code}")
        st.write("Players: " + " · ".join(players))
    with head_right:
        st.metric("Status", state["status"].replace("_", " ").title())

    credentials = st.session_state.pop("new_room_credentials", None)
    if credentials:
        st.success(f"Room created: {code}")
        if state.get("players") and state["players"][0].get("pin_enabled", True):
            st.warning("Share each player's PIN privately. These PINs are shown only now.")
            for player_name, player_pin in credentials.items():
                st.code(f"{player_name}: {player_pin}")
        else:
            st.info("Player PINs are disabled. Anyone with the room code can join by username.")

    if st.button("Disconnect", key="disconnect_room"):
        for key in ("room_code", "player_name"):
            st.session_state.pop(key, None)
        st.rerun()

    if state["status"] == "lobby":
        st.info("Waiting in the lobby. The host can start once everyone has joined.")
        if is_host and st.button("Start game", type="primary"):
            try:
                store.start_game(code, name)
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))
        return

    if state["status"] == "complete":
        st.success("Game complete!")
        ordered = sorted(state["scores"].items(), key=lambda item: item[1], reverse=True)
        unique_scores = sorted(set(state["scores"].values()), reverse=True)
        ranks = {score: index + 1 for index, score in enumerate(unique_scores)}
        st.table([
            {"Rank": ranks[score], "Player": player, "Score": score}
            for player, score in ordered
        ])
        if is_host and not state.get("history_saved") and st.button(
            "Save game to player records"
        ):
            try:
                store.save_to_history(code, name)
                st.success("Game saved to player records.")
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))
        elif state.get("history_saved"):
            st.success(
                f"Saved as game #{state['history_game_number']} "
                f"({state['history_game_id']})."
            )
        return

    round_no = state["round_sequence"][state["round_index"]]
    up_rounds = state["end_round"] - state["start_round"] + 1
    direction = "UP" if state["round_index"] < up_rounds else "DOWN"
    st.subheader(
        f"Round {state['round_index'] + 1} of {len(state['round_sequence'])} "
        f"— {round_no} card(s) per player — {direction}"
    )

    toolbar_left, toolbar_right = st.columns([3, 1])
    with toolbar_left:
        panel_mode = st.radio(
            "View",
            ["Split screen", "Hand full panel", "Game mat full panel"],
            horizontal=True,
            key="panel_mode",
            label_visibility="collapsed",
        )
    with toolbar_right:
        if st.button("Current scores", use_container_width=True):
            show_scores(
                state["scores"], players[state["dealer_index"]], state["round_results"]
            )

    ratio = 50
    if panel_mode == "Split screen":
        ratio = st.slider(
            "Resize panels — hand / game mat",
            min_value=25, max_value=75, value=50, step=5,
            help="Choose how much horizontal space each panel receives.",
            key="panel_ratio",
        )

    player_index = players.index(name)
    hand_col, mat_col = (None, None)
    if panel_mode == "Split screen":
        hand_col, mat_col = st.columns([ratio, 100 - ratio], gap="medium")
    elif panel_mode == "Hand full panel":
        hand_col = st.container()
    else:
        mat_col = st.container()

    if hand_col is not None:
        with hand_col:
            st.markdown("## Your hand")
            if state.get("hands") and state["status"] in {
                "bidding", "bids_review", "playing", "round_review"
            }:
                hand_cards = [
                    Card(Suit(suit), int(rank))
                    for suit, rank in state["hands"][str(player_index)]
                ]
                rank_names = {11: "J", 12: "Q", 13: "K", 14: "A"}
                st.markdown("**Cards in your hand**")
                st.write(" · ".join(
                    f"{rank_names.get(card.rank, str(card.rank))} of {card.suit.value}"
                    for card in hand_cards
                ) if hand_cards else "No cards remaining.")
            if state["status"] == "bidding":
                bid_index = state["bid_order"][state["bid_turn"]]
                current_bidder = players[bid_index]
                if current_bidder == name:
                    bid = st.number_input(
                        "Your bid", min_value=0, max_value=round_no, step=1,
                        key=f"bid_{state['round_index']}_{name}",
                    )
                    if st.button("Submit bid", type="primary"):
                        try:
                            store.submit_bid(code, name, int(bid))
                            st.rerun()
                        except ValueError as exc:
                            st.error(str(exc))
                else:
                    st.info(f"Waiting for {current_bidder} to bid.")
            elif state["status"] == "bids_review":
                st.write(f"Your current bid: **{state['bids'].get(name, '—')}**")
                current_bid = state["bids"][name]
                revised_bid = st.number_input(
                    "Change your bid if needed", min_value=0,
                    max_value=round_no, value=int(current_bid), step=1,
                    key=f"review_bid_{state['round_index']}_{name}",
                )
                if st.button("Save my bid correction"):
                    try:
                        store.correct_bid(code, name, int(revised_bid))
                        st.rerun()
                    except ValueError as exc:
                        st.error(str(exc))
                if is_host and st.button("All bids good — start playing", type="primary"):
                    try:
                        store.confirm_bids(code, name)
                        st.rerun()
                    except ValueError as exc:
                        st.error(str(exc))
            elif state["status"] == "playing":
                hand = [
                    Card(Suit(suit), int(rank))
                    for suit, rank in state["hands"][str(player_index)]
                ]
                rank_names = {11: "J", 12: "Q", 13: "K", 14: "A"}
                if state["current_turn"] == player_index:
                    led = (
                        Suit(state["trick_plays"][0]["suit"])
                        if state["trick_plays"] else None
                    )
                    allowed = legal_cards(hand, led)
                    labels = {
                        f"{rank_names.get(card.rank, str(card.rank))} of {card.suit.value}": card
                        for card in allowed
                    }
                    selected = st.selectbox("Choose a legal card", list(labels))
                    if st.button("Play card", type="primary"):
                        card = labels[selected]
                        try:
                            store.play_card(code, name, card.suit.value, card.rank)
                            st.rerun()
                        except ValueError as exc:
                            st.error(str(exc))
                else:
                    st.info(f"Waiting for {players[state['current_turn']]} to play.")
            elif state["status"] == "round_review":
                st.info("All cards have been played. The host reviews the trick totals.")
                if is_host:
                    st.caption(
                        "Correct any player's total if needed; totals must still add up to the round size."
                    )
                    for player in players:
                        corrected = st.number_input(
                            f"{player} tricks", min_value=0, max_value=round_no,
                            value=int(state["tricks"][player]), step=1,
                            key=f"trick_review_{state['round_index']}_{player}",
                        )
                        if st.button(
                            f"Save {player}'s trick correction",
                            key=f"save_trick_{state['round_index']}_{player}",
                        ):
                            try:
                                store.correct_trick_count(code, name, player, int(corrected))
                                st.rerun()
                            except ValueError as exc:
                                st.error(str(exc))
                    if st.button("All trick counts good — score round", type="primary"):
                        try:
                            store.finalize_round(code, name)
                            st.rerun()
                        except ValueError as exc:
                            st.error(str(exc))
                else:
                    st.info("Waiting for the host to confirm the trick totals.")

    if mat_col is not None:
        with mat_col:
            st.markdown("## Game mat")
            st.write(f"**Round:** {round_no} cards — **{direction}**")
            st.write(f"**Trump:** {state['trump_card'][1]} of {state['trump_suit']}")
            st.write(f"**Led by:** {players[state['leader_index']]}")
            if state["status"] == "bidding":
                bid_index = state["bid_order"][state["bid_turn"]]
                st.write(f"**Bid turn:** {players[bid_index]}")
            elif state["status"] == "playing":
                st.write(f"**Current turn:** {players[state['current_turn']]}")
            else:
                st.write(f"**Phase:** {state['status'].replace('_', ' ').title()}")
            st.markdown("### Bids called vs. tricks won")
            st.table([
                {
                    "Player": player,
                    "Bid called": state["bids"].get(player, "—"),
                    "Tricks won": state["tricks"].get(player, 0),
                }
                for player in players
            ])
            st.markdown("### Current trick")
            if state["trick_plays"]:
                st.table([
                    {
                        "Player": play["player"],
                        "Card": f"{play['rank']} of {play['suit']}",
                    }
                    for play in state["trick_plays"]
                ])
            else:
                st.caption("No cards played in this trick yet.")
            if state["trick_history"]:
                with st.expander("Previous tricks"):
                    for number, trick in enumerate(state["trick_history"], 1):
                        cards = ", ".join(
                            f"{play['player']}: {play['rank']} {play['suit']}"
                            for play in trick["plays"]
                        )
                        st.write(f"Trick {number}: {cards} — **{trick['winner']} won**")


if "room_code" in st.session_state:
    @st.fragment(run_every="3s")
    def live_room(code: str, name: str):
        render_room(code, name)

    live_room(st.session_state["room_code"], st.session_state["player_name"])
else:
    render_landing_page()
