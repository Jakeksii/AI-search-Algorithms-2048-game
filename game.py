"""2048 game engine. No GUI code here; used by both main.py and player.py."""

from __future__ import annotations

import random
from dataclasses import dataclass

SIZE = 4
DIRECTIONS = ("up", "down", "left", "right")


@dataclass(frozen=True)
class TileMove:
    """One tile's movement during a move. Used by the GUI for animation."""

    src: tuple[int, int]  # (row, col) before the move
    dst: tuple[int, int]  # (row, col) after the move
    value: int  # tile value before any merge
    merged: bool  # True if this tile merged into the tile already at dst


class Game:
    """State of one 2048 game.

    Public API for search algorithms:
        game.board          4x4 list of lists, 0 = empty
        game.score          current score
        game.clone()        independent copy (safe to mutate)
        game.legal_moves()  list of directions that change the board
        game.move(d)        apply a move; returns True if the board changed
        game.move(d, spawn=False)  same, but without the random tile
        game.spawn_tile()   place a random tile (90% 2, 10% 4)
        game.empty_cells()  list of (row, col) that are empty
        game.is_over()      True when no legal moves remain
        game.has_won(t)     True when a tile of at least t (default 2048) exists
        game.max_tile()     largest tile value
    """

    def __init__(self, seed: int | None = None):
        self.rng = random.Random(seed)
        self.board: list[list[int]] = [[0] * SIZE for _ in range(SIZE)]
        self.score = 0
        self.last_moves: list[TileMove] = []
        self.spawn_tile()
        self.spawn_tile()

    # ---- copying -----------------------------------------------------------

    def clone(self) -> Game:
        other = Game.__new__(Game)
        # random.Random() would seed itself from the OS, which is slow when a
        # search clones thousands of times per move. Build it unseeded instead.
        other.rng = random.Random.__new__(random.Random)
        other.rng.setstate(self.rng.getstate())
        other.board = [row[:] for row in self.board]
        other.score = self.score
        other.last_moves = []
        return other

    # ---- queries -----------------------------------------------------------

    def empty_cells(self) -> list[tuple[int, int]]:
        return [(r, c) for r in range(SIZE) for c in range(SIZE) if self.board[r][c] == 0]

    def max_tile(self) -> int:
        return max(max(row) for row in self.board)

    def has_won(self, target: int = 2048) -> bool:
        return self.max_tile() >= target

    def legal_moves(self) -> list[str]:
        return [d for d in DIRECTIONS if self._would_change(d)]

    def is_over(self) -> bool:
        return not self.legal_moves()

    # ---- actions -----------------------------------------------------------

    def spawn_tile(self) -> None:
        empty = self.empty_cells()
        if not empty:
            return
        r, c = self.rng.choice(empty)
        self.board[r][c] = 4 if self.rng.random() < 0.1 else 2

    def move(self, direction: str, spawn: bool = True) -> bool:
        """Slide and merge tiles. Returns True if anything moved.

        A random tile is spawned afterwards unless spawn=False.
        Sets self.last_moves for animation.
        """
        changed = False
        gained = 0
        moves: list[TileMove] = []
        for line in self._lines(direction):
            line_changed, line_gained, line_moves = self._slide_line(line)
            changed |= line_changed
            gained += line_gained
            moves.extend(line_moves)
        self.last_moves = moves
        if changed:
            self.score += gained
            if spawn:
                self.spawn_tile()
        return changed

    # ---- internals ---------------------------------------------------------

    @staticmethod
    def _lines(direction: str) -> list[list[tuple[int, int]]]:
        """Coordinates of each row/column, ordered from the wall tiles slide toward."""
        if direction == "left":
            return [[(r, c) for c in range(SIZE)] for r in range(SIZE)]
        if direction == "right":
            return [[(r, c) for c in reversed(range(SIZE))] for r in range(SIZE)]
        if direction == "up":
            return [[(r, c) for r in range(SIZE)] for c in range(SIZE)]
        if direction == "down":
            return [[(r, c) for r in reversed(range(SIZE))] for c in range(SIZE)]
        raise ValueError(f"unknown direction: {direction!r}")

    def _slide_line(self, coords: list[tuple[int, int]]):
        tiles = [(i, self.board[r][c]) for i, (r, c) in enumerate(coords) if self.board[r][c]]
        new = [0] * SIZE
        moves: list[TileMove] = []
        gained = 0
        dst = 0
        i = 0
        while i < len(tiles):
            src, value = tiles[i]
            if i + 1 < len(tiles) and tiles[i + 1][1] == value:
                new[dst] = value * 2
                gained += value * 2
                moves.append(TileMove(coords[src], coords[dst], value, False))
                moves.append(TileMove(coords[tiles[i + 1][0]], coords[dst], value, True))
                i += 2
            else:
                new[dst] = value
                moves.append(TileMove(coords[src], coords[dst], value, False))
                i += 1
            dst += 1
        changed = any(new[k] != self.board[r][c] for k, (r, c) in enumerate(coords))
        for k, (r, c) in enumerate(coords):
            self.board[r][c] = new[k]
        return changed, gained, moves

    def _would_change(self, direction: str) -> bool:
        for line in self._lines(direction):
            values = [self.board[r][c] for r, c in line]
            seen_gap = False
            prev = 0
            for v in values:
                if v == 0:
                    seen_gap = True
                else:
                    if seen_gap or v == prev:
                        return True
                    prev = v
        return False

    def __str__(self) -> str:
        width = len(str(self.max_tile()))
        rows = [" ".join(f"{v or '.':>{width}}" for v in row) for row in self.board]
        return "\n".join(rows) + f"\nscore: {self.score}"
