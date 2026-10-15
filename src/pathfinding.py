"""Pathfinding algorithms for grid navigation."""

from __future__ import annotations
import heapq
from collections import deque
from typing import List, Tuple, Optional, Set, Dict

Coord = Tuple[int, int]


def manhattan_distance(a: Coord, b: Coord) -> int:
    """Compute Manhattan (L1) distance between two grid points."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def get_neighbors(
    pos: Coord,
    bounds: Tuple[int, int],
    obstacles: Set[Coord]
) -> List[Coord]:
    """Return traversable cardinal neighbors within bounds."""
    rows, cols = bounds
    r, c = pos
    candidates = [
        (r - 1, c),  # UP
        (r + 1, c),  # DOWN
        (r, c - 1),  # LEFT
        (r, c + 1),  # RIGHT
    ]
    return [
        (nr, nc)
        for nr, nc in candidates
        if 0 <= nr < rows and 0 <= nc < cols and (nr, nc) not in obstacles
    ]


def a_star_search(
    start: Coord,
    goal: Coord,
    bounds: Tuple[int, int],
    obstacles: Set[Coord]
) -> Optional[List[Coord]]:
    """
    A* algorithm to find the optimal path from start to goal.
    Returns a list of coordinates including start and goal, or None if no path exists.
    """
    if start == goal:
        return [start]
    if goal in obstacles:
        return None

    # Priority queue stores: (f_score, h_score, current_node)
    open_set: List[Tuple[float, int, Coord]] = []
    initial_h = manhattan_distance(start, goal)
    heapq.heappush(open_set, (initial_h, initial_h, start))

    came_from: Dict[Coord, Coord] = {}
    g_score: Dict[Coord, float] = {start: 0.0}

    while open_set:
        _, _, current = heapq.heappop(open_set)

        if current == goal:
            # Reconstruct path
            path: List[Coord] = [current]
            while current in came_from:
                current = came_from[current]
                path.append(current)
            path.reverse()
            return path

        for neighbor in get_neighbors(current, bounds, obstacles):
            tentative_g = g_score[current] + 1.0

            if tentative_g < g_score.get(neighbor, float("inf")):
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                h = manhattan_distance(neighbor, goal)
                f = tentative_g + h
                heapq.heappush(open_set, (f, h, neighbor))

    return None


def bfs_search(
    start: Coord,
    goal: Coord,
    bounds: Tuple[int, int],
    obstacles: Set[Coord]
) -> Optional[List[Coord]]:
    """BFS shortest path search on unweighted 4-connected grid."""
    if start == goal:
        return [start]
    if goal in obstacles:
        return None

    queue: deque[Coord] = deque([start])
    came_from: Dict[Coord, Coord] = {}
    visited: Set[Coord] = {start}

    while queue:
        current = queue.popleft()
        if current == goal:
            path: List[Coord] = [current]
            while current in came_from:
                current = came_from[current]
                path.append(current)
            path.reverse()
            return path

        for neighbor in get_neighbors(current, bounds, obstacles):
            if neighbor not in visited:
                visited.add(neighbor)
                came_from[neighbor] = current
                queue.append(neighbor)

    return None


def get_reachable_cells(
    start: Coord,
    bounds: Tuple[int, int],
    obstacles: Set[Coord]
) -> Set[Coord]:
    """Return all cells reachable from start via BFS flood fill."""
    if start in obstacles:
        return set()

    visited: Set[Coord] = {start}
    queue: deque[Coord] = deque([start])

    while queue:
        current = queue.popleft()
        for neighbor in get_neighbors(current, bounds, obstacles):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)

    return visited


def find_nearest_frontier(
    start: Coord,
    bounds: Tuple[int, int],
    known_obstacles: Set[Coord],
    visited_cells: Set[Coord]
) -> Optional[Coord]:
    """
    Find the closest unvisited reachable cell to start using BFS.
    Returns coordinate or None if no reachable unvisited cells remain.
    """
    queue: deque[Coord] = deque([start])
    seen: Set[Coord] = {start}

    while queue:
        current = queue.popleft()
        if current not in visited_cells and current not in known_obstacles:
            return current

        for neighbor in get_neighbors(current, bounds, known_obstacles):
            if neighbor not in seen:
                seen.add(neighbor)
                queue.append(neighbor)

    return None
