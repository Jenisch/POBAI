from __future__ import annotations

import base64
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
import zlib

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pob_build_planner.data import BUILD_LIBRARY
from pob_build_planner.generator import generate_build_for_skill
from pob_build_planner.pob import PathOfBuildingController, PathOfBuildingLaunchError
from pob_build_planner.pob import build_to_code, build_to_pobb_in_url, build_to_xml


def test_build_to_code_round_trip() -> None:
    build = BUILD_LIBRARY[0]
    code = build_to_code(build)
    padding = "=" * (-len(code) % 4)
    xml = zlib.decompress(base64.urlsafe_b64decode(code + padding)).decode("utf-8")
    assert build["summary"] in xml
    class_name = build["ascendancy"].split("-")[0].strip()
    assert f"className=\"{class_name}\"" in xml


def test_controller_protocol(monkeypatch: pytest.MonkeyPatch) -> None:
    build = BUILD_LIBRARY[1]
    calls: list[str] = []

    def fake_open(url: str) -> None:
        calls.append(url)

    monkeypatch.setattr("webbrowser.open", fake_open)
    controller = PathOfBuildingController()
    code = controller.open_build(build)
    assert calls and calls[0].startswith("poe://build/")
    assert code in calls[0]


def test_build_to_xml_contains_skill_info() -> None:
    build = BUILD_LIBRARY[2]
    xml = build_to_xml(build)
    assert build["skill_gems"]["main_skill"] in xml  # type: ignore[index]


def test_build_to_xml_uses_template_tree_and_items() -> None:
    build = generate_build_for_skill("Kinetic Blast")
    xml = build_to_xml(build)
    root = ET.fromstring(xml)
    spec = root.find(".//Tree/Spec")
    assert spec is not None
    assert spec.get("nodes")
    items = root.find("Items")
    assert items is not None
    assert list(items)


def test_build_to_xml_preserves_template_target_version() -> None:
    build = generate_build_for_skill("Kinetic Blast")
    xml = build_to_xml(build)
    root = ET.fromstring(xml)
    build_elem = root.find("Build")
    assert build_elem is not None

    template_code = build.get("template_code")
    assert isinstance(template_code, str)
    padding = "=" * (-len(template_code) % 4)
    template_xml = zlib.decompress(base64.urlsafe_b64decode(template_code + padding)).decode("utf-8")
    template_root = ET.fromstring(template_xml)
    expected_version = template_root.find("Build").get("targetVersion")

    assert build_elem.get("targetVersion") == expected_version


def test_build_to_pobb_in_url_returns_share_link() -> None:
    build = BUILD_LIBRARY[0]
    url = build_to_pobb_in_url(build)
    assert url.startswith("https://pobb.in/")
    assert len(url.split("/")) >= 4  # ensures a code is appended


def test_controller_file_mode_permission_error(monkeypatch: pytest.MonkeyPatch) -> None:
    build = BUILD_LIBRARY[0]

    class DummyTemp:
        def __init__(self):
            self.name = "temp.xml"

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def write(self, *_args, **_kwargs):
            return None

    monkeypatch.setattr("tempfile.NamedTemporaryFile", lambda *a, **k: DummyTemp())

    def boom(_args, **_kwargs):
        raise PermissionError("no access")

    monkeypatch.setattr("subprocess.Popen", boom)

    controller = PathOfBuildingController(executable_path="PathOfBuilding.exe", open_mode="file")

    with pytest.raises(PathOfBuildingLaunchError):
        controller.open_build(build)


def test_controller_accepts_directory_path(monkeypatch: pytest.MonkeyPatch) -> None:
    build = BUILD_LIBRARY[0]

    class DummyTemp:
        def __init__(self):
            self.name = "temp.xml"

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def write(self, *_args, **_kwargs):
            return None

    monkeypatch.setattr("tempfile.NamedTemporaryFile", lambda *a, **k: DummyTemp())

    captured: list[list[str]] = []

    def fake_popen(args, **_kwargs):
        captured.append(args)

    monkeypatch.setattr(subprocess, "Popen", fake_popen)
    monkeypatch.setattr(os.path, "isdir", lambda path: path == "C:/PoBCommunity")
    monkeypatch.setattr(
        os.path,
        "isfile",
        lambda path: path == "C:/PoBCommunity/Path of Building Community.exe",
    )

    controller = PathOfBuildingController(executable_path="C:/PoBCommunity", open_mode="file")
    controller.open_build(build)

    assert captured
    assert captured[0][0] == "C:/PoBCommunity/Path of Building Community.exe"
