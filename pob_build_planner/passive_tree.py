"""Utilities for working with the Path of Exile passive tree data."""

from __future__ import annotations

import json
from collections import deque
from functools import lru_cache
from importlib import resources
from typing import Iterable, Sequence

_TREE_RESOURCE = "data_files/passive_tree_3_24.json"


@lru_cache(maxsize=None)
def _load_tree() -> dict[str, object]:
    """Load and normalise the passive tree data from the embedded JSON file."""

    with resources.files(__package__).joinpath(_TREE_RESOURCE).open(  # type: ignore[attr-defined]
        "r", encoding="utf-8"
    ) as handle:
        raw = json.load(handle)

    nodes: dict[int, dict[str, object]] = {}
    name_map: dict[str, int] = {}
    for key, value in raw["nodes"].items():
        node_id = int(key)
        out_edges = [int(edge) for edge in value.get("out", [])]
        in_edges = [int(edge) for edge in value.get("in", [])]
        name = value.get("name")
        nodes[node_id] = {
            "out": out_edges,
            "in": in_edges,
            "name": name,
        }
        if name:
            name_map[name] = node_id

    class_ids = {key: int(value) for key, value in raw["class_ids"].items()}
    ascendancy_ids = {key: int(value) for key, value in raw["ascendancy_ids"].items()}
    class_starts = {key: int(value) for key, value in raw["class_starts"].items()}
    ascendancy_starts = {key: int(value) for key, value in raw["ascendancy_starts"].items()}

    return {
        "nodes": nodes,
        "name_map": name_map,
        "class_ids": class_ids,
        "ascendancy_ids": ascendancy_ids,
        "class_starts": class_starts,
        "ascendancy_starts": ascendancy_starts,
    }


def _shortest_path(nodes: dict[int, dict[str, object]], start: int, target: int) -> list[int]:
    if start == target:
        return [start]

    queue: deque[int] = deque([start])
    previous: dict[int, int | None] = {start: None}

    while queue:
        current = queue.popleft()
        data = nodes[current]
        neighbours: Iterable[int] = [
            *(data.get("out", [])),
            *(data.get("in", [])),
        ]
        for neighbour in neighbours:
            if neighbour in previous:
                continue
            previous[neighbour] = current
            if neighbour == target:
                path: list[int] = [neighbour]
                cursor = current
                while cursor is not None:
                    path.append(cursor)
                    cursor = previous[cursor]
                path.reverse()
                return path
            queue.append(neighbour)

    return []


def generate_tree_spec(
    base_class: str,
    ascendancy: str,
    notables: Sequence[str],
    ascendancy_notables: Sequence[str] | None = None,
) -> dict[str, object]:
    """Return class identifiers and allocated node ids for the requested build."""

    tree = _load_tree()
    nodes = tree["nodes"]
    name_map: dict[str, int] = tree["name_map"]  # type: ignore[assignment]

    try:
        class_id = tree["class_ids"][base_class]
    except KeyError as exc:  # pragma: no cover - defensive
        raise KeyError(f"Unknown base class '{base_class}'") from exc

    key = f"{base_class}::{ascendancy}"
    try:
        ascendancy_id = tree["ascendancy_ids"][key]
    except KeyError as exc:  # pragma: no cover - defensive
        raise KeyError(f"Unknown ascendancy '{ascendancy}' for class '{base_class}'") from exc

    try:
        start_node = tree["class_starts"][base_class.upper()]
    except KeyError as exc:  # pragma: no cover - defensive
        raise KeyError(f"No start node recorded for class '{base_class}'") from exc

    try:
        ascendancy_start = tree["ascendancy_starts"][ascendancy]
    except KeyError as exc:  # pragma: no cover - defensive
        raise KeyError(f"No ascendancy start recorded for '{ascendancy}'") from exc

    selections: set[int] = {start_node, ascendancy_start}

    def include(name: str, *, pivot: int) -> None:
        try:
            target = name_map[name]
        except KeyError as exc:
            raise KeyError(f"Passive node '{name}' not found in tree data") from exc

        path = _shortest_path(nodes, pivot, target)
        if not path:
            # Try walking from the class start if we pivoted from ascendancy and vice versa.
            fallback = _shortest_path(nodes, start_node if pivot == ascendancy_start else ascendancy_start, target)
            if not fallback:
                raise ValueError(f"Unable to connect passive node '{name}' to the tree")
            path = fallback
        selections.update(path)

    for name in notables:
        include(name, pivot=start_node)

    for name in ascendancy_notables or []:
        include(name, pivot=ascendancy_start)

    return {
        "class_id": class_id,
        "ascend_class_id": ascendancy_id,
        "nodes": sorted(selections),
    }
