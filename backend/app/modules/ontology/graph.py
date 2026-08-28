"""Bounded skill-graph traversal. Matching, potential, and career paths share this."""

from __future__ import annotations

import uuid
from collections import deque


class SkillGraph:
    def __init__(
        self,
        *,
        children: dict[uuid.UUID, tuple[uuid.UUID, ...]],
        parents: dict[uuid.UUID, tuple[uuid.UUID, ...]],
        related: dict[uuid.UUID, tuple[uuid.UUID, ...]],
        max_depth: int,
        similar: dict[uuid.UUID, tuple[uuid.UUID, ...]] | None = None,
    ) -> None:
        self.children = children
        self.parents = parents
        self.related = related
        self.similar = similar or {}
        self.max_depth = max(1, max_depth)

    def child_ids(self, skill_id: uuid.UUID) -> tuple[uuid.UUID, ...]:
        return self.children.get(skill_id, ())

    def parent_ids(self, skill_id: uuid.UUID) -> tuple[uuid.UUID, ...]:
        return self.parents.get(skill_id, ())

    def related_ids(self, skill_id: uuid.UUID) -> tuple[uuid.UUID, ...]:
        return self.related.get(skill_id, ())

    def similar_ids(self, skill_id: uuid.UUID) -> tuple[uuid.UUID, ...]:
        return self.similar.get(skill_id, ())

    def is_descendant(self, ancestor: uuid.UUID, node: uuid.UUID) -> bool:
        return self.hops(self.children, ancestor, node) is not None

    def is_ancestor(self, descendant: uuid.UUID, node: uuid.UUID) -> bool:
        return self.hops(self.parents, descendant, node) is not None

    def hops(
        self,
        adjacency: dict[uuid.UUID, tuple[uuid.UUID, ...]],
        start: uuid.UUID,
        goal: uuid.UUID,
    ) -> int | None:
        return self._bounded_reach(adjacency, start, goal)

    def hop_kind(self, start: uuid.UUID, goal: uuid.UUID) -> str | None:
        """Direct-edge type from start toward goal. Not a match score."""
        if start == goal:
            return "exact"
        if goal in self.similar_ids(start):
            return "similar"
        if goal in self.related_ids(start):
            return "related"
        if goal in self.child_ids(start) or self.hops(self.children, start, goal) == 1:
            return "child"
        if goal in self.parent_ids(start) or self.hops(self.parents, start, goal) == 1:
            return "parent"
        return None

    def shortest_path(self, start: uuid.UUID, goal: uuid.UUID) -> list[uuid.UUID] | None:
        if start == goal:
            return [start]
        seen = {start}
        queue: deque[list[uuid.UUID]] = deque([[start]])
        while queue:
            path = queue.popleft()
            if len(path) - 1 >= self.max_depth:
                continue
            current = path[-1]
            neighbors = (
                *self.children.get(current, ()),
                *self.parents.get(current, ()),
                *self.related.get(current, ()),
                *self.similar.get(current, ()),
            )
            for nxt in neighbors:
                if nxt in seen:
                    continue
                seen.add(nxt)
                nxt_path = [*path, nxt]
                if nxt == goal:
                    return nxt_path
                queue.append(nxt_path)
        return None

    def _bounded_reach(
        self,
        adjacency: dict[uuid.UUID, tuple[uuid.UUID, ...]],
        start: uuid.UUID,
        goal: uuid.UUID,
    ) -> int | None:
        if start == goal:
            return 0
        seen = {start}
        queue: deque[tuple[uuid.UUID, int]] = deque([(start, 0)])
        while queue:
            node, depth = queue.popleft()
            if depth >= self.max_depth:
                continue
            for nxt in adjacency.get(node, ()):
                if nxt in seen:
                    continue
                if nxt == goal:
                    return depth + 1
                seen.add(nxt)
                queue.append((nxt, depth + 1))
        return None
