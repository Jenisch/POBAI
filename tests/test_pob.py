from __future__ import annotations

import base64
import copy
import os
import subprocess
import sys
import urllib.request
import xml.etree.ElementTree as ET
import zlib

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pob_build_planner.data import BUILD_LIBRARY
from pob_build_planner.generator import generate_build_for_skill
from pob_build_planner.pob import (
    TARGET_VERSION,
    PathOfBuildingController,
    PathOfBuildingLaunchError,
    build_to_code,
    build_to_pobb_in_url,
    build_to_xml,
)


def test_build_to_code_round_trip() -> None:
    build = copy.deepcopy(BUILD_LIBRARY[0])
    build.pop("pobb_in_url", None)
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
    root = ET.fromstring(xml)
    gem = root.find(".//Skills/Skill/Gem")
    assert gem is not None
    assert gem.get("nameSpec")


def test_build_to_xml_includes_generated_tree_and_items() -> None:
    build = generate_build_for_skill("Kinetic Blast")
    xml = build_to_xml(build)
    root = ET.fromstring(xml)
    spec = root.find(".//Tree/Spec")
    assert spec is not None
    nodes = spec.get("nodes")
    assert nodes
    assert "50459" in nodes.split(",")
    assert spec.get("classId") == "2"
    assert spec.get("ascendClassId") == "1"
    items = root.find("Items")
    assert items is not None
    assert list(items)


def test_build_to_xml_uses_template_target_version_when_present() -> None:
    build = generate_build_for_skill("Kinetic Blast")
    xml = build_to_xml(build)
    root = ET.fromstring(xml)
    build_elem = root.find("Build")
    assert build_elem is not None

    target_version = build_elem.get("targetVersion")
    assert target_version

    template_code = build.get("template_code")
    if isinstance(template_code, str):
        padding = "=" * (-len(template_code) % 4)
        template_xml = zlib.decompress(base64.urlsafe_b64decode(template_code + padding)).decode("utf-8")
        template_root = ET.fromstring(template_xml)
        template_build = template_root.find("Build")
        assert template_build is not None
        assert target_version == template_build.get("targetVersion")
    else:
        assert target_version == TARGET_VERSION


def test_build_to_xml_overrides_template_target_version_when_requested() -> None:
    build = generate_build_for_skill("Kinetic Blast")
    build["target_version"] = "9_99"
    xml = build_to_xml(build)
    root = ET.fromstring(xml)
    build_elem = root.find("Build")
    assert build_elem is not None
    assert build_elem.get("targetVersion") == "9_99"
    spec = root.find(".//Tree/Spec")
    assert spec is not None
    assert spec.get("treeVersion") == "9_99"
    assert spec.get("targetVersion") == "9_99"


def test_build_to_xml_sets_main_skill_group() -> None:
    build = generate_build_for_skill("Kinetic Blast")
    xml = build_to_xml(build)
    root = ET.fromstring(xml)
    skill_group = root.find(".//Skills/Skill")
    assert skill_group is not None
    assert skill_group.get("mainActiveSkill") == "1"
    gem = skill_group.find("Gem")
    assert gem is not None
    assert gem.get("nameSpec") == "Kinetic Blast"
    assert gem.get("qualityId") == "Default"


def test_build_to_pobb_in_url_returns_share_link(monkeypatch: pytest.MonkeyPatch) -> None:
    build = copy.deepcopy(BUILD_LIBRARY[0])
    build.pop("pobb_in_url", None)

    class DummyResponse:
        def __enter__(self) -> "DummyResponse":
            return self

        def __exit__(self, exc_type, exc, tb) -> bool:
            return False

        def read(self) -> bytes:
            return b"{\"id\": \"abc123\"}"

    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: DummyResponse())

    url = build_to_pobb_in_url(build)
    assert url == "https://pobb.in/abc123"


def test_build_to_pobb_in_url_falls_back_to_embedded_code(monkeypatch: pytest.MonkeyPatch) -> None:
    build = copy.deepcopy(BUILD_LIBRARY[0])
    build.pop("pobb_in_url", None)

    def boom(*_args, **_kwargs):
        raise urllib.error.URLError("nope")

    monkeypatch.setattr(urllib.request, "urlopen", boom)

    url = build_to_pobb_in_url(build)
    assert url.startswith("https://pobb.in/#code:")


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


def test_detect_tree_version_prefers_latest(monkeypatch: pytest.MonkeyPatch) -> None:
    controller = PathOfBuildingController(executable_path="C:/PoBCommunity/PathOfBuilding.exe")

    tree_dir = os.path.normpath("C:/PoBCommunity/TreeData")

    def fake_isdir(path: str) -> bool:
        normalised = os.path.normpath(path)
        return normalised in {os.path.normpath("C:/PoBCommunity"), tree_dir}

    monkeypatch.setattr(os.path, "isdir", fake_isdir)
    monkeypatch.setattr(
        os.path,
        "isfile",
        lambda path: os.path.normpath(path) == os.path.normpath("C:/PoBCommunity/PathOfBuilding.exe"),
    )
    monkeypatch.setattr(
        os,
        "listdir",
        lambda path: ["3_21.zip", "3_23_1.zip", "3_22.zip"] if os.path.normpath(path) == tree_dir else [],
    )

    detected = controller.detect_tree_version()
    assert detected == "3_23_1"


def test_open_build_uses_detected_tree_version(monkeypatch: pytest.MonkeyPatch) -> None:
    build = copy.deepcopy(BUILD_LIBRARY[0])
    build.pop("pob_code", None)

    monkeypatch.setattr(
        PathOfBuildingController,
        "detect_tree_version",
        lambda self: "3_23",
    )

    calls: list[str] = []
    monkeypatch.setattr("webbrowser.open", lambda url: calls.append(url))

    controller = PathOfBuildingController(open_mode="protocol")
    code = controller.open_build(build)

    assert build.get("target_version") == "3_23"
    padding = "=" * (-len(code) % 4)
    xml = zlib.decompress(base64.urlsafe_b64decode(code + padding)).decode("utf-8")
    assert 'targetVersion="3_23"' in xml
