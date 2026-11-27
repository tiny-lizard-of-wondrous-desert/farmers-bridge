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

with st.sidebar:
    st.header("Join an existing room")
    room_input = st.text_input("Room code").strip().upper()
    name_input = st.text_input("Username")
    pin_input = st.text_input("Player PIN (if enabled)", type="password")
    if st.button("Connect", use_container_width=True):
        if store.authenticate(room_input, name_input, pin_input):
            st.session_state.update(room_code=room_input, player_name=name_input)
            st.rerun()
        st.error("Room, username or PIN is incorrect.")
    if st.session_state.get("room_code") and st.button("Disconnect", use_container_width=True):
        for key in ("room_code", "player_name"):
            st.session_state.pop(key, None)
        st.rerun()

    with st.expander("Player records across games"):
        saved_players = data_store.load_players()
        if saved_players:
            selected_record = st.selectbox(
                "Choose a saved username",
                saved_players,
                format_func=lambda row: row["name"],
            )
            stats = data_store.get_player_stats(selected_record["player_id"])
            st.metric("Games played", stats["games_played"])
            st.metric("Wins", stats["wins"])
            st.metric("Total points", stats["total_points"])
            st.metric("Average points", stats["average_points"])
        else:
            st.caption("Player records will appear after a completed game is saved.")

st.subheader("Create a new room")
with st.form("create_room"):
    names_text = st.text_area("Player usernames (one per line)", "Player 1\\nPlayer 2\\nPlayer 3")
    start_round = st.number_input("Starting hand size", min_value=1, max_value=13, value=1)
    end_round = st.number_input("Maximum hand size", min_value=1, max_value=13, value=7)
    double_max = st.checkbox("Play the maximum hand size twice", value=True)
    require_pins = st.checkbox("Require a private player PIN", value=True)
    create = st.form_submit_button("Create room")
if create:
    try:
        names = [line.strip() for line in names_text.splitlines() if line.strip()]
        player_records = [data_store.add_player(player_name) for player_name in names]
        code, credentials = store.create_room(
            names, int(start_round), int(end_round), double_max,
            player_ids=[record["player_id"] for record in player_records],
            require_pins=require_pins,
        )
        st.success(f"Room created: **{code}**")
        if require_pins:
            st.warning("Share each player's PIN privately. These PINs are shown only now.")
            for player_name, player_pin in credentials.items():
                st.code(f"{player_name}: {player_pin}")
        else:
            st.warning("PINs are disabled. Anyone with the room code can join using a player's username.")
        st.info("The host is the first player listed. Reconnect with the room code and your username after a refresh.")
    except ValueError as exc:
        st.error(str(exc))

if "room_code" in st.session_state:
    @st.fragment(run_every="3s")
    def render_room(code: str, name: str):
        """Refresh the shared room state without requiring manual browser reloads."""
        state = store.load(code)
        if not state:
            st.error("This room no longer exists.")
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

        if state["status"] == "lobby":
            st.info("Waiting for the host to start. Players can connect from separate browsers.")
            if is_host and st.button("Start game", type="primary"):
                try:
                    store.start_game(code, name)
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))
            return

        round_no = (
            state["round_sequence"][state["round_index"]]
            if state["status"] != "complete" else None
        )
        if round_no is not None:
            st.subheader(
                f"Round {state['round_index'] + 1} — {round_no} card(s) per player"
            )
            game_tab, score_tab = st.tabs(["Current game mat", "Scores & round history"])
            with game_tab:
                st.markdown("### Current game mat")
                st.write(f"**Trump:** {state['trump_card'][1]} of {state['trump_suit']}")
                st.write(f"**Current lead:** {players[state['leader_index']]}")
                st.write("**Bids**")
                st.table([
                    {"Player": player, "Bid": state["bids"].get(player, "—"),
                     "Tricks won": state["tricks"].get(player, 0)}
                    for player in players
                ])
                st.write("**Cards in the current trick**")
                if state["trick_plays"]:
                    st.table([
                        {"Player": play["player"],
                         "Card": f"{play['rank']} of {play['suit']}"}
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
                            st.write(
                                f"Trick {number}: {cards} — **{trick['winner']} won**"
                            )
            with score_tab:
                st.markdown("### Current scores")
                st.table([
                    {"Player": player, "Score": state["scores"][player]}
                    for player in players
                ])
                st.caption(f"Dealer: {players[state['dealer_index']]}")
                for result in state["round_results"]:
                    with st.expander(f"Round with {result['round']} cards"):
                        st.write({
                            "Bids": result["bids"], "Tricks": result["tricks"],
                            "Points": result["points"], "Scores": result["scores"],
                        })

            player_index = players.index(name)
            if state["status"] == "bidding":
                bid_index = state["bid_order"][state["bid_turn"]]
                current_bidder = players[bid_index]
                st.markdown("### Bidding")
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
                st.markdown("### Review bids")
                st.write("Current bids: " + " · ".join(
                    f"{player}: {state['bids'][player]}" for player in players
                ))
                current_bid = state["bids"][name]
                revised_bid = st.number_input(
                    "Your bid (change only if needed)", min_value=0,
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
                st.markdown("### Your hand")
                if state["current_turn"] == player_index:
                    hand = [
                        Card(Suit(suit), int(rank))
                        for suit, rank in state["hands"][str(player_index)]
                    ]
                    led = (
                        Suit(state["trick_plays"][0]["suit"])
                        if state["trick_plays"] else None
                    )
                    allowed = legal_cards(hand, led)
                    labels = {
                        f"{card.rank if card.rank < 11 else {11: 'J', 12: 'Q', 13: 'K', 14: 'A'}[card.rank]} of {card.suit.value}": card
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
                st.success("All tricks have been played. Review trick totals before scoring.")
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
        else:
            st.success("Game complete!")
            ordered = sorted(
                state["scores"].items(), key=lambda item: item[1], reverse=True
            )
            unique_scores = sorted(set(state["scores"].values()), reverse=True)
            ranks = {score: index + 1 for index, score in enumerate(unique_scores)}
            for player, score in ordered:
                st.write(f"**{ranks[score]}. {player}** — {score} points")
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
            if state["round_results"]:
                st.subheader("Round-by-round results")
                for result in state["round_results"]:
                    with st.expander(f"Round with {result['round']} cards"):
                        st.write({
                            "Bids": result["bids"], "Tricks": result["tricks"],
                            "Scores": result["scores"],
                        })

    render_room(st.session_state["room_code"], st.session_state["player_name"])
else:
    st.info("Create a room or connect using a room code and your username.")
