"""Domain models and card rules for Farmer's Bridge."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum


class Suit(str, Enum):
    """The four standard playing-card suits."""
    CLUBS = "Clubs"
    DIAMONDS = "Diamonds"
    HEARTS = "Hearts"
    SPADES = "Spades"


RANKS = tuple(range(2, 15))
RANK_LABELS = {11: "J", 12: "Q", 13: "K", 14: "A"}


@dataclass(frozen=True, slots=True)
class Card:
    suit: Suit
    rank: int

    def __post_init__(self) -> None:
        if not isinstance(self.suit, Suit):
            try:
                object.__setattr__(self, "suit", Suit(self.suit))
            except ValueError as exc:
                raise ValueError(f"Unknown suit: {self.suit}") from exc
        if self.rank not in RANKS:
            raise ValueError("Rank must be 2-14.")

    @property
    def label(self) -> str:
        return f"{RANK_LABELS.get(self.rank, self.rank)}{self.suit.value[0]}"

    def __str__(self) -> str:
        return f"{RANK_LABELS.get(self.rank, self.rank)} of {self.suit.value}"


@dataclass
class Player:
    name: str
    player_id: str = ""
    bids: list[int] = field(default_factory=list)
    tricks: list[int] = field(default_factory=list)
    score: int = 0

    def score_round(self, bid: int, tricks_won: int, round_number: int) -> int:
        """Apply the established scoring rule and return the points earned."""
        if bid == tricks_won:
            points = (15 if round_number >= 5 else 10) if bid == 0 else 10 + bid
        else:
            points = -abs(bid - tricks_won)
        self.score += points
        return points


def legal_cards(hand: list[Card], led_suit: Suit | None) -> list[Card]:
    """Return cards legal under the must-follow-suit rule."""
    if not hand:
        raise ValueError("Cannot play from an empty hand.")
    if led_suit is None:
        return list(hand)
    following = [card for card in hand if card.suit == led_suit]
    return following or list(hand)


def trick_winner(plays: list[tuple[int, Card]], trump_suit: Suit | None) -> int:
    """Return winning player index; ties are resolved by first card played."""
    if not plays:
        raise ValueError("A trick needs at least one card.")
    led_suit = plays[0][1].suit

    def strength(play: tuple[int, Card]) -> tuple[int, int]:
        card = play[1]
        if trump_suit is not None and card.suit == trump_suit:
            return (2, card.rank)
        if card.suit == led_suit:
            return (1, card.rank)
        return (0, card.rank)

    return max(plays, key=strength)[0]
