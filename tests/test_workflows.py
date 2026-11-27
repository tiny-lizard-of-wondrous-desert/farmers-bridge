from cardgame.workflows import collect_bids, collect_tricks, review_bids, review_tricks


class FakeUI:
    def __init__(self, numbers=(), answers=()):
        self.numbers, self.answers, self.messages = iter(numbers), iter(answers), []

    def number(self, message, maximum):
        return next(self.numbers)

    def yes_no(self, message):
        return next(self.answers)

    def message(self, message):
        self.messages.append(message)


def test_collect_bids_retries_invalid_dealer_total(game):
    # Dealer is Alice (index 0); order Bob, Casey, Alice. Sum first attempt=1 invalid.
    ui = FakeUI(numbers=[1, 0, 0, 0, 0, 0])
    bids = collect_bids(game, ui)
    assert sum(bids.values()) == 0


def test_collect_tricks_retries_until_sum_matches(game):
    ui = FakeUI(numbers=[0, 0, 0, 1, 0, 0])
    tricks = collect_tricks(game, ui)
    assert sum(tricks.values()) == 1


def test_review_bids_changes_only_selected_player(game):
    initial = {"Alice": 0, "Bob": 0, "Casey": 0}
    # no to all-good; yes change Bob; no for Casey and Alice; yes final confirmation
    ui = FakeUI(numbers=[1, 1], answers=[False, True, True, False, True])
    result = review_bids(game, initial, ui)
    assert result == {"Alice": 0, "Bob": 1, "Casey": 1}


def test_review_tricks_changes_one_player(game):
    initial = {"Alice": 1, "Bob": 0, "Casey": 0}
    ui = FakeUI(numbers=[1, 0], answers=[False, True, False, True, True])
    result = review_tricks(game, initial, ui)
    assert result == {"Alice": 0, "Bob": 1, "Casey": 0}
