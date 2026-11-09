# Waurd

> A 1v1 PvP Word-Crafting Deckbuilder under time pressure.

---

## Overview

**Waurd** (Gothic for *word*) merges fast-paced deck-building mechanics with word-crafting combat. Players construct words from an evolving deck of letter cards under strict chess-like time controls to reduce their opponent's health to zero.

- **Genre**: 1v1 PvP Word-Crafting Battler / Deckbuilder / Strategy
- **Platform**: Web (Matchmaking with standard Elo rating)
- **Target Audience**: Competitive players who enjoy word games and deck-building mechanics

---

## Core Gameplay Loop

1. **Draw Phase**: At turn start, draw `<HAND_SIZE>` Glyphs from your draw pile. Your hand remains hidden until your turn timer starts ticking.
2. **Perk Phase**: Modify available Glyphs by applying active Perks to change stats, behaviors, or conditional triggers.
3. **Spell & Cast**: Spell a valid English word and cast it before your timer runs out.
4. **Resolution**: Glyphs resolve left-to-right (applying effects and bonus slots) against the opponent or caster.
5. **Discard & Draft**: All drawn Glyphs go to the discard pile. Draft new Perks from a random pool (with limited match rerolls).
6. **Turn Pass**: Opponent takes their turn. When a draw pile runs out, the discard pile reshuffles into the draw pile.

---

## Key Elements

### Glyphs
Magical letter cards that serve as the fundamental unit of combat.
- **Attributes**: Character letter, type (Power or Skill), effect (Damage, Heal, Defense, Vulnerability, Weak), effect value, and one Bonus Conditional Slot.
- **Resolution**: Triggered sequentially in the order spelled (e.g., doubling damage if placed in the first position).

### Perks
The primary strategic currency used to modify Glyphs.
- **Modifications**: Alter Glyph type, effect, numerical values, or inject conditional modifiers.
- **Durability**: Perks degrade per application and are destroyed once their durability reaches zero.

### Achievement / Collection System
Persistent milestones (e.g., casting specific thematic word lists like animal names) that unlock permanent bonus Perks equipped at the start of matches.

---

## Team

- **aljbari**: Product Owner, Game Designer, UI Designer, Front-End Developer
- **anaamaja**: Game Designer, UI Designer, Front-End Developer & Sound Designer
- **hfakou**: Back-End Engineer, Database Designer, API Designer
- **rmaanane**: DevOps Engineer, CI/CD Lead, Penetration Tester, SOC Analyst
- **zzaoui**: Back-End Engineer, Database Designer, API Designer

---

*Based on Game Design Document v25/10/2026 (1337 Coding School).*