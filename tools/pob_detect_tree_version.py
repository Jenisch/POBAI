#!/usr/bin/env python3
"""Detect Path of Building Community passive tree versions."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Set

POB_CANDIDATE_ROOTS: Sequence[str] = (
    os.path.join(os.environ.get("APPDATA", ""), "Path of Building Community"),
    os.path.join(
        os.environ.get("LOCALAPPDATA", ""),
        "Programs",
        "Path of Building Community",
    ),
    r"C:\\Program Files\\Path of Building Community",
    r"C:\\Program Files (x86)\\Path of Building Community",
)

VERSION_PATTERN = re.compile(r"\b\d+_\d+\b")
POE2_PATTERN = re.compile(r"poe2|pathofexile2", re.IGNORECASE)


def resolve_candidate_paths() -> List[Path]:
    """Return candidate PoB roots that contain a Data directory."""
    paths: List[Path] = []
    for raw in POB_CANDIDATE_ROOTS:
        if not raw:
            continue
        root = Path(raw).expanduser()
        data_dir = root / "Data"
        if data_dir.is_dir():
            paths.append(root)
    return paths


def iter_tree_files(data_dir: Path) -> Iterable[Path]:
    """Yield files that may contain tree version information."""
    direct_candidates = [
        data_dir / "TreeData.json",
        data_dir / "TreeData.lua",
    ]
    for path in direct_candidates:
        if path.is_file():
            yield path
    tree_data_dir = data_dir / "TreeData"
    if tree_data_dir.is_dir():
        for pattern in ("*.json", "*.lua"):
            for path in tree_data_dir.glob(pattern):
                if path.is_file():
                    yield path


def extract_versions_from_text(text: str) -> Set[str]:
    """Extract PoE1 tree version strings from text content."""
    versions: Set[str] = set()
    for match in VERSION_PATTERN.finditer(text):
        start, end = match.span()
        line_start = text.rfind("\n", 0, start)
        line_end = text.find("\n", end)
        if line_start == -1:
            line_start = 0
        else:
            line_start += 1
        if line_end == -1:
            line_end = len(text)
        line = text[line_start:line_end]
        if POE2_PATTERN.search(line):
            continue
        versions.add(match.group(0))
    return versions


def extract_versions_from_file(path: Path) -> Set[str]:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = path.read_text(encoding="utf-8", errors="ignore")
    versions = extract_versions_from_text(text)
    if versions:
        return versions

    # Attempt JSON parsing for structured filtering when regex search failed.
    if path.suffix.lower() == ".json":
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return versions
        return extract_versions_from_json(data)
    return versions


def extract_versions_from_json(data: object) -> Set[str]:
    results: Set[str] = set()
    if isinstance(data, dict):
        for key, value in data.items():
            key_str = str(key)
            if POE2_PATTERN.search(key_str):
                continue
            results.update(extract_versions_from_json(value))
    elif isinstance(data, list):
        for item in data:
            results.update(extract_versions_from_json(item))
    elif isinstance(data, str):
        if VERSION_PATTERN.fullmatch(data) and not POE2_PATTERN.search(data):
            results.add(data)
    return results


def sort_versions(versions: Iterable[str]) -> List[str]:
    def version_key(version: str) -> tuple[int, int]:
        major_str, minor_str = version.split("_", 1)
        return (int(major_str), int(minor_str))

    return sorted(versions, key=version_key)


def main() -> None:
    roots = resolve_candidate_paths()
    versions_found: Set[str] = set()
    for root in roots:
        data_dir = root / "Data"
        for file_path in iter_tree_files(data_dir):
            versions_found.update(extract_versions_from_file(file_path))

    sorted_versions = sort_versions(versions_found)
    highest: Optional[str] = sorted_versions[-1] if sorted_versions else None

    output_lines = [
        f"TREE_VERSIONS_FOUND: {sorted_versions}",
        f"HIGHEST_VERSION: {highest if highest is not None else 'none'}",
    ]
    print("\n".join(output_lines))

    output_dir = Path("outputs") / "pob_debug"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "tree_versions.txt"
    output_file.write_text("\n".join(output_lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
