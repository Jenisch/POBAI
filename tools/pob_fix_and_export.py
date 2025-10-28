import base64
import os
import re
import shutil
import zlib
from pathlib import Path
import xml.etree.ElementTree as ET

CANDIDATE_VERSIONS = ["3_26", "3_25", "3_24", "3_23"]


def get_appdata_root() -> Path | None:
    appdata = os.environ.get("APPDATA")
    if not appdata:
        return None
    return Path(appdata) / "Path of Building Community"


def normalize_settings(appdata_root: Path | None) -> None:
    if not appdata_root:
        return
    settings_path = appdata_root / "Settings.xml"
    if not settings_path.is_file():
        return
    try:
        original = settings_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return
    replaced = re.sub(r"poe2", "PoE1", original, flags=re.IGNORECASE)
    if replaced != original:
        try:
            settings_path.write_text(replaced, encoding="utf-8")
        except OSError:
            pass


def wipe_caches(appdata_root: Path | None) -> None:
    if not appdata_root:
        return
    for relative in ["TreeData", Path("Builds") / "BuildCache"]:
        target = appdata_root / relative
        if target.exists():
            shutil.rmtree(target, ignore_errors=True)


def candidate_roots(appdata_root: Path | None) -> list[Path]:
    roots: list[Path] = []
    if appdata_root:
        roots.append(appdata_root)
    localappdata = os.environ.get("LOCALAPPDATA")
    if localappdata:
        roots.append(Path(localappdata) / "Programs" / "Path of Building Community")
    roots.extend(
        [
            Path(r"C:/Program Files/Path of Building Community"),
            Path(r"C:/Program Files (x86)/Path of Building Community"),
        ]
    )
    return roots


def data_files_for_root(root: Path) -> list[Path]:
    data_dir = root / "Data"
    if not data_dir.is_dir():
        return []
    files: list[Path] = []
    for name in ("TreeData.json", "TreeData.lua"):
        path = data_dir / name
        if path.is_file():
            files.append(path)
    if not files:
        files.extend(data_dir.glob("**/TreeData.*"))
    return files


def version_supported(version: str, data_paths: list[Path]) -> bool:
    if not data_paths:
        return False
    pattern = re.compile(re.escape(version))
    for path in data_paths:
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for match in pattern.finditer(text):
            start = max(0, match.start() - 80)
            end = match.end() + 80
            context = text[start:end].lower()
            if "poe2" in context or "poe 2" in context:
                continue
            return True
    return False


def choose_version(appdata_root: Path | None) -> str:
    roots = candidate_roots(appdata_root)
    for root in roots:
        if not root:
            continue
        files = data_files_for_root(root)
        if files:
            for version in CANDIDATE_VERSIONS:
                if version_supported(version, files):
                    return version
    return CANDIDATE_VERSIONS[0]


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


def encode_xml(xml_text: str) -> str:
    xml_bytes = xml_text.encode("utf-8")
    compressed = zlib.compress(xml_bytes)
    code = base64.b64encode(compressed).decode("ascii")
    inflated = zlib.decompress(base64.b64decode(code)).decode("utf-8")
    root = ET.fromstring(inflated)
    if root.tag != "PathOfBuilding":
        raise ValueError("Invalid root element")
    if not root.findall(".//Node"):
        raise ValueError("Missing nodes in XML")
    return code


def copy_to_builds(xml_text: str, appdata_root: Path | None) -> Path | None:
    if not appdata_root:
        return None
    builds_dir = appdata_root / "Builds"
    target = builds_dir / "deadeye_demo.xml"
    try:
        builds_dir.mkdir(parents=True, exist_ok=True)
        target.write_text(xml_text, encoding="utf-8")
    except OSError:
        return target
    return target


def read_log_tail(appdata_root: Path | None) -> str:
    if not appdata_root:
        return "no log found"
    log_paths = [
        appdata_root / "Logs" / "App.log",
        appdata_root / "log.txt",
    ]
    for log_path in log_paths:
        if not log_path.is_file():
            continue
        try:
            with log_path.open("r", encoding="utf-8", errors="ignore") as fh:
                lines = fh.readlines()
        except OSError:
            continue
        tail = lines[-200:]
        return "".join(tail) if tail else "no log found"
    return "no log found"


def main() -> None:
    appdata_root = get_appdata_root()
    normalize_settings(appdata_root)
    wipe_caches(appdata_root)

    version = choose_version(appdata_root)
    xml_text = build_xml(version)
    code = encode_xml(xml_text)

    output_dir = Path("outputs/pob_debug")
    output_dir.mkdir(parents=True, exist_ok=True)

    xml_output = output_dir / "pob_minimal.xml"
    xml_output.write_text(xml_text, encoding="utf-8")

    code_output = output_dir / "pob_code.txt"
    code_output.write_text(code, encoding="utf-8")

    builds_path = copy_to_builds(xml_text, appdata_root)

    log_tail = read_log_tail(appdata_root)

    print("BASE64:")
    print(code)
    print(f"FALLBACK_XML: {xml_output.resolve()}")
    builds_str = str(builds_path.resolve()) if builds_path else "unavailable"
    print(f"POB_BUILDS_XML: {builds_str}")
    print("LOG_TAIL_START")
    if log_tail == "no log found":
        print("no log found")
    else:
        print(log_tail.rstrip("\n"))
    print("LOG_TAIL_END")


if __name__ == "__main__":
    main()
