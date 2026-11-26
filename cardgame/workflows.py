"""Shared bid/trick collection and correction workflows for every interface."""
from __future__ import annotations
from typing import Protocol
from .engine import Game


class Prompts(Protocol):
    def number(self, message: str, maximum: int) -> int: ...
    def yes_no(self, message: str) -> bool: ...
    def message(self, message: str) -> None: ...


def collect_bids(game: Game, ui: Prompts) -> dict[str, int]:
    """Collect bids in turn order and re-prompt until engine validation passes."""
    round_no = game.current_round
    if round_no is None:
        return {}
    while True:
        bids: dict[str, int] = {}
        for index in game.order_left_of_dealer():
            player = game.players[index]
            bids[player.name] = ui.number(f"Bid for {player.name} (0-{round_no})", round_no)
        try:
            game.validate_bids(bids)
            return bids
        except ValueError as exc:
            ui.message(str(exc))


def review_bids(game: Game, bids: dict[str, int], ui: Prompts) -> dict[str, int]:
    """Approve all bids or correct selected players until valid and approved."""
    if game.current_round is None:
        return bids
    current = dict(bids)
    while True:
        if ui.yes_no("Are all bids correct? (No = review individual bids)"):
            try:
                game.validate_bids(current)
                return current
            except ValueError as exc:
                ui.message(str(exc))
                continue
        for index in game.order_left_of_dealer():
            player = game.players[index]
            if ui.yes_no(f"Change {player.name}'s bid ({current[player.name]})?"):
                current[player.name] = ui.number(
                    f"New bid for {player.name} (0-{game.current_round})", game.current_round
                )
        try:
            game.validate_bids(current)
        except ValueError as exc:
            ui.message(str(exc))


def collect_tricks(game: Game, ui: Prompts) -> dict[str, int]:
    """Collect manual trick totals and repeat until their sum is correct."""
    round_no = game.current_round
    if round_no is None:
        return {}
    while True:
        tricks = {
            game.players[i].name: ui.number(
                f"Tricks won by {game.players[i].name} (0-{round_no})", round_no
            ) for i in game.order_left_of_dealer()
        }
        try:
            game.validate_tricks(tricks)
            return tricks
        except ValueError as exc:
            ui.message(str(exc))


def review_tricks(game: Game, tricks: dict[str, int], ui: Prompts) -> dict[str, int]:
    """Approve all trick counts or correct selected players until valid and approved."""
    if game.current_round is None:
        return tricks
    current = dict(tricks)
    while True:
        if ui.yes_no("Are all trick counts correct? (No = review individually)"):
            try:
                game.validate_tricks(current)
                return current
            except ValueError as exc:
                ui.message(str(exc))
                continue
        for index in game.order_left_of_dealer():
            player = game.players[index]
            if ui.yes_no(f"Change {player.name}'s trick count ({current[player.name]})?"):
                current[player.name] = ui.number(
                    f"New tricks for {player.name} (0-{game.current_round})", game.current_round
                )
        try:
            game.validate_tricks(current)
        except ValueError as exc:
            ui.message(str(exc))


def enter_round_totals(game: Game, ui: Prompts) -> tuple[dict[str, int], dict[str, int]]:
    """Shared workflow used by manual and Pygame modes."""
    bids = review_bids(game, collect_bids(game, ui), ui)
    tricks = review_tricks(game, collect_tricks(game, ui), ui)
    return bids, tricks
