"""CSV persistence for player directory and completed game history."""

from __future__ import annotations

import csv
import json
import logging
from datetime import date, datetime
from pathlib import Path
from uuid import uuid4

from .backup import GitHubFileBackup


class CSVStore:
    PLAYER_FIELDS = ["player_id", "name", "created_at"]
    HISTORY_FIELDS = [
        "game_id",
        "date",
        "game_number",
        "start_round",
        "end_round",
        "rounds_played",
        "player_id",
        "player_name",
        "bids",
        "tricks",
        "final_score",
        "players_rank",
        "winner",
        "winning_score",
    ]

    def __init__(self, data_dir="data"):
        project_root = Path(__file__).resolve().parents[1]
        requested_dir = Path(data_dir)
        self.data_dir = (
            requested_dir if requested_dir.is_absolute() else project_root / requested_dir
        )
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.players_file = self.data_dir / "players.csv"
        self.history_file = self.data_dir / "game_history.csv"
        self.checkpoint_file = self.data_dir / "saves" / "active_game.json"
        self.backup = GitHubFileBackup.from_environment()
        if self.backup:
            try:
                self.backup.restore(self.players_file, "data/players.csv")
                self.backup.restore(self.history_file, "data/game_history.csv")
            except Exception:
                logging.exception("Private player/history backup restore failed")
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
        row = {
            "player_id": uuid4().hex[:12],
            "name": clean,
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        with self.players_file.open("a", newline="", encoding="utf-8") as stream:
            csv.DictWriter(stream, fieldnames=self.PLAYER_FIELDS).writerow(row)
        self._sync_backup(self.players_file, "data/players.csv", "Update player directory")
        return row

    def get_player_stats(self, player_id: str) -> dict[str, int | float]:
        """Summarize wins and results for a stable player ID across saved games."""
        rows = [row for row in self.load_history() if row.get("player_id") == player_id]
        scores = [int(row.get("final_score") or 0) for row in rows]
        return {
            "games_played": len(rows),
            "wins": sum(row.get("players_rank") == "1" for row in rows),
            "total_points": sum(scores),
            "average_points": round(sum(scores) / len(scores), 1) if scores else 0.0,
        }

    def save_checkpoint(self, game) -> Path:
        """Atomically save the latest completed-round state for local recovery."""
        self.checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.checkpoint_file.with_suffix(".tmp")
        temporary.write_text(json.dumps(game.to_dict(), indent=2), encoding="utf-8")
        temporary.replace(self.checkpoint_file)
        return self.checkpoint_file

    def load_checkpoint(self):
        """Return the most recent local game checkpoint, if one exists."""
        if not self.checkpoint_file.exists():
            return None
        from .engine import Game

        return Game.from_dict(json.loads(self.checkpoint_file.read_text(encoding="utf-8")))

    def clear_checkpoint(self) -> None:
        """Remove the completed or intentionally abandoned local checkpoint."""
        self.checkpoint_file.unlink(missing_ok=True)

    def load_history(self) -> list[dict[str, str]]:
        """Load the per-player rows from the game history CSV."""
        with self.history_file.open(newline="", encoding="utf-8") as stream:
            return list(csv.DictReader(stream))

    def record_game(self, game, played_on: str | None = None) -> tuple[str, int]:
        if not game.results:
            raise ValueError("Cannot save a game with no completed rounds.")
        history = self.load_history()
        game_id = game.game_id
        existing = next((row for row in history if row.get("game_id") == game_id), None)
        if existing:
            return game_id, int(existing["game_number"])
        played_on = played_on or date.today().isoformat()
        game_number = 1 + max(
            (int(row["game_number"]) for row in history if row["date"] == played_on), default=0
        )
        high_score = max(player.score for player in game.players)
        rankings = game.rankings()
        rounds_played = len(game.results)
        with self.history_file.open("a", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=self.HISTORY_FIELDS)
            for player in game.players:
                writer.writerow(
                    {
                        "game_id": game_id,
                        "date": played_on,
                        "game_number": game_number,
                        "start_round": game.start_round,
                        "end_round": game.end_round,
                        "rounds_played": rounds_played,
                        "player_id": player.player_id,
                        "player_name": player.name,
                        "bids": "|".join(map(str, player.bids[-rounds_played:])),
                        "tricks": "|".join(map(str, player.tricks[-rounds_played:])),
                        "final_score": player.score,
                        "players_rank": rankings[player.name],
                        "winner": "yes" if rankings[player.name] == 1 else "no",
                        "winning_score": high_score,
                    }
                )
        self._sync_backup(self.history_file, "data/game_history.csv", "Save completed game history")
        return game_id, game_number

    def _sync_backup(self, local_path: Path, remote_path: str, message: str) -> None:
        if not self.backup:
            return
        try:
            self.backup.sync(local_path, remote_path, message)
        except Exception:
            logging.exception("Private backup sync failed for %s", remote_path)
