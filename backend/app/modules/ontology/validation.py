"""Ontology integrity checks. Parent_of graphs must be acyclic."""

from __future__ import annotations

import uuid


def duplicate_names(names: list[str]) -> list[str]:
    seen: set[str] = set()
    dupes: list[str] = []
    for name in names:
        key = name.casefold().strip()
        if key in seen:
            dupes.append(name)
        seen.add(key)
    return dupes


def parent_cycles(edges: list[tuple[uuid.UUID, uuid.UUID]]) -> list[str]:
    """edges are (parent, child) for parent_of."""
    children: dict[uuid.UUID, list[uuid.UUID]] = {}
    for parent, child in edges:
        if parent == child:
            return [f"Self parent_of relation on {parent}"]
        children.setdefault(parent, []).append(child)
    visiting: set[uuid.UUID] = set()
    visited: set[uuid.UUID] = set()
    cycle_from: list[str] = []

    def dfs(node: uuid.UUID, stack: list[uuid.UUID]) -> None:
        if node in visiting:
            cycle_from.append(" → ".join(str(item) for item in [*stack, node]))
            return
        if node in visited:
            return
        visiting.add(node)
        stack.append(node)
        for nxt in children.get(node, []):
            dfs(nxt, stack)
            if cycle_from:
                return
        stack.pop()
        visiting.remove(node)
        visited.add(node)

    for node in {src for src, _ in edges} | {dst for _, dst in edges}:
        dfs(node, [])
        if cycle_from:
            return [f"parent_of cycle: {cycle_from[0]}"]
    return []
