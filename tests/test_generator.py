import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pob_build_planner.generator import generate_build_for_skill


def test_generate_build_includes_skill_in_six_link():
    build = generate_build_for_skill("Kinetic Blast")
    gems = build["skill_gems"]["six_link"]
    assert gems[0] == "Kinetic Blast"
    assert "Power Charge On Critical Support" in gems
    assert "template_code" in build


def test_generate_build_applies_metadata_tags():
    metadata = {
        "kineticblast": {
            "skill_tags": ["attack", "projectile", "wand"],
            "damage_source": "attack",
            "damage_type": "physical",
            "combat_range": "ranged",
        }
    }
    build = generate_build_for_skill("Kinetic Blast", poedb_metadata=metadata)
    tags = build["tags"]
    assert "physical" in tags["damage_type"]
    assert "attack" in tags["damage_source"]
    assert build["ascendancy"].endswith("Deadeye")


def test_generate_build_rejects_empty_skill():
    try:
        generate_build_for_skill(" ")
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError for empty skill name")
