"""Unit tests for pathfinding and reachability algorithms."""

import pytest
from src.pathfinding import (
    manhattan_distance,
    get_neighbors,
    a_star_search,
    bfs_search,
    get_reachable_cells,
    find_nearest_frontier
)


def test_manhattan_distance():
    assert manhattan_distance((0, 0), (3, 4)) == 7
    assert manhattan_distance((2, 5), (2, 5)) == 0
    assert manhattan_distance((5, 1), (1, 5)) == 8


def test_get_neighbors_respects_bounds_and_obstacles():
    bounds = (5, 5)
    obstacles = {(0, 1), (1, 0)}

    # At corner (0, 0), candidates are (-1, 0) out, (0, -1) out, (1, 0) obstacle, (0, 1) obstacle
    neighbors = get_neighbors((0, 0), bounds, obstacles)
    assert neighbors == []

    # At (2, 2) with no obstacles around
    neighbors = get_neighbors((2, 2), bounds, obstacles)
    assert set(neighbors) == {(1, 2), (3, 2), (2, 1), (2, 3)}


def test_a_star_search_finds_optimal_path():
    bounds = (10, 10)
    obstacles = {(1, 2), (2, 2), (3, 2)}
    start = (0, 2)
    goal = (4, 2)

    path = a_star_search(start, goal, bounds, obstacles)
    assert path is not None
    assert path[0] == start
    assert path[-1] == goal
    # Path must not pass through obstacles
    for p in path:
        assert p not in obstacles

    # Verify BFS finds identical length
    bfs_path = bfs_search(start, goal, bounds, obstacles)
    assert bfs_path is not None
    assert len(path) == len(bfs_path)


def test_a_star_unreachable_target():
    bounds = (5, 5)
    # Box in (4, 4)
    obstacles = {(3, 4), (4, 3)}
    path = a_star_search((0, 0), (4, 4), bounds, obstacles)
    assert path is None


def test_get_reachable_cells():
    bounds = (4, 4)
    # Partition row 2
    obstacles = {(2, 0), (2, 1), (2, 2), (2, 3)}
    reachable = get_reachable_cells((0, 0), bounds, obstacles)

    # Top two rows (8 cells) should be reachable
    assert len(reachable) == 8
    for r, c in reachable:
        assert r < 2


def test_find_nearest_frontier():
    bounds = (4, 4)
    obstacles = set()
    visited = {(0, 0), (0, 1), (1, 0)}

    frontier = find_nearest_frontier((0, 0), bounds, obstacles, visited)
    assert frontier is not None
    assert frontier not in visited
    # Frontier should be adjacent to visited cells, e.g., (0, 2) or (1, 1) or (2, 0)
    assert manhattan_distance((0, 0), frontier) == 2
