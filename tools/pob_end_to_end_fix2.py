#!/usr/bin/env python3
"""Generate and export a minimal PoB build using the highest installed tree version."""

import os
import re
import zlib
import base64
import pathlib
import xml.etree.ElementTree as ET


def main() -> int:
    appdata = os.path.expandvars(r"%APPDATA%")
    if "%" in appdata:
        env_value = os.environ.get("APPDATA")
        if not env_value:
            raise RuntimeError(
                "APPDATA environment variable is not set or could not be expanded"
            )
        appdata = env_value

    pob_root = pathlib.Path(appdata) / "Path of Building Community"
    treedata_root = pob_root / "TreeData"
    if not treedata_root.exists():
        raise FileNotFoundError(f"TreeData not found at {treedata_root}")

    versions = [
        entry.name
        for entry in treedata_root.iterdir()
        if entry.is_dir() and re.fullmatch(r"\d+_\d+", entry.name)
    ]
    if not versions:
        raise RuntimeError("No passive-tree versions found (e.g. 3_26)")

    def vkey(text: str) -> tuple[int, int]:
        major, minor = text.split("_")
        return int(major), int(minor)

    ver = sorted(versions, key=vkey)[-1]

    xml_text = f'''<?xml version="1.0" encoding="UTF-8"?>
<PathOfBuilding>
  <Build level="90" targetVersion="{ver}" className="Ranger" ascendClassName="Deadeye"
         classId="2" ascendClassId="0" bandit="None" pantheonMajorGod="Lunaris" pantheonMinorGod="Garukhan"/>
  <Tree>
    <Spec treeVersion="{ver}" classId="2" ascendClassId="0">
      <Nodes>
        <Node id="40479"/>
        <Node id="29534"/>
      </Nodes>
    </Spec>
    <Spec treeVersion="{ver}" classId="2" ascendClassId="0">
      <Nodes/>
    </Spec>
  </Tree>
  <Skills/>
  <Items/>
</PathOfBuilding>
'''

    xml_bytes = xml_text.encode("utf-8")
    code = base64.b64encode(zlib.compress(xml_bytes)).decode("ascii")

    roundtrip_xml = zlib.decompress(base64.b64decode(code)).decode("utf-8")
    root = ET.fromstring(roundtrip_xml)
    if root.tag != "PathOfBuilding":
        raise ValueError("Decoded XML did not have the expected root element")
    if root.find("./Tree/Spec") is None:
        raise ValueError("Decoded XML did not contain a Tree/Spec element")

    builds_dir = pob_root / "Builds"
    builds_dir.mkdir(parents=True, exist_ok=True)
    xml_out = builds_dir / f"deadeye_demo_{ver}_fixed.xml"
    xml_out.write_text(xml_text, encoding="utf-8")

    out_dir = pathlib.Path("outputs") / "pob_debug"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"code_{ver}_fixed.txt").write_text(code + "\n", encoding="utf-8")

    print("CODES:")
    print(f"{ver}: {code}")
    print("FILES:")
    print(f"{ver}: {xml_out.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
