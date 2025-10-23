"""Recommendation logic for Path of Building build selection."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import re

from .data import BUILD_LIBRARY, Build
from .pob import build_to_code, build_to_pobb_in_url

FREEFORM_SINGLE_VALUE_KEYWORDS = {
    "melee": ("combat_range", "melee"),
    "ranged": ("combat_range", "ranged"),
    "aoe": ("combat_range", "aoe"),
    "attack": ("damage_source", "attack"),
    "attacker": ("damage_source", "attack"),
    "dagger": ("damage_source", "attack"),
    "daggers": ("damage_source", "attack"),
    "fast attacker": ("damage_source", "attack"),
    "caster": ("damage_source", "spell"),
    "spell": ("damage_source", "spell"),
    "spells": ("damage_source", "spell"),
    "minion": ("damage_source", "minion"),
    "summoner": ("damage_source", "minion"),
    "trapper": ("damage_source", "trap"),
    "trap": ("damage_source", "trap"),
    "dot": ("damage_source", "damage_over_time"),
    "damage over time": ("damage_source", "damage_over_time"),
    "physical": ("damage_type", "physical"),
    "fire": ("damage_type", "fire"),
    "cold": ("damage_type", "elemental"),
    "lightning": ("damage_type", "lightning"),
    "elemental": ("damage_type", "elemental"),
    "chaos": ("damage_type", "chaos"),
    "poison": ("damage_type", "chaos"),
    "budget": ("budget", "medium"),
    "cheap": ("budget", "low"),
    "starter": ("budget", "league_start"),
    "league start": ("budget", "league_start"),
    "expensive": ("budget", "high"),
    "high budget": ("budget", "high"),
    "medium budget": ("budget", "medium"),
    "simple": ("complexity", "low"),
    "easy": ("complexity", "low"),
    "complex": ("complexity", "high"),
    "advanced": ("complexity", "high"),
}

FREEFORM_BOOLEAN_KEYWORDS = {
    "league start": ("league_start", True),
    "league starter": ("league_start", True),
    "starter": ("league_start", True),
    "ssf": ("league_start", True),
    "hardcore": ("league_start", True),
    "endgame": ("league_start", False),
    "fast": ("mobility_priority", True),
    "speedy": ("mobility_priority", True),
    "mobile": ("mobility_priority", True),
    "slow": ("mobility_priority", False),
}

FREEFORM_MULTI_VALUE_KEYWORDS = {
    "mapping": ("content_focus", "mapping"),
    "maps": ("content_focus", "mapping"),
    "boss": ("content_focus", "bossing"),
    "bossing": ("content_focus", "bossing"),
    "delve": ("content_focus", "delve"),
    "juiced": ("content_focus", "juiced_mapping"),
    "juiced maps": ("content_focus", "juiced_mapping"),
    "tanky": ("defense_layers", "armour"),
    "armour": ("defense_layers", "armour"),
    "armor": ("defense_layers", "armour"),
    "block": ("defense_layers", "block"),
    "regen": ("defense_layers", "life_regen"),
    "life regen": ("defense_layers", "life_regen"),
    "leech": ("defense_layers", "life_leech"),
    "fortify": ("defense_layers", "fortify"),
    "suppression": ("defense_layers", "spell_suppression"),
    "supp": ("defense_layers", "spell_suppression"),
    "evasion": ("defense_layers", "evasion"),
    "avoidance": ("defense_layers", "ailment_avoidance"),
}

FREEFORM_PHRASES = [
    ("fast attacker", {"damage_source": "attack", "mobility_priority": True}),
    ("league starter", {"league_start": True, "budget": "league_start"}),
    ("league start", {"league_start": True, "budget": "league_start"}),
    ("endgame", {"budget": "high"}),
    (
        "tanky",
        {
            "defense_layers": ["armour", "block", "life_regen"],
        },
    ),
]


def _normalise(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    return value.strip().lower() or None


def _normalise_iterable(values: Optional[Iterable[str]]) -> List[str]:
    if not values:
        return []
    return sorted({_normalise(v) for v in values if _normalise(v)})


@dataclass
class PlaystylePreferences:
    """Structured representation of a player's desired playstyle."""

    damage_type: Optional[str] = None
    combat_range: Optional[str] = None
    damage_source: Optional[str] = None
    complexity: Optional[str] = None
    budget: Optional[str] = None
    league_start: Optional[bool] = None
    content_focus: List[str] = field(default_factory=list)
    defense_layers: List[str] = field(default_factory=list)
    mobility_priority: Optional[bool] = None

    @classmethod
    def from_dict(cls, data: Dict[str, object]) -> "PlaystylePreferences":
        return cls(
            damage_type=_normalise(data.get("damage_type")) if data else None,
            combat_range=_normalise(data.get("combat_range")) if data else None,
            damage_source=_normalise(data.get("damage_source")) if data else None,
            complexity=_normalise(data.get("complexity")) if data else None,
            budget=_normalise(data.get("budget")) if data else None,
            league_start=data.get("league_start") if data else None,
            content_focus=_normalise_iterable(data.get("content_focus")),
            defense_layers=_normalise_iterable(data.get("defense_layers")),
            mobility_priority=data.get("mobility_priority") if data else None,
        )


def _tokenise_description(description: str) -> List[str]:
    tokens = []
    lowered = description.lower()
    for phrase, _ in FREEFORM_PHRASES:
        if phrase in lowered:
            tokens.append(phrase)
    tokens.extend(re.split(r"[\s,;\n]+", lowered))
    return [token for token in tokens if token]


def parse_freeform_preferences(description: str) -> Dict[str, object]:
    """Convert a free-form description into playstyle preference hints."""

    preferences: Dict[str, object] = {
        "content_focus": set(),
        "defense_layers": set(),
    }

    lowered = description.lower()
    for phrase, updates in FREEFORM_PHRASES:
        if phrase in lowered:
            for key, value in updates.items():
                if key in {"content_focus", "defense_layers"}:
                    preferences.setdefault(key, set())
                    preferences[key].update(value)
                else:
                    preferences[key] = value

    tokens = _tokenise_description(description)
    for token in tokens:
        if token in FREEFORM_SINGLE_VALUE_KEYWORDS:
            key, value = FREEFORM_SINGLE_VALUE_KEYWORDS[token]
            preferences[key] = value
        if token in FREEFORM_BOOLEAN_KEYWORDS:
            key, value = FREEFORM_BOOLEAN_KEYWORDS[token]
            preferences[key] = value
        if token in FREEFORM_MULTI_VALUE_KEYWORDS:
            key, value = FREEFORM_MULTI_VALUE_KEYWORDS[token]
            preferences.setdefault(key, set())
            preferences[key].add(value)

    if isinstance(preferences.get("content_focus"), set):
        preferences["content_focus"] = sorted(preferences["content_focus"])
    if isinstance(preferences.get("defense_layers"), set):
        preferences["defense_layers"] = sorted(preferences["defense_layers"])

    return preferences


def playstyle_from_description(description: str) -> PlaystylePreferences:
    """Create a PlaystylePreferences object from a free-form description."""

    return PlaystylePreferences.from_dict(parse_freeform_preferences(description))


@dataclass
class BuildRecommendation:
    build: Build
    score: int
    matched_tags: Dict[str, Sequence[str]]
    _pob_code_cache: Optional[str] = field(default=None, init=False, repr=False)

    def pob_code(self) -> str:
        if not self._pob_code_cache:
            self._pob_code_cache = build_to_code(self.build)
        return self._pob_code_cache

    def pob_link(self) -> str:
        return build_to_pobb_in_url(self.build)

    def to_payload(self) -> Dict[str, object]:
        build = self.build
        payload: Dict[str, object] = {
            "id": build.get("id", ""),
            "name": build.get("name", ""),
            "score": self.score,
            "matched_tags": self.matched_tags,
            "ascendancy": build.get("ascendancy", ""),
            "summary": build.get("summary", ""),
            "core_passives": build.get("core_passives", []),
            "skill_gems": build.get("skill_gems", {}),
            "gear": build.get("gear", {}),
            "progression": build.get("progression", {}),
            "pob_code": self.pob_code(),
            "pobb_in_url": self.pob_link(),
        }
        return payload

    def to_report(self) -> str:
        build = self.build
        lines: List[str] = []
        lines.append(f"Recommended build: {build['name']} (Score: {self.score})")
        lines.append(build["summary"])  # type: ignore[index]
        lines.append("")
        lines.append(f"Ascendancy: {build['ascendancy']}")
        if self.matched_tags:
            pairs = [
                f"{attr.replace('_', ' ').title()}: {', '.join(sorted(map(str, values)))}"
                for attr, values in self.matched_tags.items()
            ]
            lines.append("Matched Preferences -> " + "; ".join(pairs))
            lines.append("")
        lines.append("Core Passive Highlights:")
        for point in build.get("core_passives", []):
            lines.append(f"  • {point}")
        if build.get("skill_gems"):
            lines.append("")
            lines.append("Skill Gem Setup:")
            skill_gems = build["skill_gems"]  # type: ignore[assignment]
            if skill_gems.get("main_skill"):
                lines.append(f"  Main Skill: {skill_gems['main_skill']}")
            if skill_gems.get("six_link"):
                lines.append("  Six-Link:")
                for gem in skill_gems["six_link"]:
                    lines.append(f"    - {gem}")
            for key in ("secondary_skill", "guard", "aura_setup", "mobility"):
                if key in skill_gems:
                    value = skill_gems[key]
                    if isinstance(value, list):
                        pretty = ", ".join(value)
                    else:
                        pretty = str(value)
                    lines.append(f"  {key.replace('_', ' ').title()}: {pretty}")
        if build.get("gear"):
            lines.append("")
            lines.append("Gear Priorities:")
            for slot, desc in build["gear"].items():
                lines.append(f"  {slot.title()}: {desc}")
        if build.get("progression"):
            lines.append("")
            lines.append("Progression Tips:")
            for stage, guidance in build["progression"].items():
                lines.append(f"  {stage.replace('_', ' ').title()}: {guidance}")
        lines.append("")
        code = self.pob_code()
        lines.append(f"PoB Import Code: {code}")
        lines.append(f"PoB Link: {build_to_pobb_in_url(self.build)}")
        return "\n".join(lines)


def score_build(preferences: PlaystylePreferences, build: Build) -> Tuple[int, Dict[str, Sequence[str]]]:
    tags = build.get("tags", {})
    matched: Dict[str, Sequence[str]] = {}
    score = 0

    def add_if_match(attr: str, value: Optional[str]) -> None:
        nonlocal score
        if not value:
            return
        pool = tags.get(attr)
        if not pool:
            return
        if isinstance(pool, list):
            if value in {str(v).lower() for v in pool}:
                score += 10
                matched[attr] = [value]
        else:
            if isinstance(pool, bool):
                if bool(pool) == (value == "true"):
                    score += 5
                    matched[attr] = [str(pool)]
            elif isinstance(pool, str) and value == pool.lower():
                score += 10
                matched[attr] = [pool]

    add_if_match("damage_type", preferences.damage_type)
    add_if_match("combat_range", preferences.combat_range)
    add_if_match("damage_source", preferences.damage_source)
    add_if_match("complexity", preferences.complexity)
    add_if_match("budget", preferences.budget)

    if preferences.league_start is not None:
        if bool(tags.get("league_start")) == preferences.league_start:
            score += 6
            matched["league_start"] = ["yes" if preferences.league_start else "no"]

    if preferences.mobility_priority is not None:
        if bool(tags.get("mobility")) == preferences.mobility_priority:
            score += 4
            matched["mobility"] = ["yes" if preferences.mobility_priority else "no"]

    if preferences.content_focus:
        build_content = {str(v).lower() for v in tags.get("content", [])}
        shared = sorted(build_content.intersection(preferences.content_focus))
        if shared:
            score += 3 * len(shared)
            matched["content"] = shared

    if preferences.defense_layers:
        build_layers = {str(v).lower() for v in tags.get("defense_layers", [])}
        shared = sorted(build_layers.intersection(preferences.defense_layers))
        if shared:
            score += 2 * len(shared)
            matched["defense_layers"] = shared

    return score, matched


def recommend_builds(
    preferences: PlaystylePreferences,
    *,
    library: Sequence[Build] = BUILD_LIBRARY,
    top_n: int = 3,
    min_score: int = 5,
) -> List[BuildRecommendation]:
    """Return the best build matches for a set of preferences."""

    scored: List[BuildRecommendation] = []
    for build in library:
        score, matched = score_build(preferences, build)
        if score >= min_score:
            scored.append(BuildRecommendation(build=build, score=score, matched_tags=matched))
    scored.sort(key=lambda rec: rec.score, reverse=True)
    return scored[:top_n]


def get_build_by_id(build_id: str, *, library: Sequence[Build] = BUILD_LIBRARY) -> Optional[BuildRecommendation]:
    build_id = build_id.strip().lower()
    for build in library:
        if build.get("id") == build_id:
            score, matched = score_build(PlaystylePreferences(), build)
            return BuildRecommendation(build=build, score=score, matched_tags=matched)
    return None


@dataclass
class DualPhasePlan:
    """Encapsulates league start and endgame recommendations."""

    league_start: Optional[BuildRecommendation]
    endgame: Optional[BuildRecommendation]

    def to_payload(self) -> Dict[str, Optional[Dict[str, object]]]:
        return {
            "league_start": self.league_start.to_payload() if self.league_start else None,
            "endgame": self.endgame.to_payload() if self.endgame else None,
        }

    def to_report(self) -> str:
        lines: List[str] = []
        if self.league_start:
            lines.append("===== League Start Recommendation =====")
            lines.append(self.league_start.to_report())
        else:
            lines.append("No league start recommendation matched your filters.")
        if self.endgame:
            if lines:
                lines.append("\n")
            lines.append("===== Endgame Recommendation =====")
            lines.append(self.endgame.to_report())
        else:
            if lines:
                lines.append("\n")
            lines.append("No endgame recommendation matched your filters.")
        return "\n".join(lines)


def recommend_dual_phase_builds(
    preferences: PlaystylePreferences,
    *,
    library: Sequence[Build] = BUILD_LIBRARY,
    top_n: int = 3,
    min_score: int = 5,
) -> DualPhasePlan:
    """Return a pair of builds targeting league start and endgame goals."""

    def _recommend_subset(candidates: Sequence[Build]) -> List[BuildRecommendation]:
        if not candidates:
            candidates = library
        recs = recommend_builds(
            preferences,
            library=candidates,
            top_n=max(top_n, 3),
            min_score=min_score,
        )
        if not recs and min_score > 0:
            recs = recommend_builds(
                preferences,
                library=candidates,
                top_n=max(top_n, 3),
                min_score=0,
            )
        return recs

    league_candidates = [
        build
        for build in library
        if bool(build.get("tags", {}).get("league_start"))
    ]
    league_recommendations = _recommend_subset(league_candidates)
    league_choice = league_recommendations[0] if league_recommendations else None

    endgame_candidates: List[Build] = []
    for build in library:
        tags = build.get("tags", {})
        budgets = {str(v).lower() for v in tags.get("budget", [])}
        if "high" in budgets or not bool(tags.get("league_start")):
            endgame_candidates.append(build)
    endgame_recommendations = _recommend_subset(endgame_candidates)

    endgame_choice: Optional[BuildRecommendation] = None
    if league_choice:
        for rec in endgame_recommendations:
            if rec.build.get("id") != league_choice.build.get("id"):
                endgame_choice = rec
                break
    if not endgame_choice and endgame_recommendations:
        endgame_choice = endgame_recommendations[0]

    return DualPhasePlan(league_start=league_choice, endgame=endgame_choice)


__all__ = [
    "PlaystylePreferences",
    "BuildRecommendation",
    "DualPhasePlan",
    "recommend_builds",
    "recommend_dual_phase_builds",
    "get_build_by_id",
]
