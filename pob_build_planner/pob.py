"""Utilities for generating and launching Path of Building profiles.

The helper in this module intentionally stays self-contained and only uses the
standard library so it can run in the same environments as the rest of the
project.  The encoded build strings are compatible with the Path of Building
Community fork (Path of Exile 1) and can be opened either via the registered
``poe://`` protocol handler or by launching the Path of Building executable
directly.
"""

from __future__ import annotations

import base64
import copy
import json
import os
import re
from dataclasses import dataclass, field
import subprocess
import tempfile
import typing as t
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
import xml.etree.ElementTree as ET
import zlib

from .data import Build


POBB_IN_BASE_URL = "https://pobb.in/"
POBB_IN_API_URL = urllib.parse.urljoin(POBB_IN_BASE_URL, "api/internal/paste")


TARGET_VERSION = "3_24"


def _split_class_and_ascendancy(ascendancy: str) -> tuple[str, str]:
    parts = [part.strip() for part in ascendancy.split("-", maxsplit=1)]
    if len(parts) == 2:
        return parts[0], parts[1]
    return ascendancy, ascendancy


def _build_notes(build: Build) -> str:
    lines: list[str] = [build.get("summary", "")]  # type: ignore[arg-type]

    def extend(section: str, values: t.Iterable[str]) -> None:
        cleaned = [v for v in values if v]
        if cleaned:
            lines.append(f"\n{section}:")
            for value in cleaned:
                lines.append(f"- {value}")

    extend("Core passives", t.cast(t.Iterable[str], build.get("core_passives", [])))
    skill_gems = t.cast(dict[str, t.Any], build.get("skill_gems", {}))
    if skill_gems:
        extend("Six-link", t.cast(t.Iterable[str], skill_gems.get("six_link", [])))
        extend("Other skill gems", [
            f"{key.replace('_', ' ').title()}: {', '.join(value) if isinstance(value, list) else value}"
            for key, value in skill_gems.items()
            if key not in {"six_link"}
        ])
    gear = t.cast(dict[str, str], build.get("gear", {}))
    if gear:
        extend("Gear priorities", [f"{slot.title()}: {desc}" for slot, desc in gear.items()])
    progression = t.cast(dict[str, str], build.get("progression", {}))
    if progression:
        extend(
            "Progression tips",
            [f"{stage.replace('_', ' ').title()}: {text}" for stage, text in progression.items()],
        )
    return "\n".join(lines).strip()


def build_to_xml(build: Build, *, target_version: str = TARGET_VERSION) -> str:
    """Render a build dictionary to a Path of Building XML payload."""

    requested_version = str(build.get("target_version", "")).strip()
    target_version = requested_version or target_version

    class_name, ascendancy = _split_class_and_ascendancy(str(build.get("ascendancy", "")))
    template_root: ET.Element | None = None
    using_template = False
    template_code = build.get("template_code")
    if isinstance(template_code, str) and template_code:
        try:
            template_xml = zlib.decompress(_decode_code(template_code)).decode("utf-8")
            template_root = ET.fromstring(template_xml)
        except Exception:
            template_root = None

    if template_root is not None:
        root = copy.deepcopy(template_root)
        using_template = True
    else:
        root = ET.Element("PathOfBuilding")

    build_elem = root.find("Build")
    if build_elem is None:
        build_elem = ET.SubElement(root, "Build")
    build_elem.set("level", str(build.get("level", 90)))
    template_target_version = build_elem.get("targetVersion") if using_template else None
    applied_target_version = template_target_version or target_version
    if applied_target_version:
        build_elem.set("targetVersion", applied_target_version)
    build_elem.set("className", class_name)
    build_elem.set("ascendClassName", ascendancy)

    for child in list(root):
        if child.tag == "Notes":
            root.remove(child)
    notes = ET.SubElement(root, "Notes")
    notes.text = _build_notes(build)

    tree = root.find("Tree")
    if tree is None:
        tree = ET.SubElement(root, "Tree", activeSpec="1")
    else:
        tree.set("activeSpec", tree.get("activeSpec", "1"))
    tree_spec = t.cast(dict[str, t.Any] | None, build.get("tree_spec"))

    specs = tree.findall("Spec")
    if not specs:
        specs = [
            ET.SubElement(
                tree,
                "Spec",
                className=class_name,
                ascendClassName=ascendancy,
                targetVersion=target_version,
                title="Generated Planner Spec",
            )
        ]
    for spec in specs:
        spec.set("className", class_name)
        spec.set("ascendClassName", ascendancy)
        if applied_target_version:
            spec.set("treeVersion", applied_target_version)
            spec.set("targetVersion", applied_target_version)
        if tree_spec:
            nodes = tree_spec.get("nodes")
            if nodes:
                spec.set(
                    "nodes",
                    ",".join(str(int(node)) for node in t.cast(t.Iterable[int], nodes)),
                )
            if "class_id" in tree_spec:
                spec.set("classId", str(tree_spec["class_id"]))
            if "ascend_class_id" in tree_spec:
                spec.set("ascendClassId", str(tree_spec["ascend_class_id"]))
            build_elem.set("ascendClassName", ascendancy)

    build_elem.set("mainSocketGroup", build_elem.get("mainSocketGroup", "1"))

    skills_elem: ET.Element | None = None
    for child in list(root):
        if child.tag == "Skills":
            skills_elem = child
            break
    if skills_elem is None:
        skills_elem = ET.SubElement(root, "Skills")

    skills_attrs = dict(skills_elem.attrib)
    default_attrs = {
        "sortGemsByDPSField": "CombinedDPS",
        "sortGemsByDPS": "true",
        "defaultGemQuality": "nil",
        "defaultGemLevel": "nil",
        "showSupportGemTypes": "ALL",
        "showAltQualityGems": "false",
    }
    for key, value in default_attrs.items():
        skills_attrs.setdefault(key, value)

    skills_elem.clear()
    skills_elem.attrib.update(skills_attrs)

    skills = t.cast(dict[str, t.Any], build.get("skill_gems", {}))
    main_skill = str(skills.get("main_skill", "")) or "Cyclone"
    main = ET.SubElement(
        skills_elem,
        "Skill",
        id="1",
        label="Generated Main Setup",
        enabled="true",
        slot="Weapon 1",
        mainActiveSkill="1",
        mainActiveSkillCalcs="1",
    )
    six_link = t.cast(t.Iterable[str], skills.get("six_link", []))
    for gem in six_link:
        gem_name = str(gem).strip()
        if not gem_name:
            continue
        ET.SubElement(
            main,
            "Gem",
            skillId=gem_name.replace(" ", ""),
            level="20",
            quality="20",
            enabled="true",
            qualityId="Default",
            nameSpec=gem_name,
        )

    items = t.cast(dict[str, str], build.get("gear", {}))
    items_elem = root.find("Items")
    if items_elem is None and items:
        items_elem = ET.SubElement(root, "Items")
    if items_elem is not None and not list(items_elem):
        for slot, description in items.items():
            item = ET.SubElement(items_elem, "Item", slot=slot.title())
            item.text = description

    xml_bytes = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    return xml_bytes.decode("utf-8")


def _decode_code(code: str) -> bytes:
    padding = "=" * (-len(code) % 4)
    return base64.urlsafe_b64decode(code + padding)


def build_to_code(build: Build) -> str:
    """Return a PoB import code for the provided build."""

    xml = build_to_xml(build)
    compressed = zlib.compress(xml.encode("utf-8"))
    encoded = base64.urlsafe_b64encode(compressed).decode("ascii")
    return encoded.rstrip("=")


def build_to_pobb_in_url(build: Build) -> str:
    """Return a pobb.in share URL for a build."""

    cached = build.get("pobb_in_url")
    if isinstance(cached, str) and cached:
        return cached

    code = build_to_code(build)

    payload = json.dumps({"content": code}).encode("utf-8")
    request = urllib.request.Request(
        POBB_IN_API_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    share_url: str
    try:
        with urllib.request.urlopen(request, timeout=10) as response:  # pragma: no cover - network
            body = response.read().decode("utf-8")
        data = json.loads(body)
        if not isinstance(data, dict):
            raise ValueError("Unexpected pobb.in response payload")
        slug = data.get("id") or data.get("slug") or data.get("code")
        if isinstance(slug, str) and slug:
            share_url = urllib.parse.urljoin(POBB_IN_BASE_URL, slug)
        else:
            raise ValueError("Missing pobb.in share identifier")
    except (OSError, ValueError, json.JSONDecodeError, urllib.error.URLError):
        share_url = f"{POBB_IN_BASE_URL}#code:{code}"

    if share_url:
        build["pobb_in_url"] = share_url
    if "pob_code" not in build:
        build["pob_code"] = code
    return share_url


WINDOWS_DEFAULT_EXECUTABLE = "Path of Building Community.exe"


@dataclass
class PathOfBuildingController:
    """Lightweight automation helper for the Path of Building desktop client."""

    executable_path: str | None = None
    open_mode: str = "protocol"
    _detected_tree_version: str | None = field(default=None, init=False, repr=False)

    def _resolve_executable(self) -> str | None:
        """Return the executable path, accepting directories on Windows."""

        if not self.executable_path:
            return None

        expanded = os.path.normpath(os.path.expanduser(self.executable_path))
        if os.path.isdir(expanded):
            candidate = os.path.join(expanded, WINDOWS_DEFAULT_EXECUTABLE)
            if os.path.isfile(candidate):
                return candidate
            raise PathOfBuildingLaunchError(
                "Failed to launch Path of Building using the provided executable "
                f"'{self.executable_path}': expected to find '{WINDOWS_DEFAULT_EXECUTABLE}' in the "
                "directory."
            )

        _, ext = os.path.splitext(expanded)
        if os.name == "nt" and not ext:
            exe_candidate = expanded + ".exe"
            if os.path.isfile(exe_candidate):
                return exe_candidate

        return expanded

    def detect_tree_version(self) -> str | None:
        """Inspect the installation for available passive tree versions."""

        if self._detected_tree_version is not None:
            return self._detected_tree_version

        candidates: list[str] = []
        path = self.executable_path
        if path:
            expanded = os.path.normpath(os.path.expanduser(path))
            if os.path.isdir(expanded):
                candidates.append(expanded)
            else:
                possible = expanded
                if os.name == "nt" and not os.path.splitext(expanded)[1]:
                    exe_candidate = expanded + ".exe"
                    if os.path.isfile(exe_candidate):
                        possible = exe_candidate
                if os.path.isfile(possible):
                    candidates.append(os.path.dirname(possible))

        try:
            resolved = self._resolve_executable()
        except PathOfBuildingLaunchError:
            resolved = None
        if resolved and os.path.isfile(resolved):
            candidates.append(os.path.dirname(resolved))

        checked: set[str] = set()
        for base in candidates:
            norm_base = os.path.normpath(base)
            if norm_base in checked:
                continue
            checked.add(norm_base)
            for probe in {norm_base, os.path.dirname(norm_base)}:
                tree_dir = os.path.join(probe, "TreeData")
                if not os.path.isdir(tree_dir):
                    continue
                try:
                    entries = os.listdir(tree_dir)
                except OSError:
                    continue
                versions: list[str] = []
                for entry in entries:
                    version = _normalise_tree_version(entry)
                    if version:
                        versions.append(version)
                if versions:
                    versions.sort(key=_tree_version_key, reverse=True)
                    self._detected_tree_version = versions[0]
                    return self._detected_tree_version

        return None

    def open_build(self, build: Build, *, use_cache: bool = True) -> str:
        detected_version = self.detect_tree_version()
        if detected_version:
            if build.get("target_version") != detected_version:
                build["target_version"] = detected_version
                build.pop("pob_code", None)
                build.pop("pobb_in_url", None)

        code: str
        if use_cache and isinstance(build.get("pob_code"), str):
            code = t.cast(str, build["pob_code"])
        else:
            code = build_to_code(build)
            if use_cache:
                build["pob_code"] = code

        if self.open_mode == "protocol":
            webbrowser.open(f"poe://build/{code}")
        elif self.open_mode == "file":
            xml_payload = zlib.decompress(_decode_code(code)).decode("utf-8")
            with tempfile.NamedTemporaryFile("w", suffix=".xml", delete=False) as handle:
                handle.write(xml_payload)
                temp_path = handle.name
            resolved_executable = self._resolve_executable()
            if resolved_executable:
                try:
                    subprocess.Popen([resolved_executable, temp_path])
                except OSError as exc:  # pragma: no cover - exercised via tests
                    raise PathOfBuildingLaunchError(
                        "Failed to launch Path of Building using the provided executable "
                        f"'{resolved_executable}': {exc}"
                    ) from exc
            else:
                webbrowser.open(f"file://{temp_path}")
        else:
            raise ValueError(f"Unknown open mode '{self.open_mode}'")

        return code


__all__ = [
    "build_to_xml",
    "build_to_code",
    "build_to_pobb_in_url",
    "PathOfBuildingController",
    "PathOfBuildingLaunchError",
]

class PathOfBuildingLaunchError(RuntimeError):
    """Raised when the planner fails to launch the Path of Building client."""


def _normalise_tree_version(entry: str) -> str | None:
    base, _ext = os.path.splitext(entry)
    parts = [part for part in re.split(r"[_.-]", base) if part]
    if not parts or not all(part.isdigit() for part in parts):
        return None
    return "_".join(parts)


def _tree_version_key(version: str) -> tuple[int, ...]:
    return tuple(int(part) if part.isdigit() else 0 for part in version.split("_"))

