"""Interface-independent game state, validation, dealing and scoring."""
from __future__ import annotations
import random
from dataclasses import dataclass, field
from typing import Any
from .models import Card, Player, Suit, RANKS, legal_cards, trick_winner


@dataclass(slots=True)
class RoundResult:
    round_number: int
    bids: dict[str, int]
    tricks: dict[str, int]
    points: dict[str, int]
    scores: dict[str, int]
    trump_suit: Suit | None = None


@dataclass
class Game:
    players: list[Player]
    round_sequence: list[int]
    dealer_index: int = 0
    round_index: int = 0
    results: list[RoundResult] = field(default_factory=list)
    start_round: int = 1
    end_round: int = 7

    @classmethod
    def create(cls, players: list[Player], start_round: int = 1,
               end_round: int = 7, double_max: bool = True,
               dealer_index: int = 0) -> "Game":
        """Create a game with its complete round schedule fixed up front."""
        if len(players) < 2:
            raise ValueError("A game requires at least two players.")
        if len({p.player_id or p.name.casefold() for p in players}) != len(players):
            raise ValueError("A player cannot be selected more than once.")
        if not (1 <= start_round <= end_round):
            raise ValueError("Rounds must satisfy 1 <= start_round <= end_round.")
        if not (0 <= dealer_index < len(players)):
            raise ValueError("Invalid dealer selection.")
        max_cards = 51 // len(players)
        if end_round > max_cards:
            raise ValueError(f"With {len(players)} players, maximum hand size is {max_cards}.")
        up = list(range(start_round, end_round + 1))
        down_start = end_round if double_max else end_round - 1
        down = list(range(down_start, start_round - 1, -1))
        return cls(list(players), up + down, dealer_index,
                   start_round=start_round, end_round=end_round)

    @property
    def current_round(self) -> int | None:
        """Current hand size, or None when the game has completed normally."""
        if self.round_index >= len(self.round_sequence):
            return None
        return self.round_sequence[self.round_index]

    @property
    def is_complete(self) -> bool:
        return self.current_round is None

    @property
    def dealer(self) -> Player:
        return self.players[self.dealer_index]

    def order_left_of_dealer(self) -> list[int]:
        """Player indices in bidding and first-trick order."""
        first = (self.dealer_index + 1) % len(self.players)
        return [(first + offset) % len(self.players) for offset in range(len(self.players))]

    def rotate_dealer(self) -> None:
        self.dealer_index = (self.dealer_index + 1) % len(self.players)

    def validate_bids(self, bids: dict[str, int]) -> None:
        """Validate a complete bid set independently of trick results."""
        round_no = self.current_round
        if round_no is None:
            raise ValueError("The game is already complete; no further bids are accepted.")
        names = {p.name for p in self.players}
        if set(bids) != names:
            raise ValueError("Every player must have exactly one bid.")
        if any(type(value) is not int or not 0 <= value <= round_no for value in bids.values()):
            raise ValueError(f"Bids must be whole numbers from 0 to {round_no}.")
        if sum(bids.values()) == round_no:
            raise ValueError("The dealer's bid cannot make total bids equal the number of tricks.")

    def validate_tricks(self, tricks: dict[str, int]) -> None:
        """Validate trick counts independently of bids."""
        round_no = self.current_round
        if round_no is None:
            raise ValueError("The game is already complete; no further tricks are accepted.")
        names = {p.name for p in self.players}
        if set(tricks) != names:
            raise ValueError("Every player must have exactly one trick count.")
        if any(type(value) is not int or not 0 <= value <= round_no for value in tricks.values()):
            raise ValueError(f"Trick counts must be whole numbers from 0 to {round_no}.")
        total = sum(tricks.values())
        if total != round_no:
            raise ValueError(f"Trick counts must add up to {round_no}; got {total}.")

    def accept_round(self, bids: dict[str, int], tricks: dict[str, int],
                     trump_suit: Suit | None = None) -> RoundResult | None:
        """Validate both phases, score one round, and return None after game end."""
        if self.is_complete:
            return None
        # Kept separate so interfaces can validate immediately after each phase.
        self.validate_bids(bids)
        self.validate_tricks(tricks)
        round_no = self.current_round
        assert round_no is not None
        points: dict[str, int] = {}
        for player in self.players:
            player.bids.append(bids[player.name])
            player.tricks.append(tricks[player.name])
            points[player.name] = player.score_round(
                bids[player.name], tricks[player.name], round_no
            )
        result = RoundResult(round_no, dict(bids), dict(tricks), points,
                             {p.name: p.score for p in self.players}, trump_suit)
        self.results.append(result)
        self.round_index += 1
        self.rotate_dealer()
        return result

    def deal_round(self, rng: random.Random | Any | None = None):
        """Deal one round; return None instead of raising when game is complete."""
        round_no = self.current_round
        if round_no is None:
            return None
        rng = rng or random
        deck = [Card(suit, rank) for suit in Suit for rank in RANKS]
        rng.shuffle(deck)
        hands = {i: [] for i in range(len(self.players))}
        for _ in range(round_no):
            for player_index in self.order_left_of_dealer():
                hands[player_index].append(deck.pop())
        trump_card = deck.pop()
        return hands, trump_card.suit, trump_card, deck

    def winners(self) -> tuple[list[str], int]:
        high_score = max(player.score for player in self.players)
        return [p.name for p in self.players if p.score == high_score], high_score

    def rankings(self) -> dict[str, int]:
        """Ranking: tied first places both rank 1; next is rank 2."""
        ordered = sorted((p.score for p in self.players), reverse=True)
        ranks = {score: ordered.index(score) + 1 for score in set(ordered)}
        return {p.name: ranks[p.score] for p in self.players}
