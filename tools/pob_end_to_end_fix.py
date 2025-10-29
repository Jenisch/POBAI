#!/usr/bin/env python3
"""Generate a minimal PoB build using the highest installed tree version."""

from __future__ import annotations

import base64
import os
import pathlib
import re
import sys
import xml.etree.ElementTree as ET
import zlib


def _expand(path: str) -> pathlib.Path:
    expanded = os.path.expandvars(path)
    if "%" in expanded:
        # Environment variable did not resolve; fall back to original string without vars.
        expanded = path
    return pathlib.Path(expanded).expanduser()


def find_pob_root() -> pathlib.Path:
    candidates = []
    appdata = os.environ.get("APPDATA")
    if appdata:
        candidates.append(pathlib.Path(appdata) / "Path of Building Community")
    candidates.append(_expand(r"%APPDATA%\Path of Building Community"))
    localappdata = os.environ.get("LOCALAPPDATA")
    if localappdata:
        candidates.append(pathlib.Path(localappdata) / "Programs" / "Path of Building Community")
    # Deduplicate while preserving order
    seen = set()
    ordered: list[pathlib.Path] = []
    for cand in candidates:
        resolved = cand.resolve()
        if resolved not in seen:
            ordered.append(resolved)
            seen.add(resolved)
    for candidate in ordered:
        treedata = candidate / "TreeData"
        if treedata.exists():
            return candidate
    raise FileNotFoundError(
        "Unable to locate Path of Building Community TreeData directory. Checked: "
        + ", ".join(str(c) for c in ordered)
    )


def detect_highest_version(treedata_root: pathlib.Path) -> str:
    version_pattern = re.compile(r"^\d+_\d+$")
    versions = [
        entry.name
        for entry in sorted(treedata_root.iterdir())
        if entry.is_dir() and version_pattern.match(entry.name)
    ]
    if not versions:
        raise RuntimeError(f"No passive-tree versions found in {treedata_root}")

    def sort_key(version: str) -> tuple[int, int]:
        major_str, minor_str = version.split("_")
        return (int(major_str), int(minor_str))

    versions.sort(key=sort_key)
    return versions[-1]


def build_xml(version: str) -> str:
    return (
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
        "<PathOfBuilding>\n"
        "  <Build level=\"90\" targetVersion=\"{ver}\" className=\"Ranger\" ascendClassName=\"Deadeye\"/>\n"
        "  <Tree>\n"
        "    <Spec treeVersion=\"{ver}\">\n"
        "      <Nodes>\n"
        "        <Node id=\"40479\"/>\n"
        "        <Node id=\"29534\"/>\n"
        "      </Nodes>\n"
        "    </Spec>\n"
        "  </Tree>\n"
        "</PathOfBuilding>\n"
    ).format(ver=version)


def encode_build(xml_text: str) -> str:
    xml_bytes = xml_text.encode("utf-8")
    compressed = zlib.compress(xml_bytes)
    encoded = base64.b64encode(compressed).decode("ascii")
    roundtrip = zlib.decompress(base64.b64decode(encoded)).decode("utf-8")
    root = ET.fromstring(roundtrip)
    if root.tag != "PathOfBuilding":
        raise ValueError(f"Unexpected XML root: {root.tag}")
    if root.find("./Tree/Spec/Nodes/Node") is None:
        raise ValueError("No nodes found in generated XML")
    return encoded


def main() -> int:
    try:
        pob_root = find_pob_root()
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    treedata_root = pob_root / "TreeData"
    try:
        version = detect_highest_version(treedata_root)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    xml_text = build_xml(version)
    try:
        code = encode_build(xml_text)
    except Exception as exc:  # noqa: BLE001
        print(f"Failed to encode build: {exc}", file=sys.stderr)
        return 1

    builds_dir = pob_root / "Builds"
    builds_dir.mkdir(parents=True, exist_ok=True)
    xml_out = builds_dir / f"deadeye_demo_{version}.xml"
    xml_out.write_text(xml_text, encoding="utf-8")

    out_dir = pathlib.Path("outputs") / "pob_debug"
    out_dir.mkdir(parents=True, exist_ok=True)
    code_path = out_dir / f"code_{version}.txt"
    code_path.write_text(code, encoding="utf-8")

    print("CODES:")
    print(f"{version}: {code}")
    print("FILES:")
    print(f"{version}: {xml_out.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
