"""Utility helpers for fixed Path of Building demo builds."""
from __future__ import annotations

import base64
import importlib.resources as resources
import re
import zlib

DEADEYE_RESOURCE = resources.files("pob_build_planner.data_files").joinpath("deadeye_demo.xml")
BASE_VERSION = "3_24"
_CLASS_NAME = "Ranger"
_ASCENDANCY = "Deadeye"
_BUILD_ID = "deadeye_demo"
_BUILD_NAME = "Deadeye Demo Ranger"
_SUMMARY = (
    "Demonstration Deadeye tree showcasing two allocated passive nodes so imports "
    "render a populated Path of Building profile."
)


def _load_deadeye_xml() -> str:
    return DEADEYE_RESOURCE.read_text(encoding="utf-8")


def _apply_tree_version(xml: str, tree_version: str) -> str:
    """Return xml updated to use the requested passive tree version."""

    pattern = r"(treeVersion|targetVersion)=\"[^\"]+\""

    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        return f'{key}="{tree_version}"'

    return re.sub(pattern, replace, xml, count=0)


def get_deadeye_demo_xml(tree_version: str | None = None) -> str:
    """Return the demo XML content, optionally overriding the tree version."""

    xml = _load_deadeye_xml()
    if tree_version and tree_version != BASE_VERSION:
        xml = _apply_tree_version(xml, tree_version)
    return xml


def get_deadeye_demo_code(tree_version: str | None = None) -> str:
    """Return the base64-encoded PoB string for the demo build."""

    xml = get_deadeye_demo_xml(tree_version)
    compressed = zlib.compress(xml.encode("utf-8"))
    return base64.b64encode(compressed).decode("ascii")


def get_deadeye_demo_build(tree_version: str | None = None) -> dict[str, object]:
    """Return a Build dict referencing the demo payload."""

    version = tree_version or BASE_VERSION
    pob_code = get_deadeye_demo_code(tree_version)
    return {
        "id": _BUILD_ID,
        "name": _BUILD_NAME,
        "summary": _SUMMARY,
        "ascendancy": f"{_CLASS_NAME} - {_ASCENDANCY}",
        "level": 90,
        "tags": {
            "damage_type": ["elemental"],
            "combat_range": ["ranged"],
            "damage_source": ["attack"],
        },
        "core_passives": [
            "Allocates Finesse near the Ranger start.",
            "Allocates Quickstep on the Ranger path for movement speed.",
        ],
        "skill_gems": {
            "main_skill": "Kinetic Blast",
            "six_link": [
                "Kinetic Blast",
                "Greater Multiple Projectiles Support",
                "Elemental Damage with Attacks Support",
                "Inspiration Support",
                "Added Lightning Damage Support",
                "Increased Critical Strikes Support",
            ],
            "guard": "Steelskin",
            "aura_setup": ["Grace", "Determination"],
            "mobility": "Dash",
        },
        "gear": {
            "weapon": "Rare wand with elemental damage and attack speed.",
            "quiver": "Penetrating Arrow Quiver with elemental damage to attacks.",
            "helmet": "Evasion helmet with life and resistances.",
        },
        "progression": {
            "leveling": (
                "Follow the highlighted nodes to reach Finesse and Quickstep while investing in "
                "core projectile damage clusters."
            ),
        },
        "target_version": version,
        "tree_spec": {
            "nodes": [40479, 29534],
        },
        "pob_code": pob_code,
    }


__all__ = [
    "get_deadeye_demo_code",
    "get_deadeye_demo_xml",
    "get_deadeye_demo_build",
    "BASE_VERSION",
]

