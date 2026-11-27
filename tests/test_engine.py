import random

import pytest

from cardgame import Game, Suit


def test_round_sequence_and_dealer_order(players):
    game = Game.create(players, 1, 3, True)
    assert game.round_sequence == [1, 2, 3, 3, 2, 1]
    assert game.order_left_of_dealer() == [1, 2, 0]

def test_invalid_game_setup(players):
    # Need at least 2 players
    with pytest.raises(ValueError): Game.create(players[:1])
    # Need at least 1 card per round/player
    with pytest.raises(ValueError): Game.create(players, 0, 2)
    # Need to not exceed 51 cards in a round
    with pytest.raises(ValueError): Game.create(players, 1, 30)
    # Need dealer index to be in range of players
    with pytest.raises(ValueError): Game.create(players, dealer_index=9)

def test_bids_validate_independently(game):
    game.validate_bids({"Alice": 0, "Bob": 0, "Casey": 0})
    # Total bids must not equal total cards in round
    with pytest.raises(ValueError): game.validate_bids({"Alice": 1, "Bob": 0, "Casey": 0})
    # Need all players to bid
    with pytest.raises(ValueError): game.validate_bids({"Alice": 0, "Bob": 0})

def test_tricks_validate_independently(game):
    game.validate_tricks({"Alice": 1, "Bob": 0, "Casey": 0})
    # Total tricks must equal total cards in round
    with pytest.raises(ValueError): game.validate_tricks({"Alice": 0, "Bob": 0, "Casey": 0})
    # Need all players to report tricks
    with pytest.raises(ValueError): game.validate_tricks({"Alice": 1, "Casey": 0})

def test_accept_round_updates_scores_and_dealer(game):
    result = game.accept_round({"Alice": 0, "Bob": 0, "Casey": 0},
                               {"Alice": 1, "Bob": 0, "Casey": 0}, Suit.HEARTS)
    assert result.points == {"Alice": -1, "Bob": 10, "Casey": 10}
    assert game.dealer_index == 1
    assert game.current_round == 2

def test_completed_game_is_non_erroring(players):
    game = Game.create(players, 1, 1, False)
    game.accept_round({"Alice": 0, "Bob": 0, "Casey": 0},
                      {"Alice": 1, "Bob": 0, "Casey": 0})
    assert game.is_complete
    assert game.current_round is None
    assert game.deal_round() is None
    assert game.accept_round({}, {}) is None

def test_deal_has_unique_cards(game):
    hands, trump_suit, trump_card, remaining = game.deal_round(random.Random(7))
    dealt = [card for hand in hands.values() for card in hand] + [trump_card] + remaining
    assert len(dealt) == 52
    assert len(set(dealt)) == 52
    assert all(len(hand) == 1 for hand in hands.values())
    assert trump_suit == trump_card.suit

def test_rankings_ties(players):
    game = Game.create(players, 1, 1, False)
    players[0].score, players[1].score, players[2].score = 50, 50, 20
    assert game.rankings() == {"Alice": 1, "Bob": 1, "Casey": 2}
    assert game.winners() == (["Alice", "Bob"], 50)


def test_dealer_rotation_and_property(game):
    assert game.dealer.name == "Alice"
    game.rotate_dealer()
    assert game.dealer.name == "Bob"
    assert game.order_left_of_dealer() == [2, 0, 1]


def test_round_direction_switches_from_up_to_down(players):
    game = Game.create(players, 1, 3, True)
    assert game.round_direction == "UP"
    for _ in range(3):
        round_no = game.current_round
        game.accept_round(
            {"Alice": 0, "Bob": 0, "Casey": 0},
            {"Alice": round_no, "Bob": 0, "Casey": 0},
        )
    assert game.current_round == 3
    assert game.round_direction == "DOWN"
