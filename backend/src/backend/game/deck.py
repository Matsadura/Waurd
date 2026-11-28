"""Drawing glyphs: shared by the turn rules and the deck perks."""

from backend.game.models import Glyph, Match, Player


def draw(match: Match, player: Player, count: int) -> list[Glyph]:
    """Draw up to `count` glyphs into the hand, reshuffling the discard pile when
    the draw pile runs out. Returns the glyphs drawn."""
    drawn = []
    for _ in range(count):
        if not player.draw_pile:
            if not player.discard_pile:
                break
            player.draw_pile = player.discard_pile
            player.discard_pile = []
            match.rng.shuffle(player.draw_pile)
        glyph = player.draw_pile.pop()
        player.hand.append(glyph)
        drawn.append(glyph)
    return drawn
