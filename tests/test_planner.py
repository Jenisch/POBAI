import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pob_build_planner.planner import PlaystylePreferences, recommend_builds


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
