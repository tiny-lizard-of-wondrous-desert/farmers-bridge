"""CSV persistence for player directory and completed game history."""
from __future__ import annotations
import csv
from datetime import date, datetime
from pathlib import Path
from uuid import uuid4


class CSVStore:
    PLAYER_FIELDS = ["player_id", "name", "created_at"]
    HISTORY_FIELDS = ["game_id", "date", "game_number", "start_round", "end_round",
                     "rounds_played", "player_id", "player_name", "bids", "tricks",
                     "final_score", "players_rank", "winner", "winning_score"]

    def __init__(self, data_dir="data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.players_file = self.data_dir / "players.csv"
        self.history_file = self.data_dir / "game_history.csv"
        self._ensure_schema(self.players_file, self.PLAYER_FIELDS)
        self._ensure_schema(self.history_file, self.HISTORY_FIELDS)

    @staticmethod
    def _ensure_schema(path: Path, fields: list[str]) -> None:
        """Create a CSV or migrate older headers without discarding old rows."""
        if not path.exists() or path.stat().st_size == 0:
            with path.open("w", newline="", encoding="utf-8") as stream:
                csv.DictWriter(stream, fieldnames=fields).writeheader()
            return
        with path.open(newline="", encoding="utf-8") as stream:
            reader = csv.DictReader(stream)
            old_fields = reader.fieldnames or []
            rows = list(reader)
        if old_fields == fields:
            return
        with path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            for row in rows:
                writer.writerow({field: row.get(field, "") for field in fields})

    def load_players(self) -> list[dict[str, str]]:
        """Load the persistent player directory."""
        with self.players_file.open(newline="", encoding="utf-8") as stream:
            return list(csv.DictReader(stream))

    def add_player(self, name: str) -> dict[str, str]:
        clean = name.strip()
        if not clean:
            raise ValueError("Player name cannot be blank.")
        existing = self.load_players()
        match = next((row for row in existing if row["name"].casefold() == clean.casefold()), None)
        if match:
            return match
        row = {"player_id": uuid4().hex[:12], "name": clean,
               "created_at": datetime.now().isoformat(timespec="seconds")}
        with self.players_file.open("a", newline="", encoding="utf-8") as stream:
            csv.DictWriter(stream, fieldnames=self.PLAYER_FIELDS).writerow(row)
        return row

    def load_history(self) -> list[dict[str, str]]:
        """Load the per-player rows from the game history CSV."""
        with self.history_file.open(newline="", encoding="utf-8") as stream:
            return list(csv.DictReader(stream))

    def record_game(self, game, played_on: str | None = None) -> tuple[str, int]:
        if not game.results:
            raise ValueError("Cannot save a game with no completed rounds.")
        played_on = played_on or date.today().isoformat()
        game_number = 1 + max((int(row["game_number"]) for row in self.load_history()
                               if row["date"] == played_on), default=0)
        game_id = uuid4().hex[:12]
        high_score = max(player.score for player in game.players)
        rankings = game.rankings()
        rounds_played = len(game.results)
        with self.history_file.open("a", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=self.HISTORY_FIELDS)
            for player in game.players:
                writer.writerow({
                    "game_id": game_id, "date": played_on, "game_number": game_number,
                    "start_round": game.start_round,
                    "end_round": game.end_round,
                    "rounds_played": rounds_played, "player_id": player.player_id,
                    "player_name": player.name,
                    "bids": "|".join(map(str, player.bids[-rounds_played:])),
                    "tricks": "|".join(map(str, player.tricks[-rounds_played:])),
                    "final_score": player.score, "players_rank": rankings[player.name],
                    "winner": "yes" if rankings[player.name] == 1 else "no",
                    "winning_score": high_score,
                })
        return game_id, game_number
