# 2048

A playable 2048 in Python with tkinter, an expectimax machine player, and a
parallel benchmark for measuring the player. Requires Python 3.10+ and nothing
outside the standard library.

```bash
python main.py
```

Controls: arrow keys or WASD to move, R for a new game. The game is won when
a tile of `TARGET_TILE` (4096 by default) appears; it is lost when no move is
left. Either way the board freezes until you press R.

Buttons:

- **AI** hands the current game to `AI.choose_move` and keeps calling it
  after each move until you press the button again or the game ends. You can
  play a while yourself and then let the AI take over.
- **New Game** starts over.
- **Benchmark** runs the benchmark (see below) while the game window stays
  playable. Results print to the console the game was started from.

## Files

| File | What it is |
|---|---|
| `game.py` | The engine. No GUI code. `Game` holds the board and score and provides `clone()`, `legal_moves()`, `move(direction, spawn=True)`, `spawn_tile()`, `empty_cells()`, `is_over()`, `has_won(target)`, `max_tile()`. |
| `AI.py` | The machine player: a depth-limited expectimax search with a heuristic evaluation. `choose_move(game)` returns `"up"`, `"down"`, `"left"` or `"right"`. |
| `main.py` | The tkinter window. |
| `benchmark.py` | Plays seeded games in parallel and prints statistics. |
| `settings.py` | Every tweakable number and flag: target tile, search depth, heuristic weights, animation timing, benchmark settings. |
| `GUIDE.md` | How expectimax works here, what each heuristic term does, and how to tune and measure. |

## Benchmarking

```bash
python benchmark.py
```

Each game runs in its own process (the AI is pure Python, so threads would
share one core) and opens a small window so you can watch. A window closes
itself when its game is won or lost, its row is printed, and a summary
follows once every game is done: win rate at the target tile, share reaching
2048, average and median score, moves, and time per game.

Games are seeded, so the same settings give the same tile spawns every run;
only changes to the AI affect the results. The benchmark settings live in
`settings.py`: `GAMES`, `FIRST_SEED`, `WORKERS` (default one per CPU core),
`ANIMATE`, and the window size and layout.

## Writing your own player

`choose_move(game)` receives the live `Game`. Do not mutate it; clone it to
look ahead:

```python
child = game.clone()
if child.move("left", spawn=False):   # slide and merge, no random tile
    for r, c in child.empty_cells():  # expand chance nodes yourself if needed
        ...
```

`Game(seed=42)` gives reproducible tile spawns for experiments by hand:

```python
from game import Game
import AI

g = Game(seed=42)
while not g.is_over():
    g.move(AI.choose_move(g))
print(g.score, g.max_tile())
```
