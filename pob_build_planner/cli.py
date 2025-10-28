"""Command line interface for the Path of Building build planner."""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, List, Optional, Sequence

from .data import BUILD_LIBRARY
from .generator import generate_build_for_skill
from .integrations import load_path_of_building_builds, load_poedb_metadata
from .planner import (
    BuildRecommendation,
    PlaystylePreferences,
    get_build_by_id,
    parse_freeform_preferences,
    recommend_builds,
    recommend_builds_by_skill,
    recommend_dual_phase_builds,
)
from .pob import PathOfBuildingController, PathOfBuildingLaunchError


def _stdin_is_interactive() -> bool:
    try:
        return sys.stdin.isatty()
    except Exception:  # pragma: no cover - defensive guard
        return False


def _prompt_for_skill(args: argparse.Namespace) -> Optional[str]:
    """Return a skill gem supplied by the user when running interactively."""

    if args.skill or args.describe or args.config or args.open_build or args.dual_phase:
        return None
    if not _stdin_is_interactive():
        return None
    try:
        response = input("What do you want to play? ")
    except EOFError:
        return None
    skill = response.strip()
    if skill:
        print(f"\nSearching for builds that feature '{skill}'.")
        return skill
    return None


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
    parser.add_argument(
        "--describe",
        help=(
            "Free-form description of your playstyle such as 'daggers, fast attacker, melee, tanky'."
        ),
    )
    parser.add_argument("--damage-type", help="Preferred damage type such as physical, fire, chaos.")
    parser.add_argument("--combat-range", help="melee, ranged, aoe, etc.")
    parser.add_argument(
        "--damage-source",
        help="Primary source of damage: attack, spell, minion, trap, damage_over_time.",
    )
    parser.add_argument(
        "--skill",
        help=(
            "Name of a skill gem to search for builds (e.g. 'Cyclone'). "
            "Ignores other preference filters."
        ),
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
        "--dual-phase",
        action="store_true",
        help=(
            "Produce two recommendations: one tuned for league start and another optimised for endgame."
        ),
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
    parser.add_argument(
        "--poedb-path",
        help=(
            "Path to a local checkout or export of the PoEDB data repository. "
            "Skill metadata from this source is used to enrich Path of Building builds."
        ),
    )
    parser.add_argument(
        "--path-of-building",
        help=(
            "Path to a local checkout of the Path of Building Community git repository. "
            "Test builds in the repo will be merged into the planner library."
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
    if args.describe:
        freeform = parse_freeform_preferences(args.describe)
        for key, value in freeform.items():
            if key in {"content_focus", "defense_layers"}:
                existing = set(config.get(key, []))
                existing.update(value)
                config[key] = sorted(existing)
            else:
                config[key] = value
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
    prompted_skill = _prompt_for_skill(args)
    if prompted_skill:
        args.skill = prompted_skill

    controller = PathOfBuildingController(
        executable_path=args.pob_executable,
        open_mode=args.open_mode,
    )

    poedb_metadata = load_poedb_metadata(args.poedb_path)
    external_builds = load_path_of_building_builds(
        args.path_of_building, poedb_metadata=poedb_metadata
    )
    library: Sequence[Dict[str, object]] = list(BUILD_LIBRARY) + list(external_builds)

    if args.open_build:
        recommendation = get_build_by_id(args.open_build, library=library)
        if not recommendation:
            print(f"No build found with id '{args.open_build}'.")
            return 1
        try:
            code = controller.open_build(recommendation.build)
            print(f"Opened build in Path of Building. Import code: {code}")
        except PathOfBuildingLaunchError as exc:
            print(str(exc))
            code = recommendation.pob_code()
            print(f"Import code: {code}")
            print("Unable to open Path of Building automatically, but the build code is available above.")
        return 0

    def present_recommendations(recommendations: List[Any]) -> None:
        detected_version = controller.detect_tree_version()
        if detected_version:
            for rec in recommendations:
                if rec.build.get("target_version") != detected_version:
                    rec.build["target_version"] = detected_version
                    rec.build.pop("pob_code", None)
                    rec.build.pop("pobb_in_url", None)
                    if hasattr(rec, "_pob_code_cache"):
                        rec._pob_code_cache = None  # type: ignore[attr-defined]
        if args.json:
            payload = [rec.to_payload() for rec in recommendations]
            print(json.dumps(payload, indent=2))
        else:
            for idx, rec in enumerate(recommendations, start=1):
                print(f"===== Recommendation #{idx} =====")
                print(rec.to_report())
                if idx != len(recommendations):
                    print("\n")
        if args.open and recommendations:
            try:
                code = controller.open_build(recommendations[0].build)
                print(f"\nOpened top recommendation in Path of Building. Import code: {code}")
            except PathOfBuildingLaunchError as exc:
                print(str(exc))
                code = recommendations[0].pob_code()
                print(f"Import code: {code}")
                print(
                    "Unable to open Path of Building automatically. Use the import code above to open the build manually."
                )

    if args.skill:
        skill_recs = recommend_builds_by_skill(args.skill, top_n=args.top, library=library)
        if not skill_recs:
            print(
                f"No builds in the library use the skill '{args.skill}'.\n"
                "Generating a fresh Path of Building plan from scratch..."
            )
            try:
                generated_build = generate_build_for_skill(
                    args.skill, poedb_metadata=poedb_metadata
                )
            except ValueError as exc:
                print(str(exc))
                return 1
            skill_recs = [
                BuildRecommendation(
                    build=generated_build,
                    score=100,
                    matched_tags={
                        "skill": [f"{args.skill} (auto-generated)"]
                    },
                )
            ]
        present_recommendations(skill_recs)
        return 0

    preferences = merge_config(args)
    if args.dual_phase:
        plan = recommend_dual_phase_builds(preferences, top_n=args.top, library=library)
        if args.json:
            print(json.dumps(plan.to_payload(), indent=2))
        else:
            print(plan.to_report())
        if args.open:
            opened = False
            launch_failed = False
            if plan.league_start:
                try:
                    code = controller.open_build(plan.league_start.build)
                    print(
                        "\nOpened league start recommendation in Path of Building. Import code: "
                        f"{code}"
                    )
                    opened = True
                except PathOfBuildingLaunchError as exc:
                    print(str(exc))
                    print(f"League start import code: {plan.league_start.pob_code()}")
                    launch_failed = True
            if plan.endgame:
                try:
                    code = controller.open_build(plan.endgame.build)
                    print(
                        "Opened endgame recommendation in Path of Building. Import code: "
                        f"{code}"
                    )
                    opened = True
                except PathOfBuildingLaunchError as exc:
                    print(str(exc))
                    print(f"Endgame import code: {plan.endgame.pob_code()}")
                    launch_failed = True
            if not opened:
                if launch_failed:
                    print(
                        "Unable to launch Path of Building automatically. Use the import codes above to open the builds manually."
                    )
                else:
                    print("No builds were opened because no recommendations were available.")
        return 0

    recommendations = recommend_builds(preferences, top_n=args.top, library=library)
    if not recommendations:
        print("No builds matched the provided playstyle. Try relaxing your filters.")
        return 1
    present_recommendations(recommendations)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(run_cli())
