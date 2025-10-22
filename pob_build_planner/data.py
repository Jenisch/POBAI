"""Sample build library for the Path of Building planner."""
from __future__ import annotations

from typing import Dict, List

Build = Dict[str, object]

BUILD_LIBRARY: List[Build] = [
    {
        "id": "cyclone_slayer",
        "name": "Cyclone Slayer",
        "summary": (
            "A spin-to-win Slayer that leverages high attack speed, life leech, "
            "and armour stacking to clear maps smoothly while remaining comfortable "
            "for boss encounters."
        ),
        "ascendancy": "Duelist - Slayer",
        "tags": {
            "damage_type": ["physical"],
            "combat_range": ["melee"],
            "damage_source": ["attack"],
            "complexity": "low",
            "budget": ["medium", "league_start"],
            "league_start": True,
            "content": ["mapping", "bossing"],
            "defense_layers": ["armour", "life_leech", "fortify"],
            "mobility": True,
        },
        "core_passives": [
            "Take Impact for effortless stun immunity while cycloning.",
            "Headsman and Bane of Legends keep clear speed high and execute bosses.",
            "Stack armour, Fortify effect, and spell suppression on rare gear."
        ],
        "skill_gems": {
            "main_skill": "Cyclone",
            "six_link": [
                "Cyclone",
                "Infused Channeling",
                "Impale",
                "Brutality",
                "Fortify",
                "Close Combat",
            ],
            "guard": "Molten Shell",
            "aura_setup": [
                "Pride",
                "Flesh and Stone",
                "Blood and Sand",
                "Herald of Purity",
            ],
            "mobility": "Leap Slam",
        },
        "gear": {
            "weapon": "Two-handed axe with high physical DPS and attack speed.",
            "armour": "Rare armour gear with life, resistances, and spell suppression.",
            "jewels": "Watcher's Eye with Pride mods, rare jewels with attack speed."
        },
        "progression": {
            "leveling": (
                "Level with Splitting Steel or Perforate until Cyclone becomes available "
                "at level 28. Invest in life and damage clusters on the passive tree "
                "while prioritising gear upgrades that add flat physical damage."
            ),
            "early_endgame": (
                "Transition into a six-link Cyclone and start stacking armour. "
                "Secure a Perseverance belt for damage and mobility."
            ),
            "endgame": (
                "Aim for an elevated Pride Watcher's Eye, double-influenced weapon, "
                "and explodey chest. Optimize flasks for critical strike suppression."
            ),
        },
    },
    {
        "id": "toxic_rain_pathfinder",
        "name": "Toxic Rain Pathfinder",
        "summary": (
            "A chaos damage over time archer that excels at bossing and league starts "
            "with very high defensive layering and mobility."
        ),
        "ascendancy": "Ranger - Pathfinder",
        "tags": {
            "damage_type": ["chaos"],
            "combat_range": ["ranged"],
            "damage_source": ["attack"],
            "complexity": "medium",
            "budget": ["low", "league_start"],
            "league_start": True,
            "content": ["bossing", "mapping"],
            "defense_layers": ["evasion", "spell_suppression", "ailment_avoidance"],
            "mobility": True,
        },
        "core_passives": [
            "Nature's Reprisal and Master Toxicist turbo-charge damage over time.",
            "Travel to skill effect duration wheels to stack pod overlap.",
            "Invest into spell suppression and ailment avoidance for near-immunity."
        ],
        "skill_gems": {
            "main_skill": "Toxic Rain",
            "six_link": [
                "Toxic Rain",
                "Ballista Totem Support",
                "Vicious Projectiles",
                "Void Manipulation",
                "Swift Affliction",
                "Efficacy",
            ],
            "guard": "Steelskin",
            "aura_setup": [
                "Malevolence",
                "Grace",
                "Determination",
            ],
            "mobility": "Dash + Flame Dash",
        },
        "gear": {
            "weapon": "+3 to socketed bow gems, damage over time multiplier bow.",
            "armour": "Evasion-based gear with life and chaos damage over time multiplier.",
            "jewels": "Malevolence Watcher's Eye, rare jewels with dot multi."
        },
        "progression": {
            "leveling": (
                "Use Caustic Arrow until level 12, then swap to Toxic Rain. Stack attack "
                "speed and skill effect duration early for smoother gameplay."
            ),
            "early_endgame": (
                "Acquire a +2 or +3 bow as soon as possible and craft damage over time "
                "multiplier quivers. Cap spell suppression before diving into red maps."
            ),
            "endgame": (
                "Upgrade to elevated Hunter bases with damage over time multiplier, and "
                "push for Mageblood or Headhunter once resistances are overcapped."
            ),
        },
    },
    {
        "id": "srs_necromancer",
        "name": "Summon Raging Spirits Necromancer",
        "summary": (
            "A minion-focused playstyle that keeps the player safe while an army of "
            "flaming skulls deals both mapping and bossing damage."
        ),
        "ascendancy": "Witch - Necromancer",
        "tags": {
            "damage_type": ["fire", "elemental"],
            "combat_range": ["ranged"],
            "damage_source": ["minion"],
            "complexity": "low",
            "budget": ["low", "league_start"],
            "league_start": True,
            "content": ["mapping", "bossing"],
            "defense_layers": ["block", "minion_taunt", "life_regen"],
            "mobility": False,
        },
        "core_passives": [
            "Unnatural Strength and Mistress of Sacrifice scale minion damage and defence.",
            "Spiritual Aid converts minion damage to personal spell damage for utility skills.",
            "Use Glancing Blows with a high block shield for layered defences."
        ],
        "skill_gems": {
            "main_skill": "Summon Raging Spirit",
            "six_link": [
                "Summon Raging Spirit",
                "Minion Damage",
                "Elemental Focus",
                "Spell Echo",
                "Unleash",
                "Empower",
            ],
            "guard": "Bone Offering",
            "aura_setup": [
                "Determination",
                "Defiance Banner",
                "Discipline",
            ],
            "mobility": "Flame Dash",
        },
        "gear": {
            "weapon": "Convoking wand with +1 to all spell skill gems and minion damage.",
            "armour": "Rare armour with life, resistances, and minion modifiers.",
            "jewels": "Ghastly Eye jewels with minion life and damage."
        },
        "progression": {
            "leveling": (
                "Use Freezing Pulse or Absolution until Summon Raging Spirits at level 4. "
                "Prioritize minion damage, life, and resistances on gear."
            ),
            "early_endgame": (
                "Craft a trigger wand for Offering and Desecrate automation and secure "
                "a +2 to minion gem helmet."
            ),
            "endgame": (
                "Stack minion crit and frenzy charge generation, with Ashes of the Stars "
                "as the ultimate luxury upgrade."
            ),
        },
    },
    {
        "id": "rf_inquisitor",
        "name": "Righteous Fire Inquisitor",
        "summary": (
            "A tanky burning templar that clears by running through packs while melting "
            "bosses with Ignite Proliferation and strong regeneration."
        ),
        "ascendancy": "Templar - Inquisitor",
        "tags": {
            "damage_type": ["fire", "elemental"],
            "combat_range": ["ranged", "aoe"],
            "damage_source": ["spell", "damage_over_time"],
            "complexity": "medium",
            "budget": ["medium", "league_start"],
            "league_start": True,
            "content": ["mapping", "bossing"],
            "defense_layers": ["life_regen", "block", "max_res"],
            "mobility": True,
        },
        "core_passives": [
            "Pious Path and Sanctuary grant huge regeneration and ailment cleanse.",
            "Anoint Holy Fire and path to Burning Crusade for damage scaling.",
            "Invest heavily into maximum fire resistance and life regeneration."
        ],
        "skill_gems": {
            "main_skill": "Righteous Fire",
            "six_link": [
                "Righteous Fire",
                "Burning Damage",
                "Elemental Focus",
                "Efficacy",
                "Increased Area of Effect",
                "Swift Affliction",
            ],
            "secondary_skill": "Fire Trap for single target burst",
            "guard": "Molten Shell",
            "aura_setup": [
                "Determination",
                "Purity of Fire",
                "Vitality",
            ],
            "mobility": "Shield Charge",
        },
        "gear": {
            "weapon": "Sceptre with fire damage over time multiplier and +1 fire gems.",
            "armour": "Armour/energy shield hybrid gear with life, regen, and resists.",
            "jewels": "Militant Faith (High Templar Venarius) and rare DoT multi jewels."
        },
        "progression": {
            "leveling": (
                "Level with Purifying Flame until 16, then swap to Fire Trap and Holy Flame Totem. "
                "Activate Righteous Fire once you can sustain 75% fire resistance and 1500 regen."
            ),
            "early_endgame": (
                "Craft or buy an early Legacy of Fury, then stack life regen and % max fire res."
            ),
            "endgame": (
                "Aim for double-influenced helmets with +3 RF radius, Eldritch implicits, "
                "and a Legacy of Fury with elevated scorched ground."
            ),
        },
    },
    {
        "id": "lightning_trap_saboteur",
        "name": "Lightning Trap Saboteur",
        "summary": (
            "A trapper that excels at burst damage, instant mobility, and safe bossing "
            "by staying off-screen while traps annihilate enemies."
        ),
        "ascendancy": "Shadow - Saboteur",
        "tags": {
            "damage_type": ["lightning", "elemental"],
            "combat_range": ["ranged"],
            "damage_source": ["trap", "spell"],
            "complexity": "high",
            "budget": ["medium", "high"],
            "league_start": False,
            "content": ["bossing", "delve", "juiced_mapping"],
            "defense_layers": ["evasion", "blind", "ailment_avoidance"],
            "mobility": True,
        },
        "core_passives": [
            "Perfect Crime and Chain Reaction for trap cooldown recovery and chaining.",
            "Path to Saboteur trap clusters and Heart of Thunder for scaling lightning."
        ],
        "skill_gems": {
            "main_skill": "Lightning Trap",
            "six_link": [
                "Lightning Trap",
                "Advanced Traps",
                "Trap and Mine Damage",
                "Cluster Traps",
                "Swift Assembly",
                "Lightning Penetration",
            ],
            "guard": "Immortal Call",
            "aura_setup": [
                "Wrath",
                "Zealotry",
                "Herald of Thunder",
            ],
            "mobility": "Flame Dash",
        },
        "gear": {
            "weapon": "Spell dagger with +1 to lightning spells and crit multi.",
            "armour": "Energy shield gear with eldritch implicits for trap throwing speed.",
            "jewels": "Rare jewels with trap damage, crit multi, and life."
        },
        "progression": {
            "leveling": (
                "Use Explosive Trap from level 1, swap to Lightning Trap at level 12, and "
                "rush trap throwing speed on the tree."
            ),
            "early_endgame": (
                "Secure Tremor Rod or crafted wand/dagger plus shield for double trap setup."
            ),
            "endgame": (
                "Invest into crit multi jewels, elevated shock effect boots, and Eldritch "
                "altars for maximum scaling."
            ),
        },
    },
]

__all__ = ["BUILD_LIBRARY", "Build"]
