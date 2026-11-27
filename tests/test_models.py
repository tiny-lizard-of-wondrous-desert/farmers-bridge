import pytest

from cardgame.models import Card, Player, Suit, legal_cards, trick_winner


def test_card_labels_and_suit_conversion():
    assert Card("Hearts", 14).label == "AH"
    assert Card(Suit.SPADES, 11).label == "JS"

def test_invalid_card():
    with pytest.raises(ValueError):
        Card("Stars", 2)
    with pytest.raises(ValueError):
        Card(Suit.CLUBS, 1)

def test_follow_suit_required():
    hand = [Card(Suit.HEARTS, 2), Card(Suit.SPADES, 14)]
    assert legal_cards(hand, Suit.HEARTS) == [hand[0]]

def test_any_suit_when_void():
    hand = [Card(Suit.CLUBS, 2), Card(Suit.SPADES, 14)]
    assert legal_cards(hand, Suit.HEARTS) == hand

def test_lead_all_cards_legal():
    hand = [Card(Suit.CLUBS, 2), Card(Suit.SPADES, 14)]
    assert legal_cards(hand, None) == hand

def test_empty_hand_rejected():
    with pytest.raises(ValueError):
        legal_cards([], None)

def test_trump_beats_led_suit():
    plays = [(0, Card(Suit.HEARTS, 14)), (1, Card(Suit.SPADES, 2)),
             (2, Card(Suit.HEARTS, 2))]
    assert trick_winner(plays, Suit.SPADES) == 1

def test_highest_trump_wins():
    plays = [(0, Card(Suit.SPADES, 10)), (1, Card(Suit.SPADES, 14))]
    assert trick_winner(plays, Suit.SPADES) == 1

def test_highest_led_suit_wins_without_trump():
    plays = [(0, Card(Suit.HEARTS, 10)), (1, Card(Suit.HEARTS, 14)),
             (2, Card(Suit.CLUBS, 14))]
    assert trick_winner(plays, None) == 1

def test_off_suit_does_not_win():
    plays = [(0, Card(Suit.HEARTS, 10)), (1, Card(Suit.CLUBS, 14))]
    assert trick_winner(plays, None) == 0

def test_empty_trick_rejected():
    with pytest.raises(ValueError):
        trick_winner([], None)

def test_scoring_rules():
    p = Player("Test")
    assert p.score_round(2, 2, 2) == 12
    assert p.score_round(0, 0, 4) == 10
    assert p.score_round(0, 0, 5) == 15
    assert p.score_round(3, 1, 3) == -2
    assert p.score == 35
