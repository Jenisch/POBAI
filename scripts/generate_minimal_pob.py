"""Generate and print a minimal Path of Building code using detected tree version.

This script searches for an installed Path of Building Community directory, detects the
highest available passive tree version for Path of Exile 1, and generates a minimal
XML build containing two allocated passive nodes. The XML is compressed via raw zlib
(DEFLATE) and base64-encoded. The script prints the encoded string, saves the XML as a
fallback file for manual import, and appends the tail of the PoB log for diagnostics.
A round-trip validation ensures the generated code decodes back into a valid PoB XML
document. Additionally, the script ensures the PoB settings target Path of Exile 1
before generating the build.
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
SETTINGS_RELATIVE_PATH = Path("Path of Building Community") / "Settings.xml"
LOGS_RELATIVE_PATH = Path("Path of Building Community") / "Logs"


def ensure_poe1_settings() -> None:
    """Update the PoB settings file to target Path of Exile 1 if necessary."""

    appdata = os.environ.get("APPDATA")
    if not appdata:
        return

    settings_path = Path(appdata) / SETTINGS_RELATIVE_PATH
    if not settings_path.is_file():
        return

    try:
        content = settings_path.read_text(encoding="utf-8")
    except OSError:
        return

    lower = content.lower()
    if "poe2" not in lower and "path of exile 2" not in lower and "pathofexile2" not in lower:
        return

    modified = content
    replacements = [
        (r"(?i)path\s*of\s*exile\s*2", "Path of Exile"),
        (r"(?i)pathofexile2", "PathOfExile"),
        (r"(?i)poe2", "PoE"),
        (r"gameMode\s*=\s*\"?2\"?", 'gameMode="1"'),
        (r"gameVersion\s*=\s*\"?2\"?", 'gameVersion="1"'),
    ]
    for pattern, replacement in replacements:
        modified = re.sub(pattern, replacement, modified)

    if modified != content:
        try:
            settings_path.write_text(modified, encoding="utf-8")
        except OSError:
            pass


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
    appdata = os.environ.get("APPDATA")

    add(Path(program_files) / "Path of Building Community")
    add(Path(program_files_x86) / "Path of Building Community")
    if local_appdata:
        add(Path(local_appdata) / "Programs" / "Path of Building Community")
    if appdata:
        add(Path(appdata) / "Path of Building Community")

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
    """Extract PoE1 version strings that look like '3_24'."""

    versions = set()
    for match in re.finditer(r"\b\d+_\d+\b", text):
        start, end = match.span()
        window = text[max(0, start - 40): end + 40].lower()
        if any(token in window for token in ("poe2", "poe 2", "pathofexile2", "path of exile 2")):
            continue
        versions.add(match.group())
    return sorted(versions)


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


def version_exists_in_dir(pob_dir: Path, version: str) -> bool:
    data_dir = pob_dir / "Data"
    if not data_dir.is_dir():
        return False

    for extension in ("*.json", "*.lua"):
        for path in data_dir.rglob(extension):
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if version in extract_versions_from_text(text):
                return True
    return False


def choose_version(detected_versions: Sequence[str]) -> str:
    def version_key(version: str) -> Tuple[int, int]:
        major, minor = version.split("_")
        return int(major), int(minor)

    if detected_versions:
        return max(detected_versions, key=version_key)
    return FALLBACK_VERSIONS[0]


def choose_version_with_fallback(dirs: Sequence[Path], detected_versions: Sequence[str]) -> str:
    if detected_versions:
        return choose_version(detected_versions)

    for version in FALLBACK_VERSIONS:
        for pob_dir in dirs:
            if version_exists_in_dir(pob_dir, version):
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


def read_log_tail(lines: int = 200) -> List[str]:
    appdata = os.environ.get("APPDATA")
    if not appdata:
        return []

    logs_dir = Path(appdata) / LOGS_RELATIVE_PATH
    candidates = [logs_dir / "App.log", logs_dir / "log.txt"]
    for path in candidates:
        if path.is_file():
            try:
                content = path.read_text(encoding="utf-8", errors="ignore").splitlines()
            except OSError:
                continue
            return content[-lines:]
    return []


def main() -> int:
    ensure_poe1_settings()

    script_path = Path(__file__).resolve()
    dirs = candidate_directories(script_path)

    detected_versions: List[str] = []
    for pob_dir in dirs:
        versions = discover_tree_versions(pob_dir)
        if versions:
            detected_versions.extend(versions)

    version = choose_version_with_fallback(dirs, detected_versions)
    xml_text = build_xml(version)
    code = encode_xml(xml_text)
    validated_xml = validate_code(code)
    fallback_path = save_fallback(validated_xml)

    # Output: base64 code line, followed by fallback path line
    sys.stdout.write(code + "\n")
    sys.stdout.write(f"FALLBACK_XML:{fallback_path}\n")
    log_tail = read_log_tail()
    sys.stdout.write("LOG_TAIL_START\n")
    for line in log_tail:
        sys.stdout.write(f"{line}\n")
    sys.stdout.write("LOG_TAIL_END\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
