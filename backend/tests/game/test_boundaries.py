"""The engine stays pure: no web framework, database, Redis, clock or asyncio,
nothing from the rest of the backend, and randomness only through rng.py."""

import ast
from pathlib import Path

import pytest

game = pytest.importorskip("backend.game", reason="The game engine is not merged yet")

ENGINE_DIR = Path(game.__file__).resolve().parent
FORBIDDEN = {
    "fastapi",
    "starlette",
    "sqlalchemy",
    "redis",
    "asyncmy",
    "time",
    "asyncio",
}


def imported_modules(tree: ast.AST) -> list[str]:
    """Absolute module names a file imports (relative imports stay in the package)."""
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names.append(node.module)
    return names


def violations(source: str, filename: str) -> list[str]:
    """Every boundary rule a file breaks."""
    tree = ast.parse(source, filename=filename)
    problems: list[str] = []

    for module in imported_modules(tree):
        root = module.split(".")[0]
        if root in FORBIDDEN:
            problems.append(f"imports {module}")
        if root == "backend" and not (
            module == "backend.game" or module.startswith("backend.game.")
        ):
            problems.append(f"imports {module} from outside the engine")
        if root == "random" and filename != "rng.py":
            problems.append("imports random outside rng.py")

    if filename == "rng.py":
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "random":
                extra = [a.name for a in node.names if a.name != "Random"]
                if extra:
                    problems.append(f"uses random.{extra[0]}")
            if (
                isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Name)
                and node.value.id == "random"
                and node.attr != "Random"
            ):
                problems.append(f"uses random.{node.attr}")

    return problems


ENGINE_FILES = sorted(ENGINE_DIR.rglob("*.py"))


def test_engine_files_were_found() -> None:
    assert {path.name for path in ENGINE_FILES} >= {
        "__init__.py",
        "rng.py",
        "config.py",
    }


@pytest.mark.parametrize("path", ENGINE_FILES, ids=lambda p: p.name)
def test_engine_file_respects_boundaries(path: Path) -> None:
    assert violations(path.read_text(), path.name) == []


@pytest.mark.parametrize(
    ("source", "filename", "expected"),
    [
        ("import fastapi", "x.py", "imports fastapi"),
        ("from sqlalchemy.orm import Session", "x.py", "imports sqlalchemy.orm"),
        ("import redis.asyncio", "x.py", "imports redis.asyncio"),
        ("import time", "x.py", "imports time"),
        ("import asyncio", "x.py", "imports asyncio"),
        ("from starlette import status", "x.py", "imports starlette"),
        ("import asyncmy", "x.py", "imports asyncmy"),
        (
            "from backend.core import config",
            "x.py",
            "imports backend.core from outside the engine",
        ),
        ("import random", "piles.py", "imports random outside rng.py"),
        ("from random import shuffle", "rng.py", "uses random.shuffle"),
        ("import random\nrandom.shuffle([])", "rng.py", "uses random.shuffle"),
    ],
)
def test_checker_catches_violations(source: str, filename: str, expected: str) -> None:
    assert expected in violations(source, filename)


@pytest.mark.parametrize(
    ("source", "filename"),
    [
        ("from backend.game.config import GameConfig", "x.py"),
        ("from . import config", "x.py"),
        ("import random\nrandom.Random('s')", "rng.py"),
        ("from random import Random", "rng.py"),
        ("import pydantic\nimport secrets", "x.py"),
    ],
)
def test_checker_allows_engine_code(source: str, filename: str) -> None:
    assert violations(source, filename) == []
