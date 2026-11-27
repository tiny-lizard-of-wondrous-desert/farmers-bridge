"""Optional local pass-and-play Pygame interface."""
from __future__ import annotations
import random
import re

from ..models import Card, RANKS, Suit, legal_cards, trick_winner
from ..workflows import review_tricks, collect_bids, review_bids

try:
    import pygame
    from pygame_cards.classics import CardSets
except ImportError as exc:  # Import only when this optional interface is selected.
    raise ImportError("Pygame mode requires `uv sync --group local`.") from exc

WIDTH, HEIGHT = 1100, 760
BG, WHITE = (24, 92, 67), (245, 245, 235)


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
    def __init__(self, game, on_round_complete=None):
        pygame.init()
        self.game = game
        self.on_round_complete = on_round_complete
        self.library_cards = self._load_card_library()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Farmer's Bridge")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("arial", 28)
        self.small = pygame.font.SysFont("arial", 20)

    @staticmethod
    def _load_card_library():
        """Use pygame_cards' standard 52-card set for all card artwork."""
        library = {}
        rank_names = {
            "jack": 11, "queen": 12, "king": 13, "ace": 14,
            "j": 11, "q": 12, "k": 13, "a": 14,
        }
        for library_card in CardSets.n52.copy():
            name = str(library_card.name)
            lowered = name.casefold()
            suit = next(
                (candidate for candidate in Suit if candidate.value.casefold() in lowered),
                None,
            )
            if suit is None:
                raise RuntimeError(f"Cannot identify the suit in pygame_cards card {name!r}.")
            number = getattr(library_card, "number", None)
            if hasattr(number, "value"):
                number = number.value
            if not isinstance(number, int):
                token = re.split(r"\s+of\s+|\s+", lowered)[0]
                number = rank_names.get(token, int(token) if token.isdigit() else None)
            if number not in RANKS:
                token = re.split(r"\s+of\s+|\s+", lowered)[0]
                number = rank_names.get(token)
            if number not in RANKS:
                raise RuntimeError(f"Cannot identify the rank in pygame_cards card {name!r}.")
            library[(suit, number)] = library_card
        if len(library) != 52:
            raise RuntimeError(f"pygame_cards supplied {len(library)} unique cards; expected 52.")
        return library

    def _deal_round(self):
        """Deal from the pygame_cards 52-card library, retaining engine rule objects."""
        deck = list(self.library_cards)
        random.shuffle(deck)
        hands = {index: [] for index in range(len(self.game.players))}
        for _ in range(self.game.current_round):
            for player_index in self.game.order_left_of_dealer():
                suit, rank = deck.pop()
                hands[player_index].append(Card(suit, rank))
        suit, rank = deck.pop()
        trump_card = Card(suit, rank)
        return hands, trump_card.suit, trump_card, deck

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
                    card_height = int(card_width * 1.55)
                    gap = 8
                    start_x = (WIDTH - (len(allowed) * card_width + (len(allowed) - 1) * gap)) // 2
                    for i, card in enumerate(allowed):
                        rect = pygame.Rect(start_x + i * (card_width + gap), 550, card_width, card_height)
                        if rect.collidepoint(event.pos):
                            return card
            self.screen.fill(BG)
            self.text(f"{player.name}: choose a card", 40, 25)
            self.text(f"Trump: {trump_suit.value} | Led suit: {getattr(led_suit, 'value', 'Lead')}", 40, 75, self.small)
            self.text(f"Cards in trick: {len(plays)} / {len(self.game.players)}", 40, 115, self.small)
            card_width = min(90, (WIDTH - 60 - 8 * (len(allowed) - 1)) // len(allowed))
            card_height = int(card_width * 1.55)
            gap = 8
            start_x = (WIDTH - (len(allowed) * card_width + (len(allowed) - 1) * gap)) // 2
            for i, card in enumerate(allowed):
                x = start_x + i * (card_width + gap)
                library_card = self.library_cards[(card.suit, card.rank)]
                artwork = pygame.transform.smoothscale(
                    library_card.graphics.surface, (card_width, card_height)
                )
                self.screen.blit(artwork, (x, 550))
            pygame.display.flip()
            self.clock.tick(30)

    def _save_checkpoint(self):
        if self.on_round_complete:
            self.on_round_complete(self.game)

    @staticmethod
    def _card_data(card):
        return [card.suit.value, card.rank]

    @staticmethod
    def _card_from_data(data):
        return Card(Suit(data[0]), int(data[1]))

    def play_card_round(self):
        if self.game.is_complete:
            return None
        round_no = self.game.current_round
        active = self.game.active_round
        ui = PygamePrompts(self)

        if active is None:
            hands, trump_suit, trump_card, _ = self._deal_round()
            self.wait_for_enter(
                f"Round {len(self.game.results) + 1}: {round_no} cards each",
                f"Trump card: {trump_card} — press ENTER",
            )
            # Shared bid workflow: same collection, validation and correction logic as in-person mode.
            bids = review_bids(self.game, collect_bids(self.game, ui), ui)
            active = {
                "hands": {
                    str(index): [self._card_data(card) for card in hand]
                    for index, hand in hands.items()
                },
                "trump_suit": trump_suit.value,
                "trump_card": self._card_data(trump_card),
                "bids": bids,
                "tricks_won": {player.name: 0 for player in self.game.players},
                "leader": self.game.order_left_of_dealer()[0],
                "trick_no": 0,
                "plays": [],
                "next_player_offset": 0,
            }
            self.game.active_round = active
            self._save_checkpoint()
        hands = {
            int(index): [self._card_from_data(card) for card in cards]
            for index, cards in active["hands"].items()
        }
        trump_suit = Suit(active["trump_suit"])
        tricks_won = dict(active["tricks_won"])
        leader = int(active["leader"])

        while int(active["trick_no"]) < round_no:
            trick_no = int(active["trick_no"])
            order = [
                (leader + offset) % len(self.game.players)
                for offset in range(len(self.game.players))
            ]
            plays = [
                (int(play[0]), self._card_from_data(play[1]))
                for play in active["plays"]
            ]
            led_suit = plays[0][1].suit if plays else None

            while int(active["next_player_offset"]) < len(self.game.players):
                offset = int(active["next_player_offset"])
                player_index = order[offset]
                player = self.game.players[player_index]
                self.wait_for_enter(
                    f"Pass the device to {player.name}",
                    "Keep the screen private; press ENTER",
                )
                card = self.choose_card(player, hands[player_index], led_suit, trump_suit, plays)
                hands[player_index].remove(card)
                plays.append((player_index, card))
                led_suit = led_suit or card.suit
                active["hands"] = {
                    str(index): [self._card_data(item) for item in hand]
                    for index, hand in hands.items()
                }
                active["plays"] = [
                    [index, self._card_data(item)] for index, item in plays
                ]
                active["next_player_offset"] = offset + 1
                self.game.active_round = active
                self._save_checkpoint()

            winner = trick_winner(plays, trump_suit)
            tricks_won[self.game.players[winner].name] += 1
            leader = winner
            active.update({
                "tricks_won": tricks_won,
                "leader": leader,
                "trick_no": trick_no + 1,
                "plays": [],
                "next_player_offset": 0,
            })
            self.game.active_round = active
            self._save_checkpoint()
            self.wait_for_enter(f"{self.game.players[winner].name} wins trick {trick_no + 1}")

        tricks_won = review_tricks(self.game, tricks_won, ui)
        result = self.game.accept_round(active["bids"], tricks_won, trump_suit)
        self._save_checkpoint()
        return result

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
