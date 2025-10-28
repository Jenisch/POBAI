import os
import sys
from types import SimpleNamespace

import pytest
import urllib.request

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pob_build_planner import cli
from pob_build_planner.demo import get_deadeye_demo_code, get_deadeye_demo_xml
from pob_build_planner.data import BUILD_LIBRARY


class DummyRecommendation:
    def __init__(self, build):
        self.build = build
        self._build = build

    def to_payload(self):
        return {"id": self.build.get("id")}

    def to_report(self):
        return "dummy report"

    def pob_code(self):
        from pob_build_planner.pob import build_to_code

        return build_to_code(self.build)


class DummyPlan:
    def __init__(self, build):
        self.league_start = DummyRecommendation(build)
        self.endgame = None

    def to_payload(self):
        return {"league_start": self.league_start.to_payload(), "endgame": None}

    def to_report(self):
        return "plan"


def test_prompt_for_skill(monkeypatch, capsys):
    args = SimpleNamespace(
        skill=None,
        describe=None,
        config=None,
        open_build=None,
        dual_phase=False,
    )
    monkeypatch.setattr(cli, "_stdin_is_interactive", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _: "Cyclone")
    skill = cli._prompt_for_skill(args)
    assert skill == "Cyclone"
    captured = capsys.readouterr()
    assert "Cyclone" in captured.out


def test_deadeye_demo_prints_code_and_opens(monkeypatch, capsys):
    base_code = get_deadeye_demo_code()
    base_xml = get_deadeye_demo_xml()

    opened = []

    class FakeController:
        def __init__(self, *args, **kwargs):
            self.open_mode = kwargs.get("open_mode", "protocol")
            self.executable_path = kwargs.get("executable_path")

        def detect_tree_version(self):
            return "3_24"

        def open_code(self, code, xml_payload=None):
            opened.append((code, xml_payload))

    monkeypatch.setattr(cli, "PathOfBuildingController", FakeController)

    exit_code = cli.run_cli(["--deadeye-demo"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert captured.out == base_code
    assert opened == [(base_code, base_xml)]


def test_run_cli_interactive_skill(monkeypatch, capsys):
    calls = {}

    def fake_recommend(skill, top_n, library):
        calls["skill"] = skill
        return [DummyRecommendation(BUILD_LIBRARY[0])]

    monkeypatch.setattr(cli, "load_poedb_metadata", lambda _: {})
    monkeypatch.setattr(cli, "load_path_of_building_builds", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(cli, "recommend_builds_by_skill", fake_recommend)
    monkeypatch.setattr(cli, "_stdin_is_interactive", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _: "Cyclone")

    exit_code = cli.run_cli([])
    assert exit_code == 0
    assert calls["skill"] == "Cyclone"
    captured = capsys.readouterr()
    assert "Cyclone" in captured.out


def test_run_cli_open_build_launch_error(monkeypatch, capsys):
    build = BUILD_LIBRARY[0]

    def fake_get_build(build_id, library):
        return DummyRecommendation(build)

    class FakeController:
        def __init__(self, *args, **kwargs):
            pass

        def open_build(self, _build):
            from pob_build_planner.pob import PathOfBuildingLaunchError

            raise PathOfBuildingLaunchError("boom")

    monkeypatch.setattr(cli, "load_poedb_metadata", lambda _: {})
    monkeypatch.setattr(cli, "load_path_of_building_builds", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(cli, "get_build_by_id", fake_get_build)
    monkeypatch.setattr(cli, "PathOfBuildingController", FakeController)

    exit_code = cli.run_cli(["--open-build", build["id"]])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "boom" in captured.out
    assert "Import code" in captured.out


def test_run_cli_open_deadeye_demo(monkeypatch, capsys):
    opened: list[str] = []

    class FakeController:
        def __init__(self, *args, **kwargs):
            pass

        def open_build(self, build):
            opened.append(build.get("id"))
            return build.get("pob_code", "demo_code")

    monkeypatch.setattr(cli, "load_poedb_metadata", lambda _: {})
    monkeypatch.setattr(cli, "load_path_of_building_builds", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(cli, "PathOfBuildingController", FakeController)

    exit_code = cli.run_cli(["--open-build", "deadeye_demo"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "Opened build in Path of Building" in captured.out
    assert opened == ["deadeye_demo"]


def test_generate_skill_fallback(monkeypatch, capsys):
    class DummyResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self) -> bytes:
            return b"{\"id\": \"generated\"}"

    monkeypatch.setattr(urllib.request, "urlopen", lambda *args, **kwargs: DummyResponse())

    monkeypatch.setattr(cli, "load_poedb_metadata", lambda _: {
        "kineticblast": {
            "skill_tags": ["attack", "projectile", "wand"],
            "damage_source": "attack",
            "damage_type": "elemental",
            "combat_range": "ranged",
        }
    })
    monkeypatch.setattr(cli, "load_path_of_building_builds", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(cli, "_stdin_is_interactive", lambda: False)
    monkeypatch.setattr(cli, "recommend_builds_by_skill", lambda *args, **kwargs: [])

    exit_code = cli.run_cli(["--skill", "Kinetic Blast"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "Generating a fresh Path of Building plan from scratch" in captured.out
    assert "Kinetic Blast Deadeye" in captured.out
