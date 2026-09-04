"""Expectimax player for 2048.

The GUI calls choose_move(game) once per turn while AI mode is on.

Expectimax is minimax for games with a random opponent. In 2048 the "opponent"
is the tile spawn: after every move the game places a 2 (90%) or a 4 (10%) in
a random empty cell. The spawn does not try to hurt us, so instead of assuming
the worst case (minimax) we average over the possibilities weighted by their
probability (expectation). The search tree therefore alternates between:

    MAX node     our turn: pick the direction with the highest value
    CHANCE node  the game's turn: average the value over every possible spawn

The tree grows very fast (4 moves x up to 16 cells x 2 values per ply), so we
stop after a few plies and estimate the position with a heuristic instead.
"""

from __future__ import annotations

import math

import settings
from game import DIRECTIONS, SIZE, Game

# Spawn probabilities from the rules (see Game.spawn_tile).
SPAWN_PROBABILITIES = ((2, 0.9), (4, 0.1))


def choose_move(game: Game) -> str | None:
    """Return the direction with the highest expectimax value."""
    # Search depth and heuristic weights live in settings.py.
    if len(game.empty_cells()) <= settings.CROWDED_THRESHOLD:
        depth = settings.DEPTH_CROWDED_BOARD
    else:
        depth = settings.DEPTH_OPEN_BOARD

    best_direction = None
    best_value = -math.inf
    for direction in DIRECTIONS:
        # Play the move on a copy so the real game is untouched. spawn=False
        # because the spawn is what the chance node below enumerates.
        child = game.clone()
        if not child.move(direction, spawn=False):
            continue  # the move would not change the board, so it is illegal
        # This root move is the first of `depth` moves we look ahead, so the
        # subtree below it has depth - 1 moves left.
        value = chance_value(child, depth - 1)
        if value > best_value:
            best_value, best_direction = value, direction
    return best_direction


def chance_value(game: Game, depth: int) -> float:
    """CHANCE node: the game is about to spawn a tile.

    `depth` is the number of our own moves still to search below this node.
    Returns the expected value over every (cell, tile value) the game could
    spawn. `game` is a private copy, so we place each candidate tile directly
    on its board and remove it again afterwards instead of cloning per child.
    """
    empty = game.empty_cells()
    if depth == 0 or not empty:
        # Either we have looked far enough, or the board is full (a spawn is
        # impossible, so the next thing that happens is our move on a full
        # board). In both cases estimate the position instead of searching.
        return evaluate(game)

    expected = 0.0
    for r, c in empty:
        for value, probability in SPAWN_PROBABILITIES:
            game.board[r][c] = value
            # Every empty cell is equally likely, so each (cell, value) pair
            # has probability P(value) / number_of_empty_cells.
            expected += probability * max_value(game, depth)
            game.board[r][c] = 0
    return expected / len(empty)


def max_value(game: Game, depth: int) -> float:
    """MAX node: our turn, with `depth` moves (including this one) to search.

    Returns the value of the best available move.
    """
    best = -math.inf
    for direction in DIRECTIONS:
        child = game.clone()
        if not child.move(direction, spawn=False):
            continue
        # After our move comes a spawn, so the child is a chance node. This
        # move used up one level of depth.
        best = max(best, chance_value(child, depth - 1))
    if best == -math.inf:
        # No legal move: the game is over in this branch. Score it far below
        # any live position so the search avoids it if it possibly can.
        return evaluate(game) - settings.GAME_OVER_PENALTY
    return best


def evaluate(game: Game) -> float:
    """Heuristic estimate of how good a board is for us (higher is better).

    The score is not a good guide on its own: two boards with the same score
    can be one move from death or wide open. Instead we reward the properties
    that experienced players maintain deliberately.
    """
    board = game.board
    # Work in log2 space so 1024 vs 512 counts the same as 4 vs 2. Empty
    # cells become 0.
    logs = [[math.log2(v) if v else 0.0 for v in row] for row in board]

    empty = sum(v == 0 for row in board for v in row)

    # Monotonicity: in each row and column the values should either only go
    # up or only go down. For each line we sum the drops in both directions
    # and take the smaller sum, so a perfectly sorted line costs nothing.
    # Monotone lines let tiles merge in order instead of getting trapped.
    monotonic = 0.0
    lines = [row for row in logs] + [[logs[r][c] for r in range(SIZE)] for c in range(SIZE)]
    for line in lines:
        increases = decreases = 0.0
        for a, b in zip(line, line[1:]):
            if a > b:
                decreases += a - b
            else:
                increases += b - a
        monotonic -= min(increases, decreases)

    # Smoothness: neighbouring tiles should have similar values, because
    # equal neighbours are exactly the ones that can merge. Sum the log
    # differences between every horizontal and vertical pair.
    smooth = 0.0
    for r in range(SIZE):
        for c in range(SIZE):
            if board[r][c] == 0:
                continue
            if c + 1 < SIZE and board[r][c + 1]:
                smooth -= abs(logs[r][c] - logs[r][c + 1])
            if r + 1 < SIZE and board[r + 1][c]:
                smooth -= abs(logs[r][c] - logs[r + 1][c])

    # Max tile in a corner: the standard strategy is to anchor the biggest
    # tile in a corner and build the rest in descending order from there.
    max_log = max(max(row) for row in logs)
    corners = (logs[0][0], logs[0][SIZE - 1], logs[SIZE - 1][0], logs[SIZE - 1][SIZE - 1])
    corner_bonus = max_log if max_log in corners else 0.0

    return (
        settings.WEIGHT_EMPTY * empty
        + settings.WEIGHT_MONOTONIC * monotonic
        + settings.WEIGHT_SMOOTH * smooth
        + settings.WEIGHT_MAX_IN_CORNER * corner_bonus
    )
