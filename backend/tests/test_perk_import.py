"""Copying the perk catalog CSV into the database perks table."""

import logging
from dataclasses import replace

import pytest

pytest.importorskip("backend.core.perk_import", reason="Perk import is not merged yet")

from backend.core.perk_import import import_perks, import_perks_on_startup
from backend.game.perks import load_catalog
from sqlalchemy import select

from backend.core import perk_import
from backend.models import Perk
from backend.models.perk import ModificationType, Rarity, TargetGlyphType


async def run(session_maker, catalog=None):  # type: ignore[no-untyped-def]
    async with session_maker() as session:
        report = await import_perks(session, catalog)
        await session.commit()
    return report


async def perks(session_maker) -> dict[str, Perk]:  # type: ignore[no-untyped-def]
    async with session_maker() as session:
        return {p.id: p for p in (await session.scalars(select(Perk))).all()}


def catalog_with(**changes):  # type: ignore[no-untyped-def]
    """The bundled catalog with some rows changed: id=dict of new values."""
    catalog = dict(load_catalog())
    for perk_id, values in changes.items():
        catalog[perk_id] = replace(catalog[perk_id], **values)
    return catalog


class TestImport:
    async def test_creates_every_catalog_row(self, session_maker):
        report = await run(session_maker)

        rows = await perks(session_maker)
        assert set(rows) == set(load_catalog())
        assert sorted(report.created) == sorted(load_catalog())
        assert report.updated == report.disabled == []

    async def test_maps_the_columns(self, session_maker):
        await run(session_maker)
        rows = await perks(session_maker)

        ing = rows["ing"]
        assert ing.name == "-ING-"
        assert ing.rarity == Rarity.UNCOMMON
        assert ing.target_glyph_type == TargetGlyphType.POWER
        assert ing.modification_type == ModificationType.LETTERS
        assert ing.durability == 4
        assert ing.quote is None and ing.image_url is None
        assert ing.effect_payload == {}
        assert rows["erase"].target_glyph_type == TargetGlyphType.SKILL
        assert rows["erase"].modification_type == ModificationType.DECK
        assert rows["matching_ends_x2"].target_glyph_type == TargetGlyphType.ANY
        assert (
            rows["last_plus_5"].modification_type == ModificationType.CONDITIONAL_SLOT
        )
        assert rows["last_plus_5"].durability is None

    async def test_ready_status_becomes_is_enabled(self, session_maker):
        await run(session_maker, catalog_with(amplify={"ready": True}))
        rows = await perks(session_maker)

        assert rows["amplify"].is_enabled is True
        assert rows["ing"].is_enabled is False

    async def test_running_again_changes_nothing(self, session_maker):
        await run(session_maker)

        report = await run(session_maker)

        assert report.created == report.updated == report.disabled == []

    async def test_changed_rows_are_updated(self, session_maker):
        await run(session_maker)

        report = await run(
            session_maker,
            catalog_with(
                amplify={"name": "Mega Amplify", "durability": 2, "ready": True}
            ),
        )

        assert report.updated == ["amplify"]
        amplify = (await perks(session_maker))["amplify"]
        assert (amplify.name, amplify.durability, amplify.is_enabled) == (
            "Mega Amplify",
            2,
            True,
        )

    async def test_update_keeps_existing_effect_payload(self, session_maker):
        await run(session_maker)
        async with session_maker() as session:
            perk = await session.get(Perk, "amplify")
            perk.effect_payload = {"legacy": True}
            await session.commit()

        await run(session_maker, catalog_with(amplify={"name": "Amp"}))

        assert (await perks(session_maker))["amplify"].effect_payload == {
            "legacy": True
        }

    async def test_perks_removed_from_the_csv_are_disabled_not_deleted(
        self, session_maker
    ):
        await run(session_maker, catalog_with(amplify={"ready": True}))
        async with session_maker() as session:
            session.add(
                Perk(
                    id="old_perk",
                    name="Old",
                    description="Gone from the CSV.",
                    rarity=Rarity.COMMON,
                    target_glyph_type=TargetGlyphType.ANY,
                    modification_type=ModificationType.EFFECT,
                    effect_payload={},
                    is_enabled=True,
                )
            )
            await session.commit()

        report = await run(session_maker)

        rows = await perks(session_maker)
        assert report.disabled == ["old_perk"]
        assert rows["old_perk"].is_enabled is False
        # Back to the bundled CSV, where amplify is not_ready.
        assert report.updated == ["amplify"]

    async def test_row_without_a_function_aborts_before_writing(self, session_maker):
        catalog = dict(load_catalog())
        catalog["mystery"] = replace(catalog["amplify"], id="mystery")

        with pytest.raises(ValueError, match="no function: mystery"):
            await run(session_maker, catalog)

        assert await perks(session_maker) == {}


class TestStartup:
    async def test_imports_and_commits(self, session_maker):
        async with session_maker() as session:
            await import_perks_on_startup(session)

        assert set(await perks(session_maker)) == set(load_catalog())

    async def test_failure_is_logged_not_raised(
        self, session_maker, monkeypatch, caplog
    ):
        async def broken(session, catalog=None):  # type: ignore[no-untyped-def]
            session.add(
                Perk(
                    id="half_written",
                    name="Half",
                    description="Should be rolled back.",
                    rarity=Rarity.COMMON,
                    target_glyph_type=TargetGlyphType.ANY,
                    modification_type=ModificationType.EFFECT,
                    effect_payload={},
                )
            )
            await session.flush()
            raise RuntimeError("database not migrated")

        monkeypatch.setattr(perk_import, "import_perks", broken)

        with caplog.at_level(logging.ERROR):
            async with session_maker() as session:
                await import_perks_on_startup(session)

        assert "Importing perks from catalog.csv failed" in caplog.text
        assert await perks(session_maker) == {}
