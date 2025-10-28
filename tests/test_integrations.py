import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pob_build_planner.integrations import (
    load_external_builds,
    load_path_of_building_builds,
    load_poedb_metadata,
)
from pob_build_planner.planner import PlaystylePreferences, recommend_builds


@pytest.fixture
def poedb_directory(tmp_path: Path) -> Path:
    data = [
        {"name": "Toxic Rain", "tags": ["Chaos", "Projectile", "Bow", "Attack"]},
        {"Name": "Cyclone", "SkillTypes": {"Attack": True, "Melee": True, "Physical": True}},
    ]
    payload = tmp_path / "ActiveSkillGem.json"
    payload.write_text(json.dumps(data), encoding="utf8")
    return tmp_path


def create_sample_build(root: Path, name: str, *, skill: str, ascendancy: str) -> Path:
    build_dir = root / "spec" / "TestBuilds" / "3.24"
    build_dir.mkdir(parents=True, exist_ok=True)
    xml = f"""<?xml version='1.0' encoding='UTF-8'?>
<PathOfBuilding>
  <Build level="95" targetVersion="3_24" className="Ranger" ascendClassName="{ascendancy}"></Build>
  <Notes>{name} showcase build.</Notes>
  <Skills>
    <Skill mainActiveSkill="1" slot="Weapon 1">
      <Gem nameSpec="{skill}" gemId="Metadata/Items/Gems/{skill}" skillId="{skill}" />
      <Gem nameSpec="Support" gemId="Metadata/Items/Gems/SupportGem" skillId="SupportGem" />
    </Skill>
  </Skills>
</PathOfBuilding>
"""
    xml_path = build_dir / f"{name}.xml"
    xml_path.write_text(xml, encoding="utf8")
    return xml_path


def test_load_poedb_metadata_extracts_skill_information(poedb_directory: Path) -> None:
    metadata = load_poedb_metadata(str(poedb_directory))
    assert metadata
    assert "toxicrain" in metadata
    assert metadata["toxicrain"]["damage_source"] == "attack"
    assert "skill_tags" in metadata["cyclone"]


def test_path_of_building_loader_builds_entries(poedb_directory: Path, tmp_path: Path) -> None:
    create_sample_build(tmp_path, "Mirage Archer Toxic Rain", skill="Toxic Rain", ascendancy="Deadeye")
    metadata = load_poedb_metadata(str(poedb_directory))
    builds = load_path_of_building_builds(str(tmp_path), poedb_metadata=metadata)
    assert builds
    build = builds[0]
    assert build["skill_gems"]["main_skill"] == "Toxic Rain"  # type: ignore[index]
    tags = build["tags"]
    assert tags["damage_type"] == "chaos"
    assert "skill_tags" in tags


def test_recommend_builds_uses_external_library(tmp_path: Path, poedb_directory: Path) -> None:
    create_sample_build(tmp_path, "Cyclone Slayer", skill="Cyclone", ascendancy="Slayer")
    external = load_external_builds(poedb_path=str(poedb_directory), pob_path=str(tmp_path))
    prefs = PlaystylePreferences(damage_source="attack")
    results = recommend_builds(prefs, library=external, min_score=5, top_n=1)
    assert results, "Expected fallback to pick the external build"
    assert results[0].build["id"].startswith("cyclone")
