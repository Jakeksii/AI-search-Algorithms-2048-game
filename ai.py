import math
import settings
from game import DIRECTIONS

# Spawn chances based on official 2048 rules (90% for 2, 10% for 4)
SPAWN_CHANCES = [(2, 0.9), (4, 0.1)]

# Snake pattern matrix: guides tiles in a descending order towards the top-left corner
WEIGHT_MATRIX = [
    [2048, 1024, 512, 256],
    [16, 32, 64, 128],
    [8, 4, 2, 1],
    [0.1, 0.2, 0.5, 0.8]
]

def choose_move(game):
    # Dynamic search depth: search deeper if the board gets crowded
    empty_spots = len(game.empty_cells())
    if empty_spots <= settings.CROWDED_THRESHOLD:
        depth = settings.DEPTH_CROWDED_BOARD
    else:
        depth = settings.DEPTH_OPEN_BOARD

    best_move = None
    best_score = -math.inf

    for direction in DIRECTIONS:
        # Clone board and test move without spawning a tile yet
        child = game.clone()
        if not child.move(direction, spawn=False):
            continue  # Move is illegal (didn't change anything)

        # Start expectimax: our move is depth 1, so chance node gets depth - 1
        score = chance_node(child, depth - 1)
        if score > best_score:
            best_score = score
            best_move = direction

    return best_move


def chance_node(game, depth):
    empty = game.empty_cells()
    # Base case: depth limit reached or no space left to spawn
    if depth == 0 or len(empty) == 0:
        return evaluate_board(game)

    # Calculate average expected value across all possible spawns
    total_expected = 0.0
    for r, c in empty:
        for tile_val, prob in SPAWN_CHANCES:
            child = game.clone()
            child.board[r][c] = tile_val
            total_expected += prob * max_node(child, depth)

    return total_expected / len(empty)


def max_node(game, depth):
    best_score = -math.inf

    for direction in DIRECTIONS:
        child = game.clone()
        if not child.move(direction, spawn=False):
            continue
        # Game's turn next (spawn)
        score = chance_node(child, depth - 1)
        best_score = max(best_score, score)

    # If no moves are possible, this path leads to game over
    if best_score == -math.inf:
        return evaluate_board(game) - settings.GAME_OVER_PENALTY

    return best_score


def evaluate_board(game):
    board = game.board
    empty_cells = len(game.empty_cells())

    # 1. Positional score using our snake pattern grid
    matrix_score = 0.0
    for r in range(4):
        for c in range(4):
            val = board[r][c]
            if val > 0:
                matrix_score += val * WEIGHT_MATRIX[r][c]

    # 2. Count adjacent matching tiles (opportunities to merge)
    merges_available = 0
    for r in range(4):
        for c in range(4):
            val = board[r][c]
            if val == 0:
                continue
            if c + 1 < 4 and board[r][c + 1] == val:
                merges_available += 1
            if r + 1 < 4 and board[r + 1][c] == val:
                merges_available += 1

    # 3. Corner check: give extra bonus if max tile is safely in top-left
    max_val = game.max_tile()
    corner_bonus = max_val if board[0][0] == max_val else 0

    # Combine everything using weights from settings.py
    total_score = (
        (matrix_score * settings.WEIGHT_MATRIX_PATTERN)
        + (empty_cells * settings.WEIGHT_EMPTY)
        + (merges_available * settings.WEIGHT_MERGES)
        + (corner_bonus * settings.WEIGHT_CORNER)
    )

    return total_score