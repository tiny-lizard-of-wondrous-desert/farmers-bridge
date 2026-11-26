"""Optional local pass-and-play Pygame interface."""
from __future__ import annotations
from ..models import legal_cards, trick_winner
from ..workflows import enter_round_totals

try:
    import pygame
except ImportError as exc:  # Import only when this optional interface is selected.
    raise ImportError("Pygame mode requires `uv pip install -r requirements-pygame.txt`.") from exc

WIDTH, HEIGHT = 1100, 760
BG, WHITE, DARK, RED, BLACK = (24, 92, 67), (245, 245, 235), (25, 30, 32), (180, 55, 55), (20, 20, 20)


class WindowClosed(Exception):
    """Internal control-flow signal for a user closing the Pygame window."""


class PygamePrompts:
    """Adapter implementing the same prompts protocol as the console UI."""
    def __init__(self, table):
        self.table = table

    def number(self, message: str, maximum: int) -> int:
        return self.table.number_entry(message, maximum)

    def yes_no(self, message: str) -> bool:
        return self.table.yes_no(message)

    def message(self, message: str) -> None:
        self.table.wait_for_enter(message)


class PygameTable:
    def __init__(self, game):
        pygame.init()
        self.game = game
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Farmer's Bridge")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("arial", 28)
        self.small = pygame.font.SysFont("arial", 20)

    def _events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                raise WindowClosed
            yield event

    def text(self, message, x, y, font=None, color=WHITE, center=False):
        surface = (font or self.font).render(str(message), True, color)
        rect = surface.get_rect()
        rect.center = (x, y) if center else rect.center
        if not center:
            rect.topleft = (x, y)
        self.screen.blit(surface, rect)

    def wait_for_enter(self, title, subtitle="Press ENTER to continue"):
        while True:
            for event in self._events():
                if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                    return
            self.screen.fill(BG)
            self.text(title, WIDTH // 2, HEIGHT // 2 - 35, center=True)
            self.text(subtitle, WIDTH // 2, HEIGHT // 2 + 25, self.small, center=True)
            pygame.display.flip()
            self.clock.tick(30)

    def number_entry(self, title, maximum):
        value = ""
        while True:
            for event in self._events():
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
            self.text("Type a number and press ENTER", WIDTH // 2, HEIGHT // 2 + 70, self.small, center=True)
            pygame.display.flip()
            self.clock.tick(30)

    def yes_no(self, title):
        while True:
            for event in self._events():
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_y:
                        return True
                    if event.key == pygame.K_n:
                        return False
            self.screen.fill(BG)
            self.text(title, WIDTH // 2, HEIGHT // 2 - 25, center=True)
            self.text("Y = yes     N = no", WIDTH // 2, HEIGHT // 2 + 35, self.small, center=True)
            pygame.display.flip()
            self.clock.tick(30)

    def choose_card(self, player, hand, led_suit, trump_suit, plays):
        allowed = legal_cards(hand, led_suit)
        while True:
            for event in self._events():
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    card_width = min(90, (WIDTH - 60 - 8 * (len(allowed) - 1)) // len(allowed))
                    gap = 8
                    start_x = (WIDTH - (len(allowed) * card_width + (len(allowed) - 1) * gap)) // 2
                    for i, card in enumerate(allowed):
                        rect = pygame.Rect(start_x + i * (card_width + gap), 550, card_width, 135)
                        if rect.collidepoint(event.pos):
                            return card
            self.screen.fill(BG)
            self.text(f"{player.name}: choose a card", 40, 25)
            self.text(f"Trump: {trump_suit.value} | Led suit: {getattr(led_suit, 'value', 'Lead')}", 40, 75, self.small)
            self.text(f"Cards in trick: {len(plays)} / {len(self.game.players)}", 40, 115, self.small)
            card_width = min(90, (WIDTH - 60 - 8 * (len(allowed) - 1)) // len(allowed))
            gap = 8
            start_x = (WIDTH - (len(allowed) * card_width + (len(allowed) - 1) * gap)) // 2
            for i, card in enumerate(allowed):
                rect = pygame.Rect(start_x + i * (card_width + gap), 550, card_width, 135)
                pygame.draw.rect(self.screen, WHITE, rect, border_radius=9)
                pygame.draw.rect(self.screen, DARK, rect, 2, border_radius=9)
                color = RED if card.suit.value in ("Hearts", "Diamonds") else BLACK
                self.text(card.label, rect.centerx, rect.centery, self.font, color, True)
            pygame.display.flip()
            self.clock.tick(30)

    def play_card_round(self):
        if self.game.is_complete:
            return None
        round_no = self.game.current_round
        hands, trump_suit, trump_card, _ = self.game.deal_round()
        self.wait_for_enter(f"Round {len(self.game.results) + 1}: {round_no} cards each",
                            f"Trump card: {trump_card} — press ENTER")
        ui = PygamePrompts(self)
        # Shared bid workflow: same collection, validation and correction logic as in-person mode.
        from ..workflows import collect_bids, review_bids, collect_tricks, review_tricks
        bids = review_bids(self.game, collect_bids(self.game, ui), ui)
        tricks_won = {p.name: 0 for p in self.game.players}
        leader = self.game.order_left_of_dealer()[0]
        for trick_no in range(round_no):
            order = [(leader + offset) % len(self.game.players) for offset in range(len(self.game.players))]
            plays, led_suit = [], None
            for player_index in order:
                player = self.game.players[player_index]
                self.wait_for_enter(f"Pass the device to {player.name}", "Keep the screen private; press ENTER")
                card = self.choose_card(player, hands[player_index], led_suit, trump_suit, plays)
                hands[player_index].remove(card)
                led_suit = led_suit or card.suit
                plays.append((player_index, card))
            winner = trick_winner(plays, trump_suit)
            tricks_won[self.game.players[winner].name] += 1
            leader = winner
            self.wait_for_enter(f"{self.game.players[winner].name} wins trick {trick_no + 1}")
        tricks_won = review_tricks(self.game, tricks_won, ui)
        return self.game.accept_round(bids, tricks_won, trump_suit)

    def run(self):
        """Run until normal completion or window close; always release Pygame."""
        try:
            while not self.game.is_complete:
                result = self.play_card_round()
                if result is None:
                    break
                self.wait_for_enter("Round complete", " | ".join(f"{n}: {s}" for n, s in result.scores.items()))
            if self.game.is_complete:
                self.wait_for_enter("Game complete!", "Press ENTER to close")
            return self.game.is_complete
        except WindowClosed:
            return self.game.is_complete
        finally:
            pygame.quit()
