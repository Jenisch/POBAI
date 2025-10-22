"""Utilities for generating and launching Path of Building profiles.

The helper in this module intentionally stays self-contained and only uses the
standard library so it can run in the same environments as the rest of the
project.  The encoded build strings are compatible with the Path of Building
Community fork (Path of Exile 1) and can be opened either via the registered
``poe://`` protocol handler or by launching the Path of Building executable
directly.
"""

from __future__ import annotations

from dataclasses import dataclass
import base64
import subprocess
import tempfile
import typing as t
import webbrowser
import xml.etree.ElementTree as ET
import zlib

from .data import Build


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

    class_name, ascendancy = _split_class_and_ascendancy(str(build.get("ascendancy", "")))
    root = ET.Element("PathOfBuilding")
    ET.SubElement(
        root,
        "Build",
        level=str(build.get("level", 90)),
        targetVersion=target_version,
        className=class_name,
        ascendClassName=ascendancy,
    )
    notes = ET.SubElement(root, "Notes")
    notes.text = _build_notes(build)

    tree = ET.SubElement(root, "Tree", activeSpec="1")
    ET.SubElement(
        tree,
        "Spec",
        className=class_name,
        ascendClassName=ascendancy,
        targetVersion=target_version,
        title="Generated Planner Spec",
    )

    skills_elem = ET.SubElement(root, "Skills")
    skills = t.cast(dict[str, t.Any], build.get("skill_gems", {}))
    main_skill = str(skills.get("main_skill", "")) or "Cyclone"
    main = ET.SubElement(
        skills_elem,
        "Skill",
        activeSkillId=main_skill.replace(" ", ""),
        enabled="true",
        slot="Main",
    )
    six_link = t.cast(t.Iterable[str], skills.get("six_link", []))
    for gem in six_link:
        ET.SubElement(
            main,
            "Gem",
            skillId=str(gem).replace(" ", ""),
            level="20",
            quality="20",
            enabled="true",
        )

    items_elem = ET.SubElement(root, "Items")
    items = t.cast(dict[str, str], build.get("gear", {}))
    for slot, description in items.items():
        item = ET.SubElement(items_elem, "Item", slot=slot.title())
        item.text = description

    xml_bytes = ET.tostring(root, encoding="utf-8")
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


@dataclass
class PathOfBuildingController:
    """Lightweight automation helper for the Path of Building desktop client."""

    executable_path: str | None = None
    open_mode: str = "protocol"

    def open_build(self, build: Build, *, use_cache: bool = True) -> str:
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
            if self.executable_path:
                subprocess.Popen([self.executable_path, temp_path])
            else:
                webbrowser.open(f"file://{temp_path}")
        else:
            raise ValueError(f"Unknown open mode '{self.open_mode}'")

        return code


__all__ = ["build_to_xml", "build_to_code", "PathOfBuildingController"]

