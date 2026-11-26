"""Optional local pass-and-play Pygame interface.

Install with: python -m pip install pygame
This is a shared-screen local interface, not online networking.
"""
from __future__ import annotations

try:
    import pygame
except ImportError as exc:
    raise SystemExit("Pygame is optional. Install it with: python -m pip install pygame") from exc

from ..models import legal_cards, trick_winner


WIDTH, HEIGHT = 1100, 760
BG = (24, 92, 67)
WHITE = (245, 245, 235)
DARK = (25, 30, 32)
GOLD = (232, 190, 90)
RED = (180, 55, 55)
BLACK = (20, 20, 20)


class PygameTable:
    def __init__(self, game):
        pygame.init()
        pygame.display.set_caption("Farmer's Bridge Card Game")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("arial", 28)
        self.small = pygame.font.SysFont("arial", 20)
        self.game = game

    def text(self, message, x, y, font=None, color=WHITE, center=False):
        surf = (font or self.font).render(str(message), True, color)
        rect = surf.get_rect()
        if center:
            rect.center = (x, y)
        else:
            rect.topleft = (x, y)
        self.screen.blit(surf, rect)
        return rect

    def wait_for_enter(self, title, subtitle="Press ENTER to continue"):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    raise SystemExit
                if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                    return
            self.screen.fill(BG)
            self.text(title, WIDTH // 2, HEIGHT // 2 - 35, center=True)
            self.text(subtitle, WIDTH // 2, HEIGHT // 2 + 25, self.small, center=True)
            pygame.display.flip()
            self.clock.tick(30)

    def choose_card(self, player, hand, led_suit, trump_suit, plays):
        allowed = legal_cards(hand, led_suit)
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    raise SystemExit
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    x, y = event.pos
                    for i, card in enumerate(allowed):
                        rect = pygame.Rect(70 + i * 115, 560, 95, 135)
                        if rect.collidepoint(x, y):
                            return card
            self.screen.fill(BG)
            self.text(f"{player.name}: choose a card", 40, 25)
            self.text(f"Trump: {trump_suit or 'None'} | Led suit: {led_suit or 'Lead'}",
                      40, 75, self.small)
            self.text("Only legal cards are shown. Click one to play.", 40, 115, self.small)
            for i, card in enumerate(allowed):
                rect = pygame.Rect(70 + i * 115, 560, 95, 135)
                pygame.draw.rect(self.screen, WHITE, rect, border_radius=9)
                pygame.draw.rect(self.screen, DARK, rect, 2, border_radius=9)
                col = RED if card.suit in ("Hearts", "Diamonds") else BLACK
                self.text(card.label, rect.centerx, rect.centery, self.font, col, True)
            self.text(f"Cards in trick: {len(plays)} / {len(self.game.players)}",
                      40, 190, self.small)
            pygame.display.flip()
            self.clock.tick(30)

    def play_card_round(self):
        round_no = self.game.current_round
        hands, trump_suit, trump_card, _ = self.game.deal_round()
        self.wait_for_enter(
            f"Round {len(self.game.results) + 1}: {round_no} cards each",
            f"Trump card: {trump_card} (suit: {trump_suit}) — press ENTER",
        )
        bids = self._collect_bids(round_no)
        bids = self._correct_bids(bids, round_no)
        tricks_won = {p.name: 0 for p in self.game.players}
        leader = self.game.order_left_of_dealer()[0]

        for trick_no in range(round_no):
            order = [(leader + offset) % len(self.game.players)
                     for offset in range(len(self.game.players))]
            plays = []
            led_suit = None
            for player_index in order:
                player = self.game.players[player_index]
                self.wait_for_enter(
                    f"Pass the device to {player.name}",
                    "Keep the screen private. Press ENTER when ready.",
                )
                card = self.choose_card(player, hands[player_index], led_suit,
                                        trump_suit, plays)
                hands[player_index].remove(card)
                if led_suit is None:
                    led_suit = card.suit
                plays.append((player_index, card))
            winner_index = trick_winner(plays, trump_suit)
            tricks_won[self.game.players[winner_index].name] += 1
            leader = winner_index
            self.wait_for_enter(
                f"{self.game.players[winner_index].name} wins trick {trick_no + 1}",
                "Press ENTER for the next trick",
            )

        tricks_won = self._correct_tricks(tricks_won, round_no)
        return self.game.accept_round(bids, tricks_won, trump_suit)

    def _collect_bids(self, round_no):
        """
        Collects bids from each player in the order of play, starting from the player to the left of the dealer.
        Ensures that the dealer's bid does not make the total bids equal to the number of tricks for the round. Returns a dictionary mapping player names to their bids.

        Inputs:
        - round_no [int]: The number of tricks in the current round.

        Outputs:
        - bids [dict: {player_name: bid}]: A dictionary mapping player names to their respective bids for the current round.
        """
        bids = {}
        total = 0
        for index in self.game.order_left_of_dealer():
            player = self.game.players[index]
            self.wait_for_enter(f"Pass to {player.name} to enter bid",
                                "Press ENTER; bid entry appears next.")
            bid = self._number_entry(f"{player.name}, enter your bid (0-{round_no})", round_no)
            if index == self.game.dealer_index:
                while total + bid == round_no:
                    self.wait_for_enter(f"Dealer bid cannot be {round_no - total}."
                                        "That would make total bids equal total cards."
                                        "Press ENTER.")
                    bid = self._number_entry("Enter dealer's bid", round_no)
            bids[player.name] = bid
            total += bid
        return bids

    def _number_entry(self, title, maximum):
        value = ""
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    raise SystemExit
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN and value.isdigit():
                        number = int(value)
                        if 0 <= number <= maximum:
                            return number
                    elif event.key == pygame.K_BACKSPACE:
                        value = value[:-1]
                    elif event.unicode.isdigit():
                        value += event.unicode
            self.screen.fill(BG)
            self.text(title, WIDTH // 2, HEIGHT // 2 - 55, center=True)
            self.text(value or "_", WIDTH // 2, HEIGHT // 2 + 10, center=True)
            self.text("Type a number and press ENTER", WIDTH // 2, HEIGHT // 2 + 70,
                      self.small, center=True)
            pygame.display.flip()
            self.clock.tick(30)

    def _yes_no(self, title):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    raise SystemExit
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_y:
                        return True
                    if event.key == pygame.K_n:
                        return False
            self.screen.fill(BG)
            self.text(title, WIDTH // 2, HEIGHT // 2 - 25, center=True)
            self.text("Y = yes     N = no", WIDTH // 2, HEIGHT // 2 + 35,
                      self.small, center=True)
            pygame.display.flip()
            self.clock.tick(30)

    def _correct_bids(self, bids, round_no):
        while self._yes_no("Correct bids before scoring?"):
            corrected = dict(bids)
            for index in self.game.order_left_of_dealer():
                p = self.game.players[index]
                corrected[p.name] = self._number_entry(
                    f"Correct bid for {p.name} (0-{round_no})", round_no
                )
            if sum(corrected.values()) != round_no:
                return corrected
            self.wait_for_enter(
                "Invalid correction",
                "Dealer's bid cannot make total equal tricks. Press ENTER.",
            )
        return bids

    def _correct_tricks(self, tricks, round_no):
        while self._yes_no("Correct trick counts before scoring?"):
            corrected = {}
            for index in self.game.order_left_of_dealer():
                p = self.game.players[index]
                corrected[p.name] = self._number_entry(
                    f"Correct tricks for {p.name} (0-{round_no})", round_no
                )
            if sum(corrected.values()) == round_no:
                return corrected
            self.wait_for_enter(
                "Invalid correction",
                f"Tricks must total {round_no}. Press ENTER.",
            )
        return tricks

    def run(self):
        while self.game.current_round is not None:
            result = self.play_card_round()
            self.wait_for_enter(
                "Round complete",
                "Scores: " + " | ".join(f"{n}: {s}" for n, s in result.scores.items()),
            )
        pygame.quit()
