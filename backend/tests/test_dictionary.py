"""The bundled ENABLE word list and its loader."""

import gzip
import hashlib
from importlib import resources

import pytest

pytest.importorskip("backend.core.dictionary", reason="The word list is not merged yet")

from backend.core.dictionary import WordList, load_word_list
from backend.game.piles import build_deck
from backend.game.spelling import Dictionary, validate_cast

ENABLE_SHA256 = "3f16130220645692ed49c7134e24a18504c2ca55b3c012f7290e3e77c63b1a89"


def test_bundled_file_is_the_documented_enable_list() -> None:
    data = resources.files("backend.data").joinpath("enable1.txt.gz").read_bytes()

    assert hashlib.sha256(gzip.decompress(data)).hexdigest() == ENABLE_SHA256


def test_loads_every_word() -> None:
    assert len(load_word_list()) == 172_823


def test_is_loaded_once() -> None:
    assert load_word_list() is load_word_list()


@pytest.mark.parametrize("word", ["CAB", "cab", "Bravo", "ZYZZYVA", "AA", "QUIZ"])
def test_real_words(word: str) -> None:
    assert word in load_word_list()


@pytest.mark.parametrize("word", ["XQZ", "CBA", "", "A", "WAURD", "CAB ", "C-A-B"])
def test_not_words(word: str) -> None:
    assert word not in load_word_list()


@pytest.mark.parametrize("value", [None, 5, b"CAB", ["CAB"]])
def test_non_strings_are_not_words(value: object) -> None:
    assert value not in load_word_list()


def test_works_as_the_engine_dictionary() -> None:
    dictionary: Dictionary = load_word_list()
    deck = build_deck(0)
    hand = [next(g for g in deck if g.letters == letter) for letter in "BAT"]

    assert validate_cast(hand, [0, 1, 2], dictionary) == "BAT"


def test_word_list_from_custom_words() -> None:
    words = WordList(frozenset({"CAB"}))

    assert "cab" in words
    assert len(words) == 1
