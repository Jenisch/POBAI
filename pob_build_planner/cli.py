"""Command line interface for the Path of Building build planner."""
from __future__ import annotations

import argparse
import json
from typing import Any, Dict, List, Optional

from .planner import PlaystylePreferences, get_build_by_id, recommend_builds
from .pob import PathOfBuildingController, build_to_code


def parse_bool(value: Optional[str]) -> Optional[bool]:
    if value is None:
        return None
    lowered = value.lower()
    if lowered in {"true", "yes", "y", "1"}:
        return True
    if lowered in {"false", "no", "n", "0"}:
        return False
    raise argparse.ArgumentTypeError(f"Cannot interpret '{value}' as a boolean flag")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Recommend Path of Building builds based on your desired playstyle. "
            "You can either pass options directly or provide a JSON configuration via --config."
        )
    )
    parser.add_argument("--config", help="Path to a JSON file containing playstyle preferences.")
    parser.add_argument("--damage-type", help="Preferred damage type such as physical, fire, chaos.")
    parser.add_argument("--combat-range", help="melee, ranged, aoe, etc.")
    parser.add_argument(
        "--damage-source",
        help="Primary source of damage: attack, spell, minion, trap, damage_over_time.",
    )
    parser.add_argument("--complexity", help="Desired complexity (low, medium, high).")
    parser.add_argument("--budget", help="Target budget tier (low, medium, high, league_start).")
    parser.add_argument(
        "--league-start",
        type=parse_bool,
        nargs="?",
        const=True,
        help="Whether the build should be league-start viable (true/false).",
    )
    parser.add_argument(
        "--content-focus",
        nargs="*",
        help="Content priorities such as mapping, bossing, delve, juiced_mapping.",
    )
    parser.add_argument(
        "--defense-layers",
        nargs="*",
        help="Important defensive layers (armour, evasion, block, spell_suppression, etc.).",
    )
    parser.add_argument(
        "--mobility-priority",
        type=parse_bool,
        nargs="?",
        const=True,
        help="Whether high mobility is required.",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=3,
        help="How many top recommendations to display (default: 3).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output the recommendation payload as JSON instead of a formatted report.",
    )
    parser.add_argument(
        "--open",
        action="store_true",
        help="Open the top recommendation inside Path of Building using the poe:// handler.",
    )
    parser.add_argument(
        "--open-build",
        help="Skip recommendation matching and open a specific build id inside Path of Building.",
    )
    parser.add_argument(
        "--pob-executable",
        help="Optional explicit path to PathOfBuilding.exe for file-based launch mode.",
    )
    parser.add_argument(
        "--open-mode",
        choices=["protocol", "file"],
        default="protocol",
        help=(
            "How to launch Path of Building when using --open or --open-build."
            " 'protocol' uses poe://build links (default) and 'file' writes a temporary"
            " XML file and opens it with the Path of Building executable."
        ),
    )
    return parser


def merge_config(args: argparse.Namespace) -> PlaystylePreferences:
    config: Dict[str, Any] = {}
    if args.config:
        with open(args.config, "r", encoding="utf8") as fh:
            config = json.load(fh)
            if not isinstance(config, dict):
                raise ValueError("Configuration file must be a JSON object")
    cli_overrides: Dict[str, Any] = {
        "damage_type": args.damage_type,
        "combat_range": args.combat_range,
        "damage_source": args.damage_source,
        "complexity": args.complexity,
        "budget": args.budget,
        "league_start": args.league_start,
        "content_focus": args.content_focus,
        "defense_layers": args.defense_layers,
        "mobility_priority": args.mobility_priority,
    }
    for key, value in list(cli_overrides.items()):
        if value is None:
            cli_overrides.pop(key)
    config.update(cli_overrides)
    return PlaystylePreferences.from_dict(config)


def run_cli(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    controller = PathOfBuildingController(
        executable_path=args.pob_executable,
        open_mode=args.open_mode,
    )

    if args.open_build:
        recommendation = get_build_by_id(args.open_build)
        if not recommendation:
            print(f"No build found with id '{args.open_build}'.")
            return 1
        code = controller.open_build(recommendation.build)
        print(f"Opened build in Path of Building. Import code: {code}")
        return 0

    preferences = merge_config(args)
    recommendations = recommend_builds(preferences, top_n=args.top)
    if not recommendations:
        print("No builds matched the provided playstyle. Try relaxing your filters.")
        return 1
    if args.json:
        payload = [
            {
                "id": rec.build["id"],
                "name": rec.build["name"],
                "score": rec.score,
                "matched_tags": rec.matched_tags,
                "ascendancy": rec.build["ascendancy"],
                "summary": rec.build["summary"],
                "core_passives": rec.build.get("core_passives", []),
                "skill_gems": rec.build.get("skill_gems", {}),
                "gear": rec.build.get("gear", {}),
                "progression": rec.build.get("progression", {}),
                "pob_code": build_to_code(rec.build),
            }
            for rec in recommendations
        ]
        print(json.dumps(payload, indent=2))
    else:
        for idx, rec in enumerate(recommendations, start=1):
            print(f"===== Recommendation #{idx} =====")
            print(rec.to_report())
            if idx != len(recommendations):
                print("\n")
    if args.open and recommendations:
        code = controller.open_build(recommendations[0].build)
        print(f"\nOpened top recommendation in Path of Building. Import code: {code}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(run_cli())
