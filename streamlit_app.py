"""Multi-browser online play with durable SQLite state and live room refresh."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from cardgame.models import Card, Suit, legal_cards, trick_winner  # noqa: E402
from cardgame.names import clean_player_name  # noqa: E402
from cardgame.online import OnlineRoomStore  # noqa: E402
from cardgame.storage import CSVStore  # noqa: E402

st.set_page_config(page_title="Farmer's Bridge Online", layout="wide")
st.title("Farmer's Bridge — Online Play")
st.caption("Each player joins from their own browser. Only your own hand is displayed.")
st.caption("The shared game mat refreshes automatically every 3 seconds.")


def card_label(card: Card) -> str:
    """Format face-card ranks as letters for compact hand and trick display."""
    rank = {11: "J", 12: "Q", 13: "K", 14: "A"}.get(card.rank, str(card.rank))
    suit = {"Clubs": "♣", "Diamonds": "♦", "Hearts": "♥", "Spades": "♠"}.get(
        card.suit.value, card.suit.value
    )
    return f"{rank}{suit}"


def render_hand_cards(
    cards: list[Card],
    compact: bool = False,
    clickable: bool = False,
    allowed_cards: list[Card] | None = None,
    key_prefix: str = "hand",
) -> Card | None:
    """Render card buttons; use compact notation when space is limited."""
    if not cards:
        st.caption("No cards remaining.")
        return None
    allowed = set(allowed_cards or [])
    if clickable:
        st.markdown(
            """
            <style>
            div[class*="st-key-play_card"] button {
                min-height: 76px;
                border: 1px solid #9a9a9a;
                border-radius: 9px;
                background: #fff;
                color: #202020;
                font-size: 1.15rem;
                font-weight: 650;
                white-space: pre-line;
                box-shadow: 0 1px 3px #0002;
            }
            div[class*="st-key-play_card"] button:disabled { opacity: .38; }
            @media (max-width: 640px) {
                div[class*="st-key-play_card"] button {
                    min-height: 54px;
                    font-size: .95rem;
                }
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
        columns = st.columns(min(len(cards), 6 if compact else 5))
        for index, card in enumerate(cards):
            rank = {11: "J", 12: "Q", 13: "K", 14: "A"}.get(card.rank, str(card.rank))
            suit = {"Clubs": "♣", "Diamonds": "♦", "Hearts": "♥", "Spades": "♠"}[card.suit.value]
            label = f"{rank}{suit}" if compact else f"{rank}\\n{suit}"
            with columns[index % len(columns)]:
                if st.button(
                    label,
                    key=f"{key_prefix}_{index}_{card.suit.value}_{card.rank}",
                    disabled=card not in allowed,
                    use_container_width=True,
                ):
                    return card
        return None

    if compact:
        st.write("　".join(card_label(card) for card in cards))
        return None

    suit_symbols = {"Clubs": "♣", "Diamonds": "♦", "Hearts": "♥", "Spades": "♠"}
    tiles = []
    for card in cards:
        red = card.suit in (Suit.HEARTS, Suit.DIAMONDS)
        color = "#c62828" if red else "#171717"
        rank = {11: "J", 12: "Q", 13: "K", 14: "A"}.get(card.rank, str(card.rank))
        suit = suit_symbols[card.suit.value]
        tiles.append(
            f'<div style="width:66px;height:94px;flex:0 0 66px;border:1px solid #b8b8b8;'
            f'border-radius:7px;background:#fff;color:{color};padding:6px 7px;'
            f'box-sizing:border-box;box-shadow:0 1px 3px #0002;display:flex;'
            f'flex-direction:column;justify-content:space-between;font-family:Arial,sans-serif">'
            f'<div style="font-size:21px;font-weight:700;line-height:1">{rank}</div>'
            f'<div style="font-size:37px;text-align:center;line-height:1">{suit}</div>'
            f'<div style="font-size:17px;text-align:right;line-height:1">{suit}</div></div>'
        )
    st.markdown(
        '<div style="display:flex;flex-wrap:wrap;gap:7px;align-items:flex-start">'
        + "".join(tiles) + "</div>",
        unsafe_allow_html=True,
    )
    return None



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
    st.table(
        [{"Rank": ranks[score], "Player": player, "Score": score} for player, score in ordered]
    )
    st.caption(f"Dealer: {dealer}")
    if round_results:
        with st.expander("Round-by-round scores", expanded=True):
            for result in round_results:
                st.markdown(f"**Round {result['round']}**")
                st.table([
                    {
                        "Player": player,
                        "Bid": result["bids"][player],
                        "Tricks": result["tricks"][player],
                        "Round score": result["points"][player],
                        "Total score": result["scores"][player],
                    }
                    for player in scores
                ])


@st.dialog("Trick complete")
def show_trick_winner(winner: str, plays: list[dict]):
    st.success(f"{winner} won the trick!")
    st.write(" · ".join(
        f"{play['player']}: {card_label(Card(Suit(play['suit']), int(play['rank'])))}"
        for play in plays
    ))
    if st.button("Continue"):
        st.rerun()


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
            host_username = st.text_input("Your username")
            start_round = st.number_input("Starting hand size", min_value=1, max_value=13, value=1)
            end_round = st.number_input("Maximum hand size", min_value=1, max_value=13, value=7)
            double_max = st.checkbox("Play the maximum hand size twice", value=True)
            require_pins = st.checkbox("Require a private player PIN", value=True)
            create = st.form_submit_button("Create room", type="primary")
        if create:
            try:
                if not host_username.strip():
                    raise ValueError("Enter your username.")
                host_name = clean_player_name(host_username)
                if not host_name:
                    raise ValueError("Your username must contain at least one letter, number or symbol.")
                host_record = data_store.add_player(host_name)
                code, credentials = store.create_room(
                    [host_record["name"]],
                    int(start_round),
                    int(end_round),
                    double_max,
                    player_ids=[host_record["player_id"]],
                    require_pins=require_pins,
                )
                st.session_state.update(room_code=code, player_name=host_record["name"])
                if require_pins:
                    st.session_state["new_room_credentials"] = credentials
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))
    else:
        st.subheader("Join an existing lobby")
        with st.form("join_room"):
            room_input = st.text_input("Room code").strip().upper()
            name_input = clean_player_name(st.text_input("Username"))
            pin_input = st.text_input("Choose/enter your player PIN (if required)", type="password")
            connect = st.form_submit_button("Join lobby", type="primary")
        if connect:
            room = store.load(room_input)
            if room and room.get("status") == "lobby":
                existing = any(p["name"].casefold() == name_input.casefold() for p in room["players"])
                try:
                    if existing:
                        accepted = store.authenticate(room_input, name_input, pin_input)
                    else:
                        player_record = data_store.add_player(name_input)
                        accepted = store.join_lobby(
                            room_input, name_input, pin_input, player_record["player_id"]
                        )
                    if accepted:
                        st.session_state.update(room_code=room_input, player_name=name_input)
                        st.rerun()
                except ValueError as exc:
                    st.error(str(exc))
            elif store.authenticate(room_input, name_input, pin_input):
                st.session_state.update(room_code=room_input, player_name=name_input)
                st.rerun()
            else:
                st.error("Room, username or PIN is incorrect, or the lobby is full.")


def is_mobile_client() -> bool:
    """Use the browser user-agent to choose a phone-friendly single-panel layout."""
    try:
        user_agent = st.context.headers.get("User-Agent", "").lower()
    except Exception:
        return False
    return any(token in user_agent for token in ("iphone", "android", "mobile", "ipod"))


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
        st.text("Players: " + " · ".join(players))
    with head_right:
        st.metric("Status", state["status"].replace("_", " ").title())

    credentials = st.session_state.pop("new_room_credentials", None)
    if credentials:
        st.success(f"Room created: {code}")
        if state.get("players") and state["players"][0].get("pin_enabled", True):
            st.warning(
                "Your host PIN is shown only now. Each other player chooses their own PIN "
                "when joining the lobby."
            )
            for player_name, player_pin in credentials.items():
                st.code(f"{player_name}: {player_pin}")
        else:
            st.info("Player PINs are disabled. Anyone with the room code can join by username.")

    if st.button("Disconnect", key="disconnect_room"):
        for key in ("room_code", "player_name"):
            st.session_state.pop(key, None)
        st.rerun()

    if state["status"] == "lobby":
        expected = state.get("expected_players")
        joined = len(players)
        st.subheader(f"Lobby — {joined} player(s) joined")
        joined_col, waiting_col = st.columns(2)
        with joined_col:
            st.markdown("**Joined**")
            for player in players:
                st.text(f"✓ {player}")
        with waiting_col:
            st.markdown("**Waiting to join**")
            if expected is None:
                st.write("Open lobby — players can keep joining until the host starts.")
            else:
                for seat in range(expected - joined):
                    st.write(f"Waiting for player {joined + seat + 1}")
        if is_host:
            st.caption("Share the room code. Any number of players can join, subject to the 52-card deck limit. Start when at least two have joined.")
            ready = joined >= 2 and (expected is None or joined == expected)
            if st.button("Start game", type="primary", disabled=not ready):
                try:
                    store.start_game(code, name)
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))
        else:
            st.info("Waiting for the host to start once at least two players have joined.")
        return

    if state["status"] == "complete":
        st.success("Game complete!")
        ordered = sorted(state["scores"].items(), key=lambda item: item[1], reverse=True)
        unique_scores = sorted(set(state["scores"].values()), reverse=True)
        ranks = {score: index + 1 for index, score in enumerate(unique_scores)}
        st.table(
            [{"Rank": ranks[score], "Player": player, "Score": score} for player, score in ordered]
        )
        if is_host and not state.get("history_saved") and st.button("Save game to player records"):
            try:
                store.save_to_history(code, name)
                st.success("Game saved to player records.")
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))
        elif state.get("history_saved"):
            st.success(
                f"Saved as game #{state['history_game_number']} ({state['history_game_id']})."
            )
        return

    if state.get("trick_history"):
        latest_trick = state["trick_history"][-1]
        trick_signature = f"{code}:{state['round_index']}:{len(state['trick_history'])}"
        if st.session_state.get("last_trick_popup") != trick_signature:
            st.session_state["last_trick_popup"] = trick_signature
            show_trick_winner(latest_trick["winner"], latest_trick["plays"])

    round_no = state["round_sequence"][state["round_index"]]
    up_rounds = state["end_round"] - state["start_round"] + 1
    direction = "UP" if state["round_index"] < up_rounds else "DOWN"
    toolbar_left, toolbar_right = st.columns([3, 1])
    mobile_client = is_mobile_client()
    with toolbar_left:
        if mobile_client:
            mobile_view = st.radio(
                "View",
                ["Hand", "Game Mat"],
                horizontal=True,
                key="mobile_panel_mode",
                label_visibility="collapsed",
            )
            panel_mode = "Hand full panel" if mobile_view == "Hand" else "Game mat full panel"
        else:
            panel_mode = st.radio(
                "View",
                ["Split screen", "Hand full panel", "Game mat full panel"],
                horizontal=True,
                key="panel_mode",
                label_visibility="collapsed",
            )
        show_card_faces = st.checkbox(
            "Show card faces when space allows",
            value=True,
            key="show_card_faces",
        )
    with toolbar_right:
        if st.button("Current scores", use_container_width=True):
            show_scores(state["scores"], players[state["dealer_index"]], state["round_results"])

    ratio = 50
    if panel_mode == "Split screen":
        ratio = st.slider(
            "Resize panels — hand / game mat",
            min_value=25,
            max_value=75,
            value=50,
            step=5,
            help="Choose how much horizontal space each panel receives.",
            key="panel_ratio",
        )

    st.subheader(
        f"Round {state['round_index'] + 1} of {len(state['round_sequence'])} "
        f"— {round_no} card(s) per player — {direction}"
    )
    if state["status"] == "bidding":
        next_player = players[state["bid_order"][state["bid_turn"]]]
        turn_summary = f"Next bid: {next_player}"
    elif state["status"] == "playing":
        turn_summary = f"Current turn: {players[state['current_turn']]}"
    else:
        turn_summary = f"Phase: {state['status'].replace('_', ' ').title()}"
    score_summary = " · ".join(
        f"{player}: {state['scores'].get(player, 0)}" for player in players
    )
    st.caption(f"{turn_summary}  |  Scores — {score_summary}")

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
                "bidding",
                "bids_review",
                "playing",
                "round_review",
            }:
                hand_cards = sorted(
                    [Card(Suit(suit), int(rank)) for suit, rank in state["hands"][str(player_index)]],
                    key=lambda card: (list(Suit).index(card.suit), card.rank),
                )
                st.markdown("**Cards in your hand**")
                narrow_panel = panel_mode == "Split screen" and ratio < 45
                compact_hand = not show_card_faces or narrow_panel
                can_play = state["status"] == "playing" and state["current_turn"] == player_index
                if can_play:
                    led_suit = (
                        Suit(state["trick_plays"][0]["suit"]) if state["trick_plays"] else None
                    )
                    allowed = legal_cards(hand_cards, led_suit)
                    selected_card = render_hand_cards(
                        hand_cards,
                        compact=compact_hand,
                        clickable=True,
                        allowed_cards=allowed,
                        key_prefix="play_card",
                    )
                    if selected_card is not None:
                        try:
                            store.play_card(
                                code, name, selected_card.suit.value, selected_card.rank
                            )
                            st.rerun()
                        except ValueError as exc:
                            st.error(str(exc))
                else:
                    render_hand_cards(hand_cards, compact=compact_hand)
            if state["status"] == "bidding":
                bid_index = state["bid_order"][state["bid_turn"]]
                current_bidder = players[bid_index]
                if current_bidder == name:
                    bid = st.number_input(
                        "Your bid",
                        min_value=0,
                        max_value=round_no,
                        step=1,
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
                st.info("Bids are locked for review. Only the host can authorize corrections.")
                if is_host:
                    st.write("**Review all bids before card play begins.**")
                    correction_player = st.selectbox(
                        "Select a player whose bid needs correcting",
                        ["No correction"] + players,
                        key=f"bid_correction_player_{state['round_index']}",
                    )
                    if correction_player != "No correction":
                        revised_bid = st.number_input(
                            f"{correction_player}'s corrected bid",
                            min_value=0,
                            max_value=round_no,
                            value=int(state["bids"][correction_player]),
                            step=1,
                            key=f"review_bid_{state['round_index']}_{correction_player}",
                        )
                        if st.button("Save authorized bid correction"):
                            try:
                                store.correct_bid(
                                    code, name, correction_player, int(revised_bid)
                                )
                                st.rerun()
                            except ValueError as exc:
                                st.error(str(exc))
                    if st.button("All bids good — start playing", type="primary"):
                        try:
                            store.confirm_bids(code, name)
                            st.rerun()
                        except ValueError as exc:
                            st.error(str(exc))
                else:
                    st.info("Waiting for the host to confirm the bids or request a correction.")
            elif state["status"] == "playing":
                if state["current_turn"] != player_index:
                    st.info(f"Waiting for {players[state['current_turn']]} to play.")
                else:
                    st.caption("Select one of the enabled cards above to play it.")
            elif state["status"] == "round_review":
                st.info("All cards have been played. The host reviews the trick totals.")
                if is_host:
                    st.caption(
                        "Correct any player's total if needed; totals must still add up to the round size."
                    )
                    for player in players:
                        corrected = st.number_input(
                            f"{player} tricks",
                            min_value=0,
                            max_value=round_no,
                            value=int(state["tricks"][player]),
                            step=1,
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
            trump_suit, trump_rank = state["trump_card"]
            st.write("**Trump card:**")
            render_hand_cards(
                [Card(Suit(trump_suit), int(trump_rank))],
                compact=not show_card_faces,
            )
            leader_index = state["leader_index"]
            st.write(f"**Led by:** {players[leader_index]}")
            active_index = None
            if state["status"] == "bidding":
                active_index = state["bid_order"][state["bid_turn"]]
                st.write(f"**Bid turn:** {players[active_index]}")
            elif state["status"] == "playing":
                active_index = state["current_turn"]
                st.write(f"**Current turn:** {players[active_index]}")
            else:
                st.write(f"**Phase:** {state['status'].replace('_', ' ').title()}")

            current_plays = state["trick_plays"]
            completed_plays = (
                state["trick_history"][-1]["plays"]
                if state["trick_history"] and not current_plays
                else []
            )
            displayed_plays = current_plays or completed_plays
            plays_by_player = {play["player_index"]: play for play in displayed_plays}
            winning_index = None
            if current_plays:
                winning_index = trick_winner(
                    [
                        (play["player_index"], Card(Suit(play["suit"]), int(play["rank"])))
                        for play in current_plays
                    ],
                    Suit(state["trump_suit"]),
                )
            elif completed_plays:
                winning_index = next(
                    play["player_index"]
                    for play in completed_plays
                    if play["player"] == state["trick_history"][-1]["winner"]
                )

            st.markdown("### Bids called vs. tricks won")
            st.caption("Players are ordered from the current trick leader, then in play order.")
            player_order = [
                (leader_index + offset) % len(players) for offset in range(len(players))
            ]
            table_rows = []
            for index in player_order:
                player = players[index]
                played = plays_by_player.get(index)
                markers = []
                if index == leader_index:
                    markers.append("LEAD")
                if index == active_index:
                    markers.append("▶ TURN")
                if index == winning_index:
                    markers.append("★ WINNING")
                table_rows.append(
                    {
                        "Player": player,
                        "Marker": " · ".join(markers),
                        "Bid called": state["bids"].get(player, "—"),
                        "Tricks won": state["tricks"].get(player, 0),
                        "Card played": (
                            card_label(Card(Suit(played["suit"]), int(played["rank"])))
                            if played else "—"
                        ),
                        "Cumulative score": state["scores"].get(player, 0),
                    }
                )
            st.table(table_rows)

            if current_plays:
                st.caption("Previous trick remains available while this trick is in progress.")
                if len(state["trick_history"]) > 0:
                    previous = state["trick_history"][-1]
                    previous_cards = " · ".join(
                        f"{play['player']}: {card_label(Card(Suit(play['suit']), int(play['rank'])))}"
                        for play in previous["plays"]
                    )
                    st.info(f"Previous trick — {previous_cards} — {previous['winner']} won")
            elif not completed_plays:
                st.caption("No cards played in this trick yet.")

            if state["trick_history"]:
                with st.expander("All previous tricks"):
                    for number, trick in enumerate(state["trick_history"], 1):
                        cards = ", ".join(
                            f"{play['player']}: {card_label(Card(Suit(play['suit']), int(play['rank'])))}"
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
