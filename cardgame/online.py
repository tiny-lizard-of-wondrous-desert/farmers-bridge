"""SQLite-backed shared room state for the Streamlit online-play MVP.

SQLite is the low-dependency state store; an optional private-file backup supports cloud recovery.
"""
from __future__ import annotations
import hashlib
import json
import logging
import random
import secrets
import sqlite3
from pathlib import Path
from typing import Callable
from uuid import uuid4

from .engine import Game, RoundResult
from .models import Card, Player, RANKS, Suit, legal_cards, trick_winner
from .storage import CSVStore
from .backup import GitHubFileBackup


class OnlineRoomStore:
    def __init__(self, database: str | Path = "data/online_rooms.sqlite3"):
        """Initialize the shared room database and create its table if needed."""
        requested_database = Path(database)
        project_root = Path(__file__).resolve().parents[1]
        self.database = requested_database if requested_database.is_absolute() else project_root / requested_database
        self.database.parent.mkdir(parents=True, exist_ok=True)
        self.backup = GitHubFileBackup.from_environment()
        if self.backup:
            try:
                self.backup.restore(self.database, "data/online_rooms.sqlite3")
            except Exception:
                logging.exception("Private online room backup restore failed")
        with self._connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS rooms (code TEXT PRIMARY KEY, payload TEXT NOT NULL)")

    def _connect(self):
        """Open a SQLite connection with a busy timeout and named columns."""
        db = sqlite3.connect(self.database, timeout=15)
        db.row_factory = sqlite3.Row
        return db

    @staticmethod
    def _hash(pin: str, salt: str) -> str:
        """Hash short PINs with a per-player salt and a deliberately slow KDF."""
        return hashlib.pbkdf2_hmac(
            "sha256", pin.encode("utf-8"), salt.encode("utf-8"), 200_000
        ).hex()

    def create_room(self, names: list[str], start_round: int, end_round: int,
                    double_max: bool = True, player_ids: list[str] | None = None,
                    require_pins: bool = True) -> tuple[str, dict[str, str]]:
        """Create a lobby and return its room code plus one-time player PINs."""
        clean = [name.strip() for name in names]
        if len(clean) < 2 or any(not n for n in clean):
            raise ValueError("Enter at least two nonblank player names.")
        if len({n.casefold() for n in clean}) != len(clean):
            raise ValueError("Player names must be unique.")
        if start_round < 1 or end_round < start_round or end_round * len(clean) + 1 > 52:
            raise ValueError("Invalid round range for this number of players.")
        code = secrets.token_hex(3).upper()
        if player_ids is not None and len(player_ids) != len(clean):
            raise ValueError("A stable player ID is required for every player.")
        credentials = {
            name: f"{secrets.randbelow(1_000_000):06d}" if require_pins else ""
            for name in clean
        }
        player_rows = []
        for index, name in enumerate(clean):
            salt = secrets.token_hex(16)
            player_rows.append({
                "name": name,
                "player_id": player_ids[index] if player_ids else uuid4().hex[:12],
                "pin_enabled": require_pins,
                "pin_salt": salt,
                "pin_hash": self._hash(credentials[name], salt) if require_pins else "",
            })
        payload = {
            "players": player_rows,
            "start_round": start_round, "end_round": end_round,
            "double_max": double_max, "status": "lobby", "round_sequence": [],
            "round_index": 0, "dealer_index": 0, "scores": {name: 0 for name in clean},
            "hands": {}, "trump_suit": None, "trump_card": None,
            "bids": {}, "bid_order": [], "bid_turn": 0, "tricks": {},
            "leader_index": 0, "current_turn": 0, "trick_plays": [],
            "trick_history": [], "round_results": [],
        }
        with self._connect() as db:
            db.execute("INSERT INTO rooms(code,payload) VALUES (?,?)", (code, json.dumps(payload)))
        self._sync_backup("Create online game room")
        return code, credentials

    def load(self, code: str) -> dict | None:
        """Return a room snapshot, or None if the room code is unknown."""
        with self._connect() as db:
            row = db.execute("SELECT payload FROM rooms WHERE code=?", (code.upper(),)).fetchone()
        return json.loads(row["payload"]) if row else None

    def _mutate(self, code: str, mutation: Callable[[dict], None]) -> dict:
        """Apply a state transition inside an immediate SQLite transaction."""
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT payload FROM rooms WHERE code=?", (code.upper(),)).fetchone()
            if row is None:
                raise ValueError("Room not found.")
            state = json.loads(row["payload"])
            mutation(state)
            db.execute("UPDATE rooms SET payload=? WHERE code=?", (json.dumps(state), code.upper()))
            db.commit()
        self._sync_backup("Save online room state")
        return state

    def _sync_backup(self, message: str) -> None:
        if not self.backup:
            return
        try:
            self.backup.sync(self.database, "data/online_rooms.sqlite3", message)
        except Exception:
            logging.exception("Private online room backup sync failed")

    def authenticate(self, code: str, player_name: str, pin: str) -> bool:
        """Verify a player's PIN against the room's stored hash."""
        state = self.load(code)
        if not state:
            return False
        player = next((p for p in state["players"] if p["name"].casefold() == player_name.casefold()), None)
        if not player:
            return False
        if not player.get("pin_enabled", True):
            return not pin
        return bool(pin and secrets.compare_digest(
            player["pin_hash"], self._hash(pin, player["pin_salt"])
        ))

    @staticmethod
    def _round(state):
        return state["round_sequence"][state["round_index"]]

    def _deal(self, state):
        """Deal the current hand and initialize bidding/trick state."""
        round_no = self._round(state)
        deck = [Card(suit, rank) for suit in Suit for rank in RANKS]
        random.shuffle(deck)
        n = len(state["players"])
        first = (state["dealer_index"] + 1) % n
        order = [(first + i) % n for i in range(n)]
        hands = {str(i): [] for i in range(n)}
        for _ in range(round_no):
            for i in order:
                card = deck.pop()
                hands[str(i)].append([card.suit.value, card.rank])
        trump = deck.pop()
        state.update({"hands": hands, "trump_suit": trump.suit.value,
                      "trump_card": [trump.suit.value, trump.rank],
                      "bids": {}, "bid_order": order, "bid_turn": 0,
                      "tricks": {p["name"]: 0 for p in state["players"]},
                      "leader_index": first, "current_turn": first,
                      "trick_plays": [], "trick_history": [], "status": "bidding"})

    def start_game(self, code: str, host_name: str):
        """Start the room and deal its first round; only the host may do so."""
        def mutation(state):
            if state["players"][0]["name"] != host_name:
                raise ValueError("Only the host can start the game.")
            if state["status"] != "lobby":
                raise ValueError("Game has already started.")
            state["round_sequence"] = list(range(state["start_round"], state["end_round"] + 1))
            down_start = state["end_round"] if state["double_max"] else state["end_round"] - 1
            state["round_sequence"] += list(range(down_start, state["start_round"] - 1, -1))
            self._deal(state)
        return self._mutate(code, mutation)

    def submit_bid(self, code: str, player_name: str, bid: int):
        """Submit the current player's bid and advance the bidding turn."""
        def mutation(state):
            if state["status"] != "bidding":
                raise ValueError("Bidding is not open.")
            index = state["bid_order"][state["bid_turn"]]
            if state["players"][index]["name"] != player_name:
                raise ValueError("It is not your turn to bid.")
            round_no = self._round(state)
            if type(bid) is not int or not 0 <= bid <= round_no:
                raise ValueError(f"Bid must be between 0 and {round_no}.")
            bids = dict(state["bids"])
            bids[player_name] = bid
            if index == state["dealer_index"] and sum(bids.values()) == round_no:
                raise ValueError("Dealer's bid cannot make total bids equal tricks.")
            state["bids"] = bids
            state["bid_turn"] += 1
            if state["bid_turn"] >= len(state["bid_order"]):
                # Use the same engine validation used by the other interfaces.
                players = [Player(p["name"]) for p in state["players"]]
                game = Game(players, state["round_sequence"], state["dealer_index"], state["round_index"])
                game.validate_bids(bids)
                state["status"] = "bids_review"
        return self._mutate(code, mutation)

    def correct_bid(self, code: str, player_name: str, bid: int):
        """Update one player's bid during the bid-review phase."""
        def mutation(state):
            if state["status"] != "bids_review":
                raise ValueError("Bid corrections are only available during bid review.")
            if player_name not in state["bids"]:
                raise ValueError("Unknown player.")
            round_no = self._round(state)
            if type(bid) is not int or not 0 <= bid <= round_no:
                raise ValueError(f"Bid must be between 0 and {round_no}.")
            state["bids"][player_name] = bid
        return self._mutate(code, mutation)

    def confirm_bids(self, code: str, host_name: str):
        """Validate the reviewed bids and open card play."""
        def mutation(state):
            if state["players"][0]["name"] != host_name:
                raise ValueError("Only the host can confirm bids.")
            if state["status"] != "bids_review":
                raise ValueError("Bids are not awaiting review.")
            players = [Player(p["name"]) for p in state["players"]]
            game = Game(players, state["round_sequence"], state["dealer_index"], state["round_index"])
            game.validate_bids(state["bids"])
            state["status"] = "playing"
        return self._mutate(code, mutation)

    def play_card(self, code: str, player_name: str, suit: str, rank: int):
        """Validate and play a card, resolving the trick when all players act."""
        def mutation(state):
            if state["status"] != "playing":
                raise ValueError("Card play is not open.")
            index = state["current_turn"]
            if state["players"][index]["name"] != player_name:
                raise ValueError("It is not your turn to play.")
            card = Card(Suit(suit), int(rank))
            hand = [Card(Suit(s), int(r)) for s, r in state["hands"][str(index)]]
            led = Suit(state["trick_plays"][0]["suit"]) if state["trick_plays"] else None
            if card not in legal_cards(hand, led):
                raise ValueError("You must follow suit when you have a card of the led suit.")
            hand.remove(card)
            state["hands"][str(index)] = [[c.suit.value, c.rank] for c in hand]
            state["trick_plays"].append({"player_index": index, "player": player_name,
                                         "suit": card.suit.value, "rank": card.rank})
            n = len(state["players"])
            if len(state["trick_plays"]) == n:
                plays = [(p["player_index"], Card(Suit(p["suit"]), p["rank"]))
                         for p in state["trick_plays"]]
                winner = trick_winner(plays, Suit(state["trump_suit"]))
                winner_name = state["players"][winner]["name"]
                state["tricks"][winner_name] += 1
                state["trick_history"].append({"plays": state["trick_plays"], "winner": winner_name})
                state["trick_plays"] = []
                state["leader_index"] = winner
                if all(not cards for cards in state["hands"].values()):
                    state["status"] = "round_review"
                else:
                    state["current_turn"] = winner
            else:
                state["current_turn"] = (index + 1) % n
        return self._mutate(code, mutation)

    def correct_trick_count(self, code: str, host_name: str, player_name: str, count: int):
        """Correct one player's trick total during the host review phase."""
        def mutation(state):
            if state["players"][0]["name"] != host_name:
                raise ValueError("Only the host can correct trick totals.")
            if state["status"] != "round_review":
                raise ValueError("Trick totals are not awaiting review.")
            round_no = self._round(state)
            if player_name not in state["tricks"] or type(count) is not int or not 0 <= count <= round_no:
                raise ValueError(f"Trick count must be between 0 and {round_no}.")
            state["tricks"][player_name] = count
        return self._mutate(code, mutation)

    def finalize_round(self, code: str, host_name: str):
        """Validate reviewed totals, score the round and deal the next one."""
        def mutation(state):
            if state["players"][0]["name"] != host_name:
                raise ValueError("Only the host can finalize a round.")
            if state["status"] != "round_review":
                raise ValueError("The round is not complete yet.")
            round_no = self._round(state)
            players_for_validation = [Player(p["name"]) for p in state["players"]]
            validation_game = Game(players_for_validation, state["round_sequence"],
                                   state["dealer_index"], state["round_index"])
            validation_game.validate_bids(state["bids"])
            validation_game.validate_tricks(state["tricks"])
            players = [Player(p["name"]) for p in state["players"]]
            points = {}
            for player in players:
                player.score = state["scores"][player.name]
                points[player.name] = player.score_round(
                    state["bids"][player.name], state["tricks"][player.name], round_no
                )
                state["scores"][player.name] = player.score
            state["round_results"].append({"round": round_no, "bids": dict(state["bids"]),
                                            "tricks": dict(state["tricks"]),
                                            "points": points, "scores": dict(state["scores"])})
            state["round_index"] += 1
            state["dealer_index"] = (state["dealer_index"] + 1) % len(state["players"])
            if state["round_index"] >= len(state["round_sequence"]):
                state["status"] = "complete"
            else:
                self._deal(state)
        return self._mutate(code, mutation)

    def save_to_history(self, code: str, host_name: str, data_dir: str | Path = "data"):
        """Write a completed online game into the same CSV history as local modes."""
        def mutation(state):
            if state["players"][0]["name"] != host_name:
                raise ValueError("Only the host can save this game.")
            if state["status"] != "complete":
                raise ValueError("Only completed games can be saved.")
            if state.get("history_saved"):
                raise ValueError("This game has already been saved to history.")
            players = [Player(p["name"], p["player_id"]) for p in state["players"]]
            for player in players:
                player.score = state["scores"][player.name]
                player.bids = [result["bids"][player.name] for result in state["round_results"]]
                player.tricks = [result["tricks"][player.name] for result in state["round_results"]]
            sequence = list(state["round_sequence"])
            results = []
            for result in state["round_results"]:
                results.append(RoundResult(
                    round_number=result["round"], bids=dict(result["bids"]),
                    tricks=dict(result["tricks"]), points=dict(result["points"]),
                    scores=dict(result["scores"]),
                ))
            game = Game(
                players, sequence, state["dealer_index"], len(sequence), results,
                state["start_round"], state["end_round"],
                game_id=f"online-{code.upper()}",
            )
            game_id, game_number = CSVStore(data_dir).record_game(game)
            state["history_saved"] = True
            state["history_game_id"] = game_id
            state["history_game_number"] = game_number
        return self._mutate(code, mutation)
