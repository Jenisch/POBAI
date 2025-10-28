import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pob_build_planner.planner import (
    PlaystylePreferences,
    playstyle_from_description,
    recommend_builds,
    recommend_builds_by_skill,
    recommend_dual_phase_builds,
)


def test_recommendations_return_sorted_results():
    prefs = PlaystylePreferences(
        damage_type="chaos",
        combat_range="ranged",
        damage_source="attack",
        budget="league_start",
        content_focus=["mapping", "bossing"],
    )
    results = recommend_builds(prefs, top_n=2)
    assert results, "Expected at least one result"
    assert results[0].score >= results[-1].score
    ids = [rec.build["id"] for rec in results]
    assert "toxic_rain_pathfinder" in ids


def test_handles_strict_preferences_without_crashing():
    prefs = PlaystylePreferences(
        damage_type="cold",
        combat_range="melee",
        damage_source="trap",
        budget="low",
        content_focus=["delve"],
        defense_layers=["spell_suppression"],
        mobility_priority=True,
        league_start=False,
    )
    results = recommend_builds(prefs, top_n=3)
    assert isinstance(results, list)
    for rec in results:
        assert rec.score >= 5


def test_dual_phase_returns_league_and_endgame_recommendations():
    prefs = PlaystylePreferences(budget="league_start", content_focus=["bossing"])
    plan = recommend_dual_phase_builds(prefs)
    assert plan.league_start is not None
    assert plan.endgame is not None
    league_tags = plan.league_start.build.get("tags", {})
    assert bool(league_tags.get("league_start"))
    endgame_tags = plan.endgame.build.get("tags", {})
    budgets = {str(v).lower() for v in endgame_tags.get("budget", [])}
    assert "high" in budgets or not bool(endgame_tags.get("league_start"))
    assert plan.league_start.build["id"] != plan.endgame.build["id"]


def test_playstyle_from_description_sets_expected_preferences():
    prefs = playstyle_from_description("daggers, fast attacker, melee, tanky")
    assert prefs.damage_source == "attack"
    assert prefs.combat_range == "melee"
    assert prefs.mobility_priority is True
    assert "armour" in prefs.defense_layers


def test_description_merges_multiple_focus_keywords():
    prefs = playstyle_from_description("bossing and mapping league starter")
    assert sorted(prefs.content_focus) == ["bossing", "mapping"]
    assert prefs.league_start is True
    assert prefs.budget == "league_start"


def test_recommendations_by_skill_prioritise_main_skill_matches():
    results = recommend_builds_by_skill("Cyclone")
    assert results, "Expected at least one Cyclone build"
    top = results[0]
    assert top.build["id"] == "cyclone_slayer"
    assert "skill" in top.matched_tags
    assert any("Cyclone" in value for value in top.matched_tags["skill"])
    assert top.pob_link().startswith("https://pobb.in/")


def test_skill_lookup_supports_partial_matches():
    results = recommend_builds_by_skill("toxic")
    assert results, "Expected a match when searching for toxic"
    assert any("Toxic Rain" in value for rec in results for value in rec.matched_tags["skill"])
