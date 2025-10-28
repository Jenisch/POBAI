"""Generate Path of Building build dictionaries on demand.

The planner originally focused on matching against a curated library of
hand-authored builds.  Some users, however, want to jump straight to a fresh
Path of Building profile for a specific skill gem even when no pre-built plan
exists.  This module produces reasonable starting points by combining
lightweight heuristics with optional PoEDB metadata so the CLI can always emit
a PoB import code and pobb.in link for arbitrary skills.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Dict, Iterable, List, Mapping, MutableMapping, Optional

from .data import Build


def _normalise(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "generated-build"


def _as_list(value: object) -> List[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, Iterable):
        return [str(item) for item in value if str(item)]
    return []


def _merge_lists(*values: Iterable[str]) -> List[str]:
    merged: List[str] = []
    for value in values:
        for item in value:
            if item and item not in merged:
                merged.append(item)
    return merged


def _metadata_for_skill(
    skill: str, metadata: Optional[Mapping[str, Mapping[str, object]]]
) -> Mapping[str, object]:
    if not metadata:
        return {}
    key = _normalise(skill)
    if not key:
        return {}
    return metadata.get(key, {})


def _skill_name_contains(skill: str, *keywords: str) -> bool:
    lowered = skill.lower()
    return any(keyword in lowered for keyword in keywords)


@dataclass(frozen=True)
class ArchetypePlan:
    """Recipe for producing a generated build."""

    key: str
    ascendancy: str
    summary_template: str
    support_gems: List[str]
    guard_gem: str
    aura_setup: List[str]
    mobility: str
    core_passives: List[str]
    gear: Dict[str, str]
    progression: Dict[str, str]
    tags: Dict[str, object]

    def instantiate(
        self, skill: str, *, metadata: Mapping[str, object]
    ) -> MutableMapping[str, object]:
        ascendancy = self.ascendancy
        ascendancy_title = ascendancy.split(" - ")[-1]
        six_link = [skill] + [gem for gem in self.support_gems if gem]

        base_tags: Dict[str, object] = {
            key: (list(value) if isinstance(value, list) else value)
            for key, value in self.tags.items()
        }

        def _merge_tag(key: str, values: Iterable[str]) -> None:
            existing = _as_list(base_tags.get(key))
            merged = _merge_lists(existing, values)
            if merged:
                base_tags[key] = merged

        metadata_lists = {
            "damage_type": _as_list(metadata.get("damage_type")),
            "damage_source": _as_list(metadata.get("damage_source")),
            "combat_range": _as_list(metadata.get("combat_range")),
            "skill_tags": _as_list(metadata.get("skill_tags")),
        }
        for key, values in metadata_lists.items():
            if values:
                _merge_tag(key, values)

        summary = self.summary_template.format(
            skill=skill,
            ascendancy=ascendancy,
            ascendancy_title=ascendancy_title,
        )

        build: MutableMapping[str, object] = {
            "id": _slugify(f"{skill}-{ascendancy_title}-{self.key}"),
            "name": f"{skill} {ascendancy_title}",
            "summary": summary,
            "ascendancy": ascendancy,
            "level": 92,
            "tags": base_tags,
            "core_passives": list(self.core_passives),
            "skill_gems": {
                "main_skill": skill,
                "six_link": six_link,
                "guard": self.guard_gem,
                "aura_setup": list(self.aura_setup),
                "mobility": self.mobility,
            },
            "gear": dict(self.gear),
            "progression": dict(self.progression),
        }
        return build


ARCHETYPES: List[ArchetypePlan] = [
    ArchetypePlan(
        key="wand_projectile",
        ascendancy="Ranger - Deadeye",
        summary_template=(
            "A {skill} Deadeye that leverages projectile chaining, wand damage, and "
            "evasion stacking for effortless clear and solid single-target damage."
        ),
        support_gems=[
            "Greater Multiple Projectiles Support",
            "Inspiration Support",
            "Elemental Damage with Attacks Support",
            "Increased Critical Strikes Support",
            "Power Charge On Critical Support",
        ],
        guard_gem="Steelskin",
        aura_setup=["Grace", "Determination", "Herald of Ice"],
        mobility="Dash + Flame Dash",
        core_passives=[
            "Take Gathering Winds into Endless Munitions for projectile speed and additional projectiles.",
            "Scale wand damage via Wand Mastery and spell suppression clusters on the right side of the tree.",
            "Invest into spell suppression and evasion wheels to stay safe while clearing.",
        ],
        gear={
            "weapon": "High attack speed wand with added elemental damage and critical strike chance.",
            "armour": "Evasion gear with spell suppression, life, and elemental resistances.",
            "jewels": "Crit multi and projectile damage rare jewels; consider Thread of Hope near Fervour.",
        },
        progression={
            "leveling": "Level with Power Siphon or Frost Blades until Kinetic Blast is available, then equip wands with added elemental damage.",
            "early_endgame": "Transition into a six-link Kinetic Blast, cap spell suppression, and acquire a Blast-Freeze or Heatshiver helmet.",
            "endgame": "Craft elevated wands with +2 projectiles, invest in Awakened support gems, and upgrade to Inspired Learning or Headhunter for mapping.",
        },
        tags={
            "damage_type": ["elemental"],
            "damage_source": ["attack"],
            "combat_range": ["ranged"],
            "complexity": "medium",
            "budget": ["medium", "league_start"],
            "league_start": True,
            "content": ["mapping", "bossing"],
            "defense_layers": ["evasion", "spell_suppression", "ailment_avoidance"],
            "mobility": True,
        },
    ),
    ArchetypePlan(
        key="bow_chaos",
        ascendancy="Ranger - Pathfinder",
        summary_template=(
            "A {skill} Pathfinder that excels at damage over time scaling, flask uptime, "
            "and layered defences for bossing and mapping alike."
        ),
        support_gems=[
            "Mirage Archer Support",
            "Vicious Projectiles Support",
            "Void Manipulation Support",
            "Swift Affliction Support",
            "Empower Support",
        ],
        guard_gem="Steelskin",
        aura_setup=["Malevolence", "Grace", "Determination"],
        mobility="Dash + Flame Dash",
        core_passives=[
            "Take Nature's Reprisal and Master Toxicist for chaos damage over time scaling.",
            "Path to skill effect duration and chaos damage clusters to maximise pod overlap.",
            "Invest into flask effect, spell suppression, and ailment avoidance for survivability.",
        ],
        gear={
            "weapon": "+3 bow with chaos damage over time multiplier and attack speed.",
            "armour": "Evasion bases with spell suppression, life, and chaos resistance.",
            "jewels": "Malevolence Watcher's Eye, rare jewels with damage over time multiplier and life.",
        },
        progression={
            "leveling": "Use Caustic Arrow through the campaign, swapping to {skill} once gem levels allow.",
            "early_endgame": "Secure a +2 or +3 bow, cap spell suppression, and craft utility flasks with increased effect.",
            "endgame": "Add Empower Support, aim for Mageblood or Headhunter, and min-max Eldritch implicits for defense.",
        },
        tags={
            "damage_type": ["chaos"],
            "damage_source": ["attack"],
            "combat_range": ["ranged"],
            "complexity": "medium",
            "budget": ["low", "league_start"],
            "league_start": True,
            "content": ["mapping", "bossing"],
            "defense_layers": ["evasion", "spell_suppression", "ailment_avoidance"],
            "mobility": True,
        },
    ),
    ArchetypePlan(
        key="melee_physical",
        ascendancy="Duelist - Slayer",
        summary_template=(
            "A {skill} Slayer that leeches through incoming damage, scales two-handed physical DPS, "
            "and maintains Fortify for smooth mapping and bossing."
        ),
        support_gems=[
            "Brutality Support",
            "Impale Support",
            "Melee Physical Damage Support",
            "Fortify Support",
            "Close Combat Support",
        ],
        guard_gem="Molten Shell",
        aura_setup=["Pride", "Blood and Sand", "Flesh and Stone"],
        mobility="Leap Slam",
        core_passives=[
            "Take Headsman and Bane of Legends for cull, damage, and onslaught.",
            "Stack physical damage, impale effect, and leech nodes on the Duelist section of the tree.",
            "Use armour and Fortify effect nodes to stay durable in melee.",
        ],
        gear={
            "weapon": "High DPS two-handed weapon with attack speed and critical strike chance.",
            "armour": "Armour gear with life, resistances, and increased Fortify effect.",
            "jewels": "Watcher's Eye with Pride modifiers, rare jewels with attack speed and melee damage.",
        },
        progression={
            "leveling": "Level with ground-slam style skills, switching to {skill} when support gems become available.",
            "early_endgame": "Acquire a six-link chest, cap resistances, and craft a strong physical weapon.",
            "endgame": "Invest into elevated physical modifiers, double-influenced chests, and high-tier flasks.",
        },
        tags={
            "damage_type": ["physical"],
            "damage_source": ["attack"],
            "combat_range": ["melee"],
            "complexity": "low",
            "budget": ["medium", "league_start"],
            "league_start": True,
            "content": ["mapping", "bossing"],
            "defense_layers": ["armour", "life_leech", "fortify"],
            "mobility": True,
        },
    ),
    ArchetypePlan(
        key="spell_fire",
        ascendancy="Templar - Inquisitor",
        summary_template=(
            "A burning {skill} Inquisitor that stacks regeneration, exposure immunity, and crit to melt bosses while face-tanking maps."
        ),
        support_gems=[
            "Burning Damage Support",
            "Elemental Focus Support",
            "Efficacy Support",
            "Increased Area of Effect Support",
            "Swift Affliction Support",
        ],
        guard_gem="Molten Shell",
        aura_setup=["Determination", "Purity of Fire", "Vitality"],
        mobility="Shield Charge",
        core_passives=[
            "Take Sanctuary and Pious Path for consecrated ground uptime and ailment immunity.",
            "Invest into fire damage over time nodes and maximum fire resistance clusters.",
            "Use armour and regeneration gear to comfortably sustain the burn.",
        ],
        gear={
            "weapon": "Sceptre with fire damage over time multiplier and +1 to fire spell gems.",
            "armour": "Armour/energy shield bases with maximum fire resistance and regeneration.",
            "jewels": "Militant Faith timeless jewel plus rare damage over time multiplier jewels.",
        },
        progression={
            "leveling": "Campaign with Purifying Flame and Fire Trap, enabling {skill} when regeneration allows sustained burning.",
            "early_endgame": "Craft a +1 fire sceptre, obtain Legacy of Fury, and invest into reservation efficiency clusters.",
            "endgame": "Elevate helmets with +3 AoE, chase Inquisitor crit multi clusters, and optimise flasks for regen.",
        },
        tags={
            "damage_type": ["fire", "elemental"],
            "damage_source": ["spell", "damage_over_time"],
            "combat_range": ["aoe", "ranged"],
            "complexity": "medium",
            "budget": ["medium", "league_start"],
            "league_start": True,
            "content": ["mapping", "bossing"],
            "defense_layers": ["life_regen", "armour", "max_res"],
            "mobility": True,
        },
    ),
    ArchetypePlan(
        key="spell_lightning",
        ascendancy="Witch - Elementalist",
        summary_template=(
            "A {skill} Elementalist that leverages shock proliferation, golem buffs, and ailment immunity for high-voltage clearing."
        ),
        support_gems=[
            "Spell Echo Support",
            "Unleash Support",
            "Inspiration Support",
            "Lightning Penetration Support",
            "Increased Critical Strikes Support",
        ],
        guard_gem="Steelskin",
        aura_setup=["Wrath", "Zealotry", "Herald of Thunder"],
        mobility="Flame Dash",
        core_passives=[
            "Take Shaper of Storms and Heart of Destruction for shock effect and AoE.",
            "Invest into lightning penetration clusters and cast speed nodes.",
            "Use golems and Elementalist notables to gain ailment immunity and defensive layers.",
        ],
        gear={
            "weapon": "Lightning spell wand with +1 lightning gems, cast speed, and crit multi.",
            "armour": "Energy shield gear with spell suppression and elemental resistances.",
            "jewels": "Crit multi jewels, Watcher's Eye with Wrath mods, and medium lightning cluster jewels.",
        },
        progression={
            "leveling": "Level with Stormblast Mine or Arc, adding {skill} once cast speed nodes are allocated.",
            "early_endgame": "Secure a six-link chest, add Unleash, and craft wands with flat lightning damage.",
            "endgame": "Upgrade to elevated crit gear, cluster jewels, and Bottled Faith for maximum DPS.",
        },
        tags={
            "damage_type": ["lightning", "elemental"],
            "damage_source": ["spell"],
            "combat_range": ["ranged"],
            "complexity": "medium",
            "budget": ["medium", "league_start"],
            "league_start": True,
            "content": ["mapping", "bossing"],
            "defense_layers": ["spell_suppression", "ailment_avoidance", "energy_shield"],
            "mobility": True,
        },
    ),
    ArchetypePlan(
        key="spell_cold",
        ascendancy="Witch - Occultist",
        summary_template=(
            "A chilling {skill} Occultist that layers curses, cold exposure, and energy shield recovery for ruthless mapping and bossing."
        ),
        support_gems=[
            "Spell Echo Support",
            "Cold Penetration Support",
            "Hypothermia Support",
            "Controlled Destruction Support",
            "Arcane Surge Support",
        ],
        guard_gem="Steelskin",
        aura_setup=["Hatred", "Discipline", "Determination"],
        mobility="Flame Dash",
        core_passives=[
            "Take Frigid Wake and Void Beacon for cold damage, exposure, and defensive utility.",
            "Path through cold damage over time and curse effect wheels on the north side of the tree.",
            "Stack energy shield, chill effect, and block to stay safe while enemies are frozen."
        ],
        gear={
            "weapon": "+1 cold spell staff or wand with cold damage over time multiplier.",
            "armour": "Energy shield bases with spell suppression and elemental resistances.",
            "jewels": "Rare ES jewels, Forbidden Flesh/Flame for Vile Bastion, and medium cold cluster jewels.",
        },
        progression={
            "leveling": "Start with Freezing Pulse, switching to {skill} once gem and support levels unlock.",
            "early_endgame": "Secure a six-link, add curses via self-cast or automation, and cap cold exposure.",
            "endgame": "Upgrade to elevated ES gear, double curse rings, and watcher's eye with Discipline mods.",
        },
        tags={
            "damage_type": ["cold", "elemental"],
            "damage_source": ["spell"],
            "combat_range": ["ranged"],
            "complexity": "high",
            "budget": ["medium", "high"],
            "league_start": False,
            "content": ["mapping", "bossing"],
            "defense_layers": ["energy_shield", "block", "chill_effect"],
            "mobility": True,
        },
    ),
    ArchetypePlan(
        key="spell_chaos",
        ascendancy="Witch - Occultist",
        summary_template=(
            "A {skill} Occultist that scales chaos damage over time, profane bloom explosions, and layered curses for safe clear."
        ),
        support_gems=[
            "Efficacy Support",
            "Swift Affliction Support",
            "Void Manipulation Support",
            "Controlled Destruction Support",
            "Increased Area of Effect Support",
        ],
        guard_gem="Steelskin",
        aura_setup=["Malevolence", "Determination", "Discipline"],
        mobility="Flame Dash",
        core_passives=[
            "Take Profane Bloom and Malediction for explosions and curse effect.",
            "Stack chaos damage over time multiplier clusters like Method to the Madness.",
            "Invest into energy shield, suppress, and wither application for bossing.",
        ],
        gear={
            "weapon": "Wand or staff with +1 chaos gems and chaos damage over time multiplier.",
            "armour": "Energy shield bases with chaos resistance and spell suppression.",
            "jewels": "Unnatural Instinct near Shadow, Watcher's Eye with Malevolence mods, and rare DoT multi jewels.",
        },
        progression={
            "leveling": "Level with Essence Drain/Contagion, swapping to {skill} once the gem setup is available.",
            "early_endgame": "Acquire Wither totems or Spell Totems, craft chaos DoT gear, and secure a +1 chaos wand.",
            "endgame": "Chase elevated chaos bases, double curse rings, and cluster jewels for DoT multiplier.",
        },
        tags={
            "damage_type": ["chaos"],
            "damage_source": ["spell", "damage_over_time"],
            "combat_range": ["ranged"],
            "complexity": "medium",
            "budget": ["medium"],
            "league_start": True,
            "content": ["mapping", "bossing"],
            "defense_layers": ["energy_shield", "spell_suppression", "ailment_avoidance"],
            "mobility": True,
        },
    ),
    ArchetypePlan(
        key="minion",
        ascendancy="Witch - Necromancer",
        summary_template=(
            "A {skill} Necromancer that commands an army of minions, automates offerings, and layers block plus bone armour for safety."
        ),
        support_gems=[
            "Minion Damage Support",
            "Elemental Army Support",
            "Spell Echo Support",
            "Unleash Support",
            "Empower Support",
        ],
        guard_gem="Bone Offering",
        aura_setup=["Determination", "Defiance Banner", "Discipline"],
        mobility="Flame Dash",
        core_passives=[
            "Take Unnatural Strength and Bone Barrier to scale minion damage and defences.",
            "Invest into minion duration, life, and damage clusters across the Witch and Templar sectors.",
            "Use Glancing Blows plus block gear to stay safe while minions do the work.",
        ],
        gear={
            "weapon": "Trigger wand with +1 all spell skill gems and minion damage.",
            "armour": "Bone helmet with +2 minion gems, armour/ES bases with life and resistances.",
            "jewels": "Ghastly Eye jewels with minion life, damage, and blind/taunt chance.",
        },
        progression={
            "leveling": "Level with Absolution or Summon Raging Spirit until {skill} is online, grabbing minion damage nodes early.",
            "early_endgame": "Craft a trigger wand, automate Offering, and secure a bone helmet with minion levels.",
            "endgame": "Invest into cluster jewels, primordial jewels, and +2 minion gem gear for scaling.",
        },
        tags={
            "damage_source": ["minion"],
            "combat_range": ["ranged"],
            "complexity": "low",
            "budget": ["low", "league_start"],
            "league_start": True,
            "content": ["mapping", "bossing"],
            "defense_layers": ["block", "minion_taunt", "life_regen"],
            "mobility": False,
        },
    ),
    ArchetypePlan(
        key="trap",
        ascendancy="Shadow - Saboteur",
        summary_template=(
            "A {skill} Saboteur that leverages trap cooldown recovery, chain reactions, and blind proliferation for safe damage from range."
        ),
        support_gems=[
            "Advanced Traps Support",
            "Trap and Mine Damage Support",
            "Swift Assembly Support",
            "Cluster Traps Support",
            "Charged Traps Support",
        ],
        guard_gem="Immortal Call",
        aura_setup=["Grace", "Determination", "Herald of Thunder"],
        mobility="Flame Dash",
        core_passives=[
            "Take Perfect Crime and Chain Reaction for trap chaining and cooldown recovery.",
            "Invest into trap throwing speed, crit scaling, and elemental penetration where appropriate.",
            "Use blind and ailment avoidance layers from Saboteur ascendancy for defence.",
        ],
        gear={
            "weapon": "Spell dagger or wand with spell damage, crit multi, and trap throwing speed.",
            "armour": "Evasion/energy shield gear with spell suppression and life.",
            "jewels": "Trap damage jewels, crit multi, and life; consider Saboteur cluster jewels.",
        },
        progression={
            "leveling": "Use Explosive Trap early then graduate into {skill} once traps scale well with supports.",
            "early_endgame": "Acquire Tremor Rod or crafted trap weapons, automate guard skills, and cap suppression.",
            "endgame": "Stack crit multi, elevated trap damage gear, and medium cluster jewels for trap damage.",
        },
        tags={
            "damage_source": ["trap"],
            "combat_range": ["ranged"],
            "complexity": "high",
            "budget": ["medium"],
            "league_start": True,
            "content": ["bossing", "mapping"],
            "defense_layers": ["evasion", "blind", "ailment_avoidance"],
            "mobility": True,
        },
    ),
    ArchetypePlan(
        key="totem",
        ascendancy="Templar - Hierophant",
        summary_template=(
            "A {skill} Hierophant that fields multiple totems, layers mana-based defences, and clears from a safe distance."
        ),
        support_gems=[
            "Spell Totem Support",
            "Multiple Totems Support",
            "Increased Critical Strikes Support",
            "Controlled Destruction Support",
            "Inspiration Support",
        ],
        guard_gem="Steelskin",
        aura_setup=["Wrath", "Determination", "Clarity"],
        mobility="Flame Dash",
        core_passives=[
            "Take Pursuit of Faith and Ritual of Awakening for extra totems and mana regen.",
            "Invest into totem damage and cast speed clusters near the Templar start.",
            "Use Mind over Matter and mana reservation efficiency for layered defence.",
        ],
        gear={
            "weapon": "Wand or sceptre with +1 to spell skill gems and cast speed.",
            "armour": "Hybrid armour/ES with mana, life, and resistances.",
            "jewels": "Totem damage jewels, rare mana multi jewels, and a Self-Flagellation for extra curse effect if applicable.",
        },
        progression={
            "leveling": "Level with Holy Flame Totem or Freezing Pulse totems, adopting {skill} once supports unlock.",
            "early_endgame": "Secure a soul mantle setup or crafted +1 totem shields, and cap resistances.",
            "endgame": "Invest into awakened support gems, multiple totem medium clusters, and transfigured gem variants.",
        },
        tags={
            "damage_source": ["spell"],
            "combat_range": ["ranged"],
            "complexity": "medium",
            "budget": ["medium", "league_start"],
            "league_start": True,
            "content": ["bossing", "mapping"],
            "defense_layers": ["mind_over_matter", "block", "mana_regen"],
            "mobility": False,
        },
    ),
]


def _select_archetype(skill: str, metadata: Mapping[str, object]) -> ArchetypePlan:
    tags = {str(tag).lower() for tag in _as_list(metadata.get("skill_tags"))}
    damage_source = str(metadata.get("damage_source", "")).lower()
    damage_type = str(metadata.get("damage_type", "")).lower()
    combat_range = str(metadata.get("combat_range", "")).lower()

    if "minion" in tags or damage_source == "minion" or _skill_name_contains(skill, "animate", "summon"):
        return next(plan for plan in ARCHETYPES if plan.key == "minion")
    if any(tag in tags for tag in {"trap", "mine"}) or damage_source == "trap":
        return next(plan for plan in ARCHETYPES if plan.key == "trap")
    if "totem" in tags or _skill_name_contains(skill, "totem"):
        return next(plan for plan in ARCHETYPES if plan.key == "totem")
    if "bow" in tags:
        if damage_type == "chaos" or "chaos" in tags:
            return next(plan for plan in ARCHETYPES if plan.key == "bow_chaos")
        return next(plan for plan in ARCHETYPES if plan.key == "wand_projectile")
    if "wand" in tags or _skill_name_contains(skill, "wand", "kinetic"):
        return next(plan for plan in ARCHETYPES if plan.key == "wand_projectile")
    if _skill_name_contains(skill, "summon", "animate", "minion", "golem", "skeleton", "zombie"):
        return next(plan for plan in ARCHETYPES if plan.key == "minion")
    if _skill_name_contains(skill, "trap", "mine"):
        return next(plan for plan in ARCHETYPES if plan.key == "trap")
    if _skill_name_contains(skill, "totem"):
        return next(plan for plan in ARCHETYPES if plan.key == "totem")
    if _skill_name_contains(skill, "arrow", "shot", "blast"):
        if _skill_name_contains(skill, "toxic", "chaos", "dark"):
            return next(plan for plan in ARCHETYPES if plan.key == "bow_chaos")
        return next(plan for plan in ARCHETYPES if plan.key == "wand_projectile")
    if _skill_name_contains(skill, "slam", "strike", "cleave", "bash", "blow", "leap"):
        return next(plan for plan in ARCHETYPES if plan.key == "melee_physical")
    if damage_source == "attack" and (combat_range == "melee" or "melee" in tags):
        return next(plan for plan in ARCHETYPES if plan.key == "melee_physical")
    if damage_source == "spell":
        if damage_type == "fire":
            return next(plan for plan in ARCHETYPES if plan.key == "spell_fire")
        if damage_type == "lightning":
            return next(plan for plan in ARCHETYPES if plan.key == "spell_lightning")
        if damage_type == "cold":
            return next(plan for plan in ARCHETYPES if plan.key == "spell_cold")
        if damage_type == "chaos":
            return next(plan for plan in ARCHETYPES if plan.key == "spell_chaos")
    if _skill_name_contains(skill, "fire", "flame", "ignite", "burn"):
        return next(plan for plan in ARCHETYPES if plan.key == "spell_fire")
    if _skill_name_contains(skill, "storm", "lightning", "spark", "arc", "shock"):
        return next(plan for plan in ARCHETYPES if plan.key == "spell_lightning")
    if _skill_name_contains(skill, "cold", "ice", "frost", "glacial"):
        return next(plan for plan in ARCHETYPES if plan.key == "spell_cold")
    if _skill_name_contains(skill, "chaos", "toxic", "poison", "essence", "bane"):
        return next(plan for plan in ARCHETYPES if plan.key == "spell_chaos")
    if "chaos" in tags and damage_source in {"spell", "", None}:
        return next(plan for plan in ARCHETYPES if plan.key == "spell_chaos")
    if damage_source == "attack":
        if damage_type == "chaos":
            return next(plan for plan in ARCHETYPES if plan.key == "bow_chaos")
        return next(plan for plan in ARCHETYPES if plan.key == "melee_physical")
    return next(plan for plan in ARCHETYPES if plan.key == "spell_lightning")


def generate_build_for_skill(
    skill: str,
    *,
    poedb_metadata: Optional[Mapping[str, Mapping[str, object]]] = None,
) -> Build:
    """Create a fresh build dictionary tailored to the requested skill."""

    skill_name = skill.strip()
    if not skill_name:
        raise ValueError("Skill name must be provided to generate a build")

    metadata = dict(_metadata_for_skill(skill_name, poedb_metadata))
    archetype = _select_archetype(skill_name, metadata)
    build = archetype.instantiate(skill_name, metadata=metadata)
    return build


__all__ = ["generate_build_for_skill"]

