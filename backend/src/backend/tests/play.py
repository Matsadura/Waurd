"""Play Waurd in the terminal: two players, one keyboard.

Run from the backend folder:
    uv run python scripts/play.py                     # small built-in word list
    uv run python scripts/play.py --words words.txt   # one word per line
    uv run python scripts/play.py --seed 42           # same seed = same match

On your turn, type a word made from your hand, "pass" or "quit".
"""

import argparse
import random

from backend.game.models import Glyph, Match
from backend.game.rules import (
    cast_word,
    select_perks,
    pass_turn,
    start_turn,
)
from backend.game.setup import load_words, new_match

STARTER_WORDS = """
a an at as am be by do go he if in is it me my no of on or so to up us we
ace act add age aid aim air ale and ant ape arc are arm art ash ate bad bag
ban bat bed bet bid big bin bit bog bud bug bun bus but cab can cap car cat
cod cot cow cub cup cut dad dam den dig dim din dip dog dot dry due dug ear
eat egg elf elm end era eve eye fan far fat fed few fig fin fit fly fog for
fun fur gap gas gem get gin god got gum gun gut ham hat hen her hid him hip
his hit hog hot how hub hug hum hut ice ill ink inn ion its key kid kin kit
lab lad lap law lay led leg let lid lie lip lit log lot low mad man map mat
men met mid mob mop mud mug nap net new nib nod nor not now nut oak oar oat
odd off oil old one opt orb ore our out owl own pad pal pan pat paw pay pea
pen pet pie pig pin pit pod pot pun pup put rag ram ran rat raw red rib rid
rig rim rip rod rot row rub rug run rut sad sat saw say sea set she shy sin
sip sit ski sky sly son sow soy spa spy sub sum sun tab tag tan tap tar tea
ten the tie tin tip toe ton top tow toy try tub tug two use van vat vet vow
war was wax way web wed wet who why wig win wit woe won yak yam yes yet you
able bake band bark bear beat bend best bird boat bold bone brag cake calm
card care cart cash cast clan coat code cold come cord cost dare dark dart
dash date dawn deal dear dent dine dirt dish dive dome done door dove dust
earn east edge face fact fade fair fake fame farm fast fate fear feat film
find fire fish flag foam fold fond fore form fort gain game gate gift gold
golf grab grin grow hand hard harm hate head heal hear heat herd hero hide
hint hold hole home hope horn hunt idea iron kind king knit lake land last
late lead lean lend lion load loan lone lord lose loud love main make mark
mast mean melt mild mind mint mist mold most mule name near neat nest note
oath open oven pace pain pair pale palm part past path peak pine plan plot
post pour rain rate read rest rice ride ring rise road roam robe rock role
rope rose rust safe sail salt sand seal seat send shed ship shoe shot sing
slow snow soap soft song sour spin star stem stir tail tale talk tame tear
tend tent tide time tone torn town trap tree trim tune vast vine vote wade
wait wake walk wand want warm wave weak wear west wide wild wind wine wing
wise wolf word worn yard year beast blade brave break charm cider crown
dream drink earth feast flame ghost giant grind heart honor horse light
magic night ocean plant point power quest raven risen scale shade shine
sword spell stone storm tower trade water witch wound youth
"""


def positions_for(word: str, hand: list[Glyph]) -> list[int] | None:
    """Find hand positions that spell `word`, or None if the hand can't."""
    positions = []
    for letter in word:
        free = [
            i
            for i, glyph in enumerate(hand)
            if glyph.letter == letter and i not in positions
        ]
        if not free:
            return None
        positions.append(free[0])
    return positions


def show(match: Match) -> None:
    me = match.active_player_index
    player = match.players[me]
    opponent = match.players[1 - me]
    hand = "  ".join(f"{g.letter}({g.effect_value})" for g in player.hand)
    print(f"\n--- Turn {match.turn}: Player {me + 1} ---")
    print(f"You: {player.hp} HP   Opponent: {opponent.hp} HP")
    print(f"Hand: {hand}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Play Waurd in the terminal.")
    parser.add_argument("--words", help="word list file, one word per line")
    parser.add_argument("--seed", type=int, help="replay the same match")
    args = parser.parse_args()

    words = load_words(args.words)
    match = new_match(args.seed)
    start_turn(match)

    while match.winner is None:
        show(match)
        me = match.active_player_index
        answer = input("Word, pass or quit: ").strip().upper()

        if answer == "QUIT":
            return
        if answer == "PASS":
            pass_turn(match, me)
            continue

        positions = positions_for(answer, match.players[me].hand)
        if positions is None:
            print("Your hand can't spell that.")
            continue

        target_hp = match.players[1 - me].hp
        try:
            cast_word(match, me, positions, words)
            if match.winner is None:
                select_perks(match, me, [])  # no perk drafting in this script
        except ValueError as error:
            print(error)
            continue
        damage = target_hp - match.players[1 - me].hp
        print(f"{answer} hits for {damage}!")

    print(f"\nPlayer {match.winner + 1} wins on turn {match.turn}!")


if __name__ == "__main__":
    main()
