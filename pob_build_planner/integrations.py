"""Utilities for augmenting the planner with external data sources."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Dict, Iterable, Iterator, List, Mapping, MutableMapping, Optional
import xml.etree.ElementTree as ET

Build = MutableMapping[str, object]


def _normalise(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "pob_build"


def _as_iterable(value: object) -> Iterable[object]:
    if isinstance(value, dict):
        return [key for key, flag in value.items() if flag]
    if isinstance(value, (list, tuple, set)):
        return value
    if value is None:
        return []
    return [value]


def _extract_skill_tags(entry: Mapping[str, object]) -> Dict[str, object]:
    """Translate PoEDB style metadata into planner tags."""

    tags = {str(value).lower() for value in _as_iterable(entry.get("tags"))}
    tags.update(str(value).lower() for value in _as_iterable(entry.get("type")))
    tags.update(str(value).lower() for value in _as_iterable(entry.get("types")))
    tags.update(str(value).lower() for value in _as_iterable(entry.get("skillTypes")))
    tags.update(str(value).lower() for value in _as_iterable(entry.get("SkillTypes")))
    tags.update(str(value).lower() for value in _as_iterable(entry.get("Keywords")))

    meta: Dict[str, object] = {
        "skill_tags": sorted(tags),
    }

    if any(key in tags for key in {"attack", "bow", "projectile", "melee"}):
        meta["damage_source"] = "attack"
    if any(key in tags for key in {"spell", "spell_damage", "channelling", "channeling"}):
        meta["damage_source"] = "spell"
    if any(key in tags for key in {"minion", "summon", "golem"}):
        meta["damage_source"] = "minion"
    if any(key in tags for key in {"trap", "mine"}):
        meta["damage_source"] = "trap"

    if any(key in tags for key in {"melee"}):
        meta["combat_range"] = "melee"
    if any(key in tags for key in {"bow", "projectile", "spell"}):
        meta.setdefault("combat_range", "ranged")

    if "chaos" in tags or "poison" in tags:
        meta["damage_type"] = "chaos"
    elif "fire" in tags or "burning" in tags:
        meta["damage_type"] = "fire"
    elif "cold" in tags or "ice" in tags:
        meta["damage_type"] = "cold"
    elif "lightning" in tags or "shock" in tags:
        meta["damage_type"] = "lightning"

    return meta


def _iter_skill_entries(data: object) -> Iterator[Mapping[str, object]]:
    if isinstance(data, list):
        for entry in data:
            if isinstance(entry, dict):
                yield entry
    elif isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, dict):
                entry = dict(value)
                entry.setdefault("name", key)
                yield entry


def load_poedb_metadata(root: Optional[str]) -> Dict[str, Dict[str, object]]:
    """Return skill metadata keyed by normalised skill names."""

    if not root:
        return {}

    base = Path(root)
    if not base.exists():
        return {}

    metadata: Dict[str, Dict[str, object]] = {}
    patterns = [
        "*.json",
        "*.min.json",
        "*ActiveSkill*.json",
        "*SkillGem*.json",
    ]
    for pattern in patterns:
        for candidate in base.rglob(pattern):
            try:
                with candidate.open("r", encoding="utf8") as handle:
                    payload = json.load(handle)
            except Exception:
                continue
            for entry in _iter_skill_entries(payload):
                name = entry.get("name") or entry.get("Name")
                if not isinstance(name, str):
                    continue
                normalised = _normalise(name)
                if not normalised:
                    continue
                metadata[normalised] = _extract_skill_tags(entry)
    return metadata


def _guess_default_tags(ascendancy: str, skill: str) -> Dict[str, object]:
    ascendancy_lower = ascendancy.lower()
    skill_lower = skill.lower()

    tags: Dict[str, object] = {
        "content": ["mapping", "bossing"],
        "budget": ["medium", "league_start"],
        "league_start": True,
        "mobility": True,
    }

    if any(keyword in skill_lower for keyword in {"totem", "summon", "minion", "animate"}):
        tags["damage_source"] = "minion"
    elif "trap" in skill_lower or "mine" in skill_lower:
        tags["damage_source"] = "trap"
    elif any(keyword in ascendancy_lower for keyword in {"elementalist", "occultist", "hierophant", "inquisitor", "trickster"}):
        tags["damage_source"] = "spell"
    else:
        tags["damage_source"] = "attack"

    if any(keyword in ascendancy_lower for keyword in {"deadeye", "pathfinder", "occultist", "elementalist", "saboteur"}):
        tags["combat_range"] = "ranged"
    else:
        tags["combat_range"] = "melee"

    if any(keyword in skill_lower for keyword in {"chaos", "toxic", "poison", "essence", "dark"}):
        tags["damage_type"] = "chaos"
    elif any(keyword in skill_lower for keyword in {"fire", "inferno", "flame", "molten"}):
        tags["damage_type"] = "fire"
    elif any(keyword in skill_lower for keyword in {"ice", "cold", "frost"}):
        tags["damage_type"] = "cold"
    elif any(keyword in skill_lower for keyword in {"lightning", "storm", "spark", "arc"}):
        tags["damage_type"] = "lightning"
    else:
        tags.setdefault("damage_type", "physical")

    return tags


def _extract_skill_group(skills_elem: Optional[ET.Element]) -> tuple[str, List[str]]:
    if skills_elem is None:
        return "", []

    for skill_elem in skills_elem.findall("Skill"):
        gems = []
        active_gem = ""
        for gem_elem in skill_elem.findall("Gem"):
            name = gem_elem.get("nameSpec") or gem_elem.get("skillId") or ""
            if not name:
                continue
            gems.append(name)
            gem_id = gem_elem.get("gemId", "")
            skill_id = gem_elem.get("skillId", "")
            if active_gem:
                continue
            if "support" in gem_id.lower() or "support" in skill_id.lower():
                continue
            active_gem = name
        if gems:
            return active_gem or gems[0], gems
    return "", []


def load_path_of_building_builds(
    repository_root: Optional[str],
    *,
    poedb_metadata: Optional[Mapping[str, Mapping[str, object]]] = None,
) -> List[Build]:
    """Parse Path of Building XML files into planner build dictionaries."""

    if not repository_root:
        return []
    base = Path(repository_root)
    if not base.exists():
        return []

    metadata = poedb_metadata or {}

    builds: List[Build] = []
    for xml_path in base.rglob("*.xml"):
        if "TestBuilds" not in xml_path.parts:
            continue
        try:
            tree = ET.parse(xml_path)
        except ET.ParseError:
            continue
        root = tree.getroot()
        build_elem = root.find("Build")
        if build_elem is None:
            continue
        class_name = build_elem.get("className", "Unknown")
        ascend_class = build_elem.get("ascendClassName", "") or class_name
        ascendancy = f"{class_name} - {ascend_class}".strip()
        main_skill, gem_group = _extract_skill_group(root.find("Skills"))
        notes_elem = root.find("Notes")
        summary = (notes_elem.text or "").strip() if notes_elem is not None else ""
        if not summary:
            summary = f"Imported test build for {main_skill or 'an unknown skill'} from the Path of Building repository."

        tags = _guess_default_tags(ascend_class, main_skill)
        meta_key = _normalise(main_skill)
        if meta_key and meta_key in metadata:
            for key, value in metadata[meta_key].items():
                if key == "skill_tags":
                    tags.setdefault("skill_tags", value)
                else:
                    tags[key] = value

        build: Build = {
            "id": _slugify(xml_path.stem),
            "name": f"{main_skill or xml_path.stem} ({ascend_class})",
            "summary": summary,
            "ascendancy": ascendancy,
            "tags": tags,
            "skill_gems": {
                "main_skill": main_skill or gem_group[:1][0] if gem_group else "",
                "six_link": gem_group,
            },
        }
        builds.append(build)
    return builds


@dataclass
class ExternalLibrary:
    builds: List[Build]


def load_external_builds(
    *,
    poedb_path: Optional[str] = None,
    pob_path: Optional[str] = None,
) -> List[Build]:
    """Collect external builds from PoEDB and Path of Building sources."""

    metadata = load_poedb_metadata(poedb_path)
    builds = load_path_of_building_builds(pob_path, poedb_metadata=metadata)
    return builds


__all__ = [
    "ExternalLibrary",
    "load_external_builds",
    "load_path_of_building_builds",
    "load_poedb_metadata",
]

