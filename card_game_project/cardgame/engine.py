from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional

from .models import Card, Player, SUITS, RANKS, legal_cards, trick_winner


@dataclass
class RoundResult:
    round_number: int
    bids: dict[str, int]
    tricks: dict[str, int]
    points: dict[str, int]
    scores: dict[str, int]
    trump_suit: Optional[str] = None


@dataclass
class Game:
    players: list[Player]
    round_sequence: list[int]
    dealer_index: int = 0
    round_index: int = 0
    results: list[RoundResult] = field(default_factory=list)

    @classmethod
    def create(cls, players, start_round=1, end_round=7, double_max=True, dealer_index=0):
        """
        Creates a new Game instance with the specified players and round parameters.
        Includes a list of rounds to be played, starting from start_round to end_round, and optionally doubling the maximum round.

        Inputs:
        - players [list:Player class instances]: A list of Player instances representing the players in the game.
        - start_round [int]: The starting hand size for the game (default is 1).
        - end_round [int]: The maximum hand size for the game (default is 7).
        - double_max [bool]: Whether to play the maximum hand size twice (default is True).
        - dealer_index [int]: The index of the player who will be the dealer for the first round (default is 0).

        Outputs:
        - Game instance: A new instance of the Game class initialized with the specified parameters.
        
        Raises:
        - ValueError:
            - If the number of players is less than 2; or
            - If the round parameters are invalid; or
            - If the dealer index is out of range.
        """
        if len(players) < 2:
            raise ValueError("A game requires at least two players.")
        if not (1 <= start_round <= end_round):
            raise ValueError("Rounds must satisfy 1 <= start_round <= end_round.")
        if not (0 <= dealer_index < len(players)):
            raise ValueError("Invalid dealer selection.")
        # Reserve one card to turn up as trump in every round.
        if end_round * len(players) + 1 > 52:
            raise ValueError(
                f"{len(players)} players at {end_round} cards each leaves no trump card. "
                "Reduce the maximum hand size or number of players."
            )
        up = list(range(start_round, end_round + 1))
        down_start = end_round if double_max else end_round - 1
        down = list(range(down_start, start_round - 1, -1))
        return cls(list(players), up + down, dealer_index)

    @property
    def current_round(self) -> Optional[int]:
        """
        Returns the current round number based on the round index.
        If the round index exceeds the length of the round sequence
            -> it returns None, indicating that the game is complete.
        """
        return self.round_sequence[self.round_index] if self.round_index < len(self.round_sequence) else None

    @property
    def dealer(self) -> Player:
        """
        Returns the Player instance who is currently the dealer based on the dealer index.
        """
        return self.players[self.dealer_index]

    def order_left_of_dealer(self) -> list[int]:
        """
        Returns a list of player indices in the order of play, starting from the player to the left of the dealer.
        The order is determined by the dealer index and the number of players in the game.
        Ensures that the order wraps around correctly when reaching the end of the player list.
        """
        n = len(self.players)
        first = (self.dealer_index + 1) % n
        return [(first + offset) % n for offset in range(n)]

    def rotate_dealer(self):
        """
        Rotates the dealer index to the next player in the list.
        This method updates the dealer index to point to the next player in the order of play,
        ensuring that the dealer role rotates among all players in the game.
        The dealer index wraps around to the beginning of the player list when it reaches the end.
        """
        self.dealer_index = (self.dealer_index + 1) % len(self.players)

    def accept_round(self, bids: dict[str, int], tricks: dict[str, int],
                     trump_suit: Optional[str] = None) -> RoundResult:
        """
        Accepts the bids and tricks for the current round, calculates points, and updates player scores.
        Validates the input data to ensure that each player has exactly one bid and trick count,
            and that the bids and tricks are within the valid range for the current round.
        
        Inputs:
        - bids [dict: {player_name: bid_value}]: A dictionary mapping player names to their respective bid values for the current round.
        - tricks [dict: {player_name: trick_count}]: A dictionary mapping player names to their respective trick counts for the current round.
        - trump_suit [Optional[str]]: The suit that is designated as trump for the current round (default is None).

        Outputs:
        - RoundResult: An instance of the RoundResult dataclass containing
            - the round number,
            - bids,
            - tricks,
            - points,
            - scores, and
            - trump suit
            for the current round.
       
        Raises:
        - RuntimeError: If the game is complete and there are no more rounds to play.
        - ValueError: If the bids or tricks do not meet the required conditions, such as
            - Not having exactly one bid and trick count for each player;
            - Bids or tricks being outside the valid range for the current round;
            - The total number of tricks not matching the current round number;
            - The dealer's bid making the total bids equal to the number of tricks.
        """
        round_no = self.current_round
        if round_no is None:
            raise RuntimeError("The game is complete.")
        names = [p.name for p in self.players]
        if set(bids) != set(names) or set(tricks) != set(names):
            raise ValueError("Every player must have one bid and trick count.")
        if any(type(v) is not int or not 0 <= v <= round_no for v in bids.values()):
            raise ValueError(f"Bids must be whole numbers from 0 to {round_no}.")
        if any(type(v) is not int or not 0 <= v <= round_no for v in tricks.values()):
            raise ValueError(f"Tricks must be whole numbers from 0 to {round_no}.")
        if sum(tricks.values()) != round_no:
            raise ValueError(f"Trick counts must add up to {round_no}; got {sum(tricks.values())}.")

        dealer_name = self.dealer.name
        if sum(bids.values()) == round_no:
            raise ValueError("The dealer's bid must not make total bids equal the number of tricks.")

        points = {}
        for p in self.players:
            p.bids.append(bids[p.name])
            p.tricks.append(tricks[p.name])
            points[p.name] = p.score_round(bids[p.name], tricks[p.name], round_no)

        result = RoundResult(
            round_number=round_no,
            bids=dict(bids),
            tricks=dict(tricks),
            points=points,
            scores={p.name: p.score for p in self.players},
            trump_suit=trump_suit,
        )
        self.results.append(result)
        self.round_index += 1
        self.rotate_dealer()
        return result

    def deal_round(self, rng=None):
        """
        Deal a fresh shuffled 52-card deck; return hands and turned-up trump.
        The method:
        - creates a standard 52-card deck
        - shuffles it using the provided random number generator (or the default random module),
        - deals cards to each player based on the current round number.
        - selects a trump card from the remaining deck after dealing.

        Inputs:
        - rng [Optional[random.Random]]: An optional random number generator instance for shuffling the

        Outputs:
        - hands [dict: {player_index: list[Card]}]: A dictionary mapping player indices to their respective hands of Card instances for the current round.
        - trump_suit [str]: The suit of the turned-up trump card for the current round.
        - trump_card [Card]: The turned-up trump card for the current round.
        - remaining_deck [list[Card]]: The remaining cards in the deck after dealing and selecting the trump card.
        """
        round_no = self.current_round
        if round_no is None:
            raise RuntimeError("The game is complete.")
        rng = rng or random
        deck = [Card(suit, rank) for suit in SUITS for rank in RANKS]
        rng.shuffle(deck)
        hands = {i: [] for i in range(len(self.players))}
        order = self.order_left_of_dealer()
        for _ in range(round_no):
            for player_index in order:
                hands[player_index].append(deck.pop())
        trump_card = deck.pop()
        return hands, trump_card.suit, trump_card, deck

    def winners(self):
        """
        Determine the winner(s) of the game based on the highest score.
        The method calculates the highest score among all players and returns the names of the players who achieved that score.
        If there is a tie for the highest score, all players with that score are included in the list of winners.
         
        Returns:
        - winners [list: str]: A list of player names who achieved the highest score.
        - high_score [int]: The highest score achieved by any player in the game.
        """
        high_score = max(player.score for player in self.players)
        winners = [p.name for p in self.players if p.score == high_score]
        return winners, high_score
