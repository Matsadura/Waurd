"""Play seeded bot-vs-bot matches and print what happened.

uv run python scripts/simulate.py                  # 1,000 matches, the CSV as it is
uv run python scripts/simulate.py --all-perks      # treat every perk as ready
uv run python scripts/simulate.py --matches 200 --resign 0.01

Each match checks the engine's rules after every action and stops at the
first broken one, naming the seed that replays it.
"""

import argparse
import sys
import time
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from backend.core.dictionary import load_word_list
from backend.game.perks import load_catalog
from backend.game.simulation import BotStyle, InvariantError, simulate


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--matches", type=int, default=1000)
    parser.add_argument("--all-perks", action="store_true", help="draft every perk")
    parser.add_argument("--resign", type=float, default=0.0, help="chance per turn")
    parser.add_argument("--disconnect", type=float, default=0.0, help="chance per turn")
    parser.add_argument("--seed-prefix", default="sim")
    args = parser.parse_args()

    catalog = dict(load_catalog())
    if args.all_perks:
        catalog = {pid: replace(spec, ready=True) for pid, spec in catalog.items()}
    style = BotStyle(resign_chance=args.resign, disconnect_chance=args.disconnect)

    started = time.perf_counter()
    try:
        report = simulate(
            load_word_list(),
            matches=args.matches,
            catalog=catalog,
            style=style,
            seed_prefix=args.seed_prefix,
        )
    except InvariantError as error:
        print(f"Broken rule: {error}", file=sys.stderr)
        return 1
    seconds = time.perf_counter() - started

    ready = sum(spec.ready for spec in catalog.values())
    print(f"{args.matches} matches in {seconds:.1f}s, {ready} perks in drafts")
    for key, value in report.summary().items():
        print(f"  {key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
