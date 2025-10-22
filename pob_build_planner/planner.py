"""Recommendation logic for Path of Building build selection."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from .data import BUILD_LIBRARY, Build
from .pob import build_to_code


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


@dataclass
class BuildRecommendation:
    build: Build
    score: int
    matched_tags: Dict[str, Sequence[str]]

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
        lines.append(f"PoB Import Code: {build_to_code(build)}")
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


__all__ = [
    "PlaystylePreferences",
    "BuildRecommendation",
    "recommend_builds",
    "get_build_by_id",
]
