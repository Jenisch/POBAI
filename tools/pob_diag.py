import base64
import json
import os
import re
import zlib
from pathlib import Path
import xml.etree.ElementTree as ET

CANDIDATE_ROOTS = []
appdata = os.environ.get("APPDATA")
if appdata:
    CANDIDATE_ROOTS.append(Path(appdata) / "Path of Building Community")
localappdata = os.environ.get("LOCALAPPDATA")
if localappdata:
    CANDIDATE_ROOTS.append(Path(localappdata) / "Programs" / "Path of Building Community")
CANDIDATE_ROOTS.extend([
    Path(r"C:/Program Files/Path of Building Community"),
    Path(r"C:/Program Files (x86)/Path of Building Community"),
])

VERSION_FALLBACKS = ["3_26", "3_25", "3_24", "3_23"]
VERSION_PATTERN = re.compile(r"\b\d+_\d+\b")


def find_data_root():
    for root in CANDIDATE_ROOTS:
        if not root:
            continue
        data_dir = root / "Data"
        if data_dir.is_dir():
            return root
    return None


def extract_versions(data_dir: Path):
    versions = set()
    files_to_check = []
    json_path = data_dir / "TreeData.json"
    lua_path = data_dir / "TreeData.lua"
    if json_path.is_file():
        files_to_check.append(json_path)
    if lua_path.is_file():
        files_to_check.append(lua_path)
    if not files_to_check:
        files_to_check = list(data_dir.glob("**/TreeData.*"))
    for path in files_to_check:
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for match in VERSION_PATTERN.finditer(text):
            start = max(0, match.start() - 40)
            end = match.end() + 40
            context = text[start:end].lower()
            if "poe2" in context or "poe 2" in context:
                continue
            versions.add(match.group())
    if versions:
        return sorted(versions, key=lambda v: tuple(int(x) for x in v.split("_")), reverse=True)
    for fallback in VERSION_FALLBACKS:
        for path in files_to_check:
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if fallback in text:
                return [fallback]
    return VERSION_FALLBACKS[:]


def generate_xml(version: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
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


def encode_xml(xml_text: str) -> str:
    xml_bytes = xml_text.encode("utf-8")
    compressed = zlib.compress(xml_bytes)
    code = base64.b64encode(compressed).decode("ascii")
    inflated = zlib.decompress(base64.b64decode(code)).decode("utf-8")
    root = ET.fromstring(inflated)
    if root.tag != "PathOfBuilding":
        raise ValueError("Invalid root tag")
    node_elements = root.findall(".//Node")
    if not node_elements:
        raise ValueError("No nodes found in XML")
    return code


def read_log_tail(appdata_root: Path) -> str:
    log_path = appdata_root / "Logs" / "App.log"
    if not log_path.is_file():
        return "no log found"
    try:
        with log_path.open("r", encoding="utf-8", errors="ignore") as fh:
            lines = fh.readlines()
    except OSError:
        return "no log found"
    tail = lines[-200:]
    return "".join(tail) if tail else "no log found"


def main():
    data_root = find_data_root()
    appdata_root = Path(appdata) / "Path of Building Community" if appdata else None
    if not data_root:
        versions = VERSION_FALLBACKS[:]
    else:
        versions = extract_versions(data_root / "Data")
    version = versions[0] if versions else VERSION_FALLBACKS[0]
    xml_text = generate_xml(version)
    code = encode_xml(xml_text)

    output_dir = Path("outputs/pob_debug")
    output_dir.mkdir(parents=True, exist_ok=True)

    xml_path = output_dir / "pob_minimal.xml"
    xml_path.write_text(xml_text, encoding="utf-8")

    base64_path = output_dir / "pob_base64.txt"
    base64_path.write_text(code, encoding="utf-8")

    log_tail = "no log found"
    if appdata_root and appdata_root.is_dir():
        log_tail = read_log_tail(appdata_root)

    log_path = output_dir / "pob_log_tail.txt"
    log_content = log_tail if log_tail.endswith("\n") else log_tail + "\n"
    log_path.write_text(log_content, encoding="utf-8")

    print("BASE64:")
    print(code)
    print(f"FALLBACK_XML: {xml_path.resolve()}")
    print("LOG_TAIL_START")
    if log_tail == "no log found":
        print(log_tail)
    else:
        print(log_tail.rstrip("\n"))
    print("LOG_TAIL_END")


if __name__ == "__main__":
    main()
