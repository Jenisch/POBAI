"""Generate and print a minimal Path of Building code using detected tree version.

This script searches for an installed Path of Building Community directory, detects the
highest available passive tree version for Path of Exile 1, and generates a minimal
XML build containing two allocated passive nodes. The XML is compressed via raw zlib
(DEFLATE) and base64-encoded. The script prints the encoded string and saves the XML
as a fallback file for manual import. A round-trip validation ensures the generated
code decodes back into a valid PoB XML document.
"""
from __future__ import annotations

import base64
import json
import os
import re
import sys
import tempfile
import zlib
from pathlib import Path
from typing import List, Sequence, Tuple
import xml.etree.ElementTree as ET

FALLBACK_VERSIONS: Sequence[str] = ("3_26", "3_25", "3_24", "3_23")
NODE_IDS: Sequence[str] = ("40479", "29534")


def candidate_directories(script_path: Path) -> List[Path]:
    """Return potential Path of Building installation directories.

    The search includes standard Program Files locations, local app installs,
    and portable directories near the current script. Duplicate paths are
    removed while preserving order.
    """

    candidates: List[Path] = []

    def add(path: Path) -> None:
        path = path.resolve()
        if path not in candidates:
            candidates.append(path)

    program_files = os.environ.get("PROGRAMFILES", r"C:\\Program Files")
    program_files_x86 = os.environ.get("PROGRAMFILES(X86)", r"C:\\Program Files (x86)")
    local_appdata = os.environ.get("LOCALAPPDATA")

    add(Path(program_files) / "Path of Building Community")
    add(Path(program_files_x86) / "Path of Building Community")
    if local_appdata:
        add(Path(local_appdata) / "Programs" / "Path of Building Community")

    # Search for sibling folders matching the pattern under C:\ and %LOCALAPPDATA%\Programs
    search_roots: List[Path] = [Path(r"C:\\")]
    if local_appdata:
        search_roots.append(Path(local_appdata) / "Programs")

    for root in search_roots:
        if root.is_dir():
            for child in root.glob("Path of Building Community*"):
                add(child)

    # Portable folder next to the script (or its parent) containing a Data directory
    for base in [script_path.parent, script_path.parent.parent]:
        if base and base.exists():
            for child in base.iterdir():
                if child.is_dir() and child.name.lower().startswith("path of building community"):
                    add(child)
            if (base / "Data").is_dir():
                add(base)

    # Filter to directories that contain a Data sub-directory
    valid = [path for path in candidates if (path / "Data").is_dir()]
    return valid


def extract_versions_from_text(text: str) -> List[str]:
    """Extract version strings that look like '3_24'."""

    return sorted(set(re.findall(r"\b\d+_\d+\b", text)))


def parse_tree_data_json(path: Path) -> List[str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []

    versions: List[str] = []

    def walk(obj: object) -> None:
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key.lower().startswith("treeversion") and isinstance(value, (str, int, float)):
                    versions.append(str(value))
                walk(value)
        elif isinstance(obj, list):
            for item in obj:
                walk(item)

    walk(data)
    if not versions:
        versions.extend(extract_versions_from_text(json.dumps(data)))
    return versions


def parse_tree_data_lua(path: Path) -> List[str]:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []
    return extract_versions_from_text(text)


def discover_tree_versions(pob_dir: Path) -> List[str]:
    data_dir = pob_dir / "Data"
    if not data_dir.is_dir():
        return []

    versions: List[str] = []

    priority_files: Sequence[str] = ("TreeData.json", "TreeData.lua")
    for file_name in priority_files:
        file_path = data_dir / file_name
        if file_path.is_file():
            if file_name.lower().endswith(".json"):
                versions.extend(parse_tree_data_json(file_path))
            else:
                versions.extend(parse_tree_data_lua(file_path))

    if not versions:
        # Scan any JSON/LUA file for embedded versions
        for file_path in data_dir.rglob("*.json"):
            versions.extend(extract_versions_from_text(
                file_path.read_text(encoding="utf-8", errors="ignore")))
        if not versions:
            for file_path in data_dir.rglob("*.lua"):
                versions.extend(parse_tree_data_lua(file_path))

    unique_versions = sorted(set(v for v in versions if re.match(r"^\d+_\d+$", v)))
    return unique_versions


def choose_version(detected_versions: Sequence[str]) -> str:
    def version_key(version: str) -> Tuple[int, int]:
        major, minor = version.split("_")
        return int(major), int(minor)

    if detected_versions:
        return max(detected_versions, key=version_key)

    # Fallback search; return the first known fallback detected, otherwise the first entry
    for version in FALLBACK_VERSIONS:
        if version in detected_versions:
            return version
    return FALLBACK_VERSIONS[0]



def build_xml(version: str) -> str:
    node_lines = "\n".join(f"        <Node id=\"{node_id}\"/>" for node_id in NODE_IDS)
    return (
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
        "<PathOfBuilding>\n"
        f"  <Build level=\"90\" targetVersion=\"{version}\" className=\"Ranger\" ascendClassName=\"Deadeye\"/>\n"
        "  <Tree>\n"
        f"    <Spec treeVersion=\"{version}\">\n"
        "      <Nodes>\n"
        f"{node_lines}\n"
        "      </Nodes>\n"
        "    </Spec>\n"
        "  </Tree>\n"
        "</PathOfBuilding>\n"
    )


def encode_xml(xml_content: str) -> str:
    xml_bytes = xml_content.encode("utf-8")
    compressed = zlib.compress(xml_bytes)
    return base64.b64encode(compressed).decode("ascii")


def validate_code(code: str) -> str:
    xml_bytes = zlib.decompress(base64.b64decode(code))
    xml_text = xml_bytes.decode("utf-8")
    root = ET.fromstring(xml_text)
    if root.tag != "PathOfBuilding":
        raise ValueError("Decoded XML root tag is not 'PathOfBuilding'")
    nodes = root.findall(".//Node")
    if not nodes:
        raise ValueError("Decoded XML is missing passive nodes")
    return xml_text


def save_fallback(xml_text: str) -> Path:
    temp_dir = Path(tempfile.gettempdir())
    fallback_path = temp_dir / "pob_minimal.xml"
    fallback_path.write_text(xml_text, encoding="utf-8")
    return fallback_path


def main() -> int:
    script_path = Path(__file__).resolve()
    dirs = candidate_directories(script_path)

    detected_versions: List[str] = []
    for pob_dir in dirs:
        versions = discover_tree_versions(pob_dir)
        if versions:
            detected_versions.extend(versions)

    version = choose_version(detected_versions)
    xml_text = build_xml(version)
    code = encode_xml(xml_text)
    validated_xml = validate_code(code)
    fallback_path = save_fallback(validated_xml)

    # Output: base64 code line, followed by fallback path line
    sys.stdout.write(code + "\n")
    sys.stdout.write(f"FALLBACK_XML:{fallback_path}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
