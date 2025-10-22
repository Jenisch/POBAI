from __future__ import annotations

import base64
import zlib

import pytest

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pob_build_planner.data import BUILD_LIBRARY
from pob_build_planner.pob import (
    PathOfBuildingController,
    build_to_code,
    build_to_pobb_in_url,
    build_to_xml,
)


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


def test_build_to_pobb_in_url_returns_share_link() -> None:
    build = BUILD_LIBRARY[0]
    url = build_to_pobb_in_url(build)
    assert url.startswith("https://pobb.in/")
    assert len(url.split("/")) >= 4  # ensures a code is appended
