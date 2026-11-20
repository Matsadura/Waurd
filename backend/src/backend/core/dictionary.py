"""The English word list the game accepts, loaded once per process.

The list is ENABLE (Enhanced North American Benchmark Lexicon), 172,823
words, which is in the public domain. Source and licence notes are in
backend/data/WORDLIST.md. The game engine never loads this itself; the match
runtime passes it in as a backend.game.spelling.Dictionary.
"""

import gzip
from collections.abc import Iterator
from functools import lru_cache
from importlib import resources


class WordList:
    """A set of uppercase words, usable as a game Dictionary."""

    def __init__(self, words: frozenset[str]) -> None:
        self._words = words

    def __contains__(self, word: object) -> bool:
        return isinstance(word, str) and word.upper() in self._words

    def __len__(self) -> int:
        return len(self._words)

    def __iter__(self) -> Iterator[str]:
        return iter(self._words)


@lru_cache(maxsize=1)
def load_word_list() -> WordList:
    """Read the bundled ENABLE list. Cached, so it's read once per process."""
    data = resources.files("backend.data").joinpath("enable1.txt.gz").read_bytes()
    text = gzip.decompress(data).decode("ascii")
    return WordList(
        frozenset(line.strip().upper() for line in text.splitlines() if line.strip())
    )
