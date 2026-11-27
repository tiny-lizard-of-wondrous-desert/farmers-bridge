import sys
from pathlib import Path

import pytest

# Resolve imports from the project root, regardless of the shell's working directory.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from cardgame import Game, Player


@pytest.fixture
def players():
    return [Player("Alice", "a"), Player("Bob", "b"), Player("Casey", "c")]


@pytest.fixture
def game(players):
    return Game.create(players, start_round=1, end_round=2, double_max=False)
