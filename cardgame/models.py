from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

SUITS = ("Clubs", "Diamonds", "Hearts", "Spades")
RANKS = tuple(range(2, 15))
RANK_LABELS = {11: "J", 12: "Q", 13: "K", 14: "A"}


@dataclass(frozen=True)
class Card:
    suit: str
    rank: int

    def __post_init__(self):
        if self.suit not in SUITS:
            raise ValueError(f"Unknown suit: {self.suit}")
        if self.rank not in RANKS:
            raise ValueError("Rank must be 2-14.")

    @property
    def label(self) -> str:
        return f"{RANK_LABELS.get(self.rank, self.rank)}{self.suit[0]}"

    def __str__(self):
        rank = RANK_LABELS.get(self.rank, str(self.rank))
        return f"{rank} of {self.suit}"


@dataclass
class Player:
    name: str
    player_id: str = ""
    bids: list[int] = field(default_factory=list)
    tricks: list[int] = field(default_factory=list)
    score: int = 0

    def score_round(self, bid: int, tricks_won: int, round_number: int) -> int:
        if bid == tricks_won:
            points = (15 if round_number >= 5 else 10) if bid == 0 else 10 + bid
        else:
            points = -abs(bid - tricks_won)
        self.score += points
        return points


def legal_cards(hand: list[Card], led_suit: Optional[str]) -> list[Card]:
    if not hand:
        raise ValueError("Cannot play from an empty hand.")
    if led_suit is None:
        return list(hand)
    following = [card for card in hand if card.suit == led_suit]
    return following if following else list(hand)


def trick_winner(plays: list[tuple[int, Card]], trump_suit: Optional[str]) -> int:
    """
    Return player index of winner; plays are already in play order.
    """
    if not plays:
        raise ValueError("A trick needs at least one card.")
    led_suit = plays[0][1].suit

    def strength(item):
        _, card = item
        if trump_suit and card.suit == trump_suit:
            return (2, card.rank)
        if card.suit == led_suit:
            return (1, card.rank)
        return (0, card.rank)

    return max(plays, key=strength)[0]
