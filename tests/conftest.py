import pytest
from cardgame import Game, Player

@pytest.fixture
def players():
    return [Player("Alice", "a"), Player("Bob", "b"), Player("Casey", "c")]

@pytest.fixture
def game(players):
    return Game.create(players, start_round=1, end_round=2, double_max=False)
