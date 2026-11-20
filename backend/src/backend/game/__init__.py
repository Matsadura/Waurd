"""The Waurd game engine.

Pure Python: no database, Redis, web framework, clock or asyncio. The match
runtime feeds it actions and the current time, stores the state it returns,
and sends out the events. tests/game/test_boundaries.py enforces this.
"""
