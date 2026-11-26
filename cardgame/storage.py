from __future__ import annotations

import csv
from datetime import date, datetime
from pathlib import Path
from uuid import uuid4


class CSVStore:
    """
    Small CSV persistence layer. Paths default to the project data folder.

    Player records are stored in players.csv with fields:
        player_id, name, created_at
    
    Game history records are stored in game_history.csv with fields:
        game_id, date, game_number, rounds_played,
        player_id, player_name, bids, tricks, final_score,
        winner, winning_score
    """

    PLAYER_FIELDS = ["player_id", "name", "created_at"]
    HISTORY_FIELDS = [
        "game_id", "date", "game_number", "rounds_played",
        "player_id", "player_name", "bids", "tricks", "final_score",
        "winner", "winning_score",
    ]

    def __init__(self, data_dir="data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.players_file = self.data_dir / "players.csv"
        self.history_file = self.data_dir / "game_history.csv"
        self._ensure_file(self.players_file, self.PLAYER_FIELDS)
        self._ensure_file(self.history_file, self.HISTORY_FIELDS)

    @staticmethod
    def _ensure_file(path, fields):
        if not path.exists():
            with path.open("w", newline="", encoding="utf-8") as f:
                csv.DictWriter(f, fieldnames=fields).writeheader()

    def load_players(self):
        with self.players_file.open(newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    def add_player(self, name):
        """
        Adds a new player to the players.csv file if the name is not blank and does not already exist.
        Returns the newly added player record as a dictionary.

        Inputs:
        - name [str]: The name of the player to be added.

        Outputs:
        - row [dict]: A dictionary representing the newly added player record with fields:
            - player_id: A unique identifier for the player.
            - name: The name of the player.
            - created_at: The timestamp when the player was added.

        Raises:
        - ValueError: If the name is blank or already exists in the player records.
        """
        clean = name.strip()
        if not clean:
            raise ValueError("Player name cannot be blank.")
        existing = self.load_players()
        match = next((p for p in existing if p["name"].casefold() == clean.casefold()), None)
        if match:
            raise ValueError(f"Player name already exists: {match['player_id']}.")
        row = {
            "player_id": uuid4().hex[:12],
            "name": clean,
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        with self.players_file.open("a", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=self.PLAYER_FIELDS).writerow(row)
        return row

    def record_game(self, game, played_on=None):
        """
        Records the results of a completed game in the game_history.csv file.
        Each player's bids, tricks, and final score for the game are saved along with the game metadata.

        Inputs:
        - game [Game]: An instance of the Game class representing the completed game.
        - played_on [Optional[str]]: The date the game was played in ISO format (YYYY-MM-DD). If not provided, defaults to today's date.

        Outputs:
        - game_id [str]: A unique identifier for the recorded game.
        - game_number [int]: The sequential number of the game played on the specified date.
        """
        if not game.results:
            raise ValueError("Cannot save a game with no completed rounds.")
        played_on = played_on or date.today().isoformat()
        existing = self.load_history()
        game_number = 1 + max(
            (int(row["game_number"]) for row in existing if row["date"] == played_on),
            default=0,
        )
        game_id = uuid4().hex[:12]
        top_score = max(p.score for p in game.players)
        winners = {p.name for p in game.players if p.score == top_score}
        rounds_played = len(game.results)

        for p in game.players:
            bids = [str(x) for x in p.bids[-rounds_played:]]
            tricks = [str(x) for x in p.tricks[-rounds_played:]]
            row = {
                "game_id": game_id,
                "date": played_on,
                "game_number": game_number,
                "rounds_played": rounds_played,
                "player_id": p.player_id,
                "player_name": p.name,
                "bids": "|".join(bids),
                "tricks": "|".join(tricks),
                "final_score": p.score,
                "winner": "yes" if p.name in winners else "no",
                "winning_score": top_score,
            }
            with self.history_file.open("a", newline="", encoding="utf-8") as f:
                csv.DictWriter(f, fieldnames=self.HISTORY_FIELDS).writerow(row)
        return game_id, game_number

    def load_history(self):
        """
        Loads the game history records from the game_history.csv file.
        Returns a list of dictionaries, each representing a recorded game with its associated player data.
        """
        with self.history_file.open(newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))
