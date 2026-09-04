# Guide: expectimax for 2048

This guide explains what the player in `AI.py` does, why, and how to change
it. Everything it refers to by name is in `AI.py` or `settings.py`.

## 1. Why not minimax?

2048 has two "players": you, who choose a direction, and the game, which
drops a 2 or a 4 into a random empty cell after every move. Minimax would
treat the game as an adversary that always picks the worst spawn for you.
That is too pessimistic: the spawn is random, not hostile, and planning for
the single worst case makes the player timid and weak.

Expectimax replaces the adversary's *minimum* with an *expected value*: the
average over all possible spawns, weighted by how likely each one is. The
search tree alternates two kinds of node:

| Node | Whose turn | Value |
|---|---|---|
| MAX | ours | the best value among the legal moves |
| CHANCE | the game's | probability-weighted average over every possible spawn |

A spawn puts a 2 with probability 0.9 or a 4 with probability 0.1 into one of
the empty cells, each cell equally likely. So a CHANCE node with `k` empty
cells has `2k` children, and the child "value `v` in cell `c`" has
probability `P(v) / k`.

## 2. The search in `AI.py`

```
choose_move(game)                     root: try each direction
  └─ chance_value(child, depth-1)     average over spawns
       └─ max_value(board, depth)     best direction
            └─ chance_value(...)      ...until depth reaches 0
                 └─ evaluate(board)   heuristic estimate at the leaves
```

- `choose_move` plays each direction on a clone with `spawn=False`, because
  the spawn is exactly what the CHANCE node below it enumerates. Moves that
  do not change the board are illegal and skipped. It returns the direction
  whose CHANCE value is highest.
- `chance_value` loops over every empty cell and both tile values. It writes
  the candidate tile straight into the board, recurses, and erases it again.
  No cloning is needed at this level because the board is already a private
  copy.
- `max_value` clones per direction (the slide changes many cells, so a copy
  is simpler than undoing it) and takes the maximum. If no direction is
  legal, the game is over in that branch and the value is the heuristic
  minus `GAME_OVER_PENALTY`, so the search avoids that branch if it possibly
  can.
- `depth` counts *our* moves. Depth 2 means: my move, spawn, my move, spawn,
  evaluate.

### Cost

The root tries 4 directions, and every further level of depth multiplies the
tree by roughly `(2 × empty cells) spawns × 4 directions`. With 10 empty
cells that is 80 per level: depth 2 is about 320 leaves, depth 3 about
25,000, depth 4 about 2 million. Each leaf costs a clone, a slide and an
evaluation in pure Python, roughly 10,000 leaves per second, which is why
depth 3 is only used when the board is crowded and the tree is small.

## 3. The heuristic: `evaluate`

The leaves are scored by a weighted sum of four features. All tile values are
first converted to `log2`, so the gap between 1024 and 2048 counts the same as
the gap between 2 and 4. Higher is better.

| Feature | What it measures | Why it matters |
|---|---|---|
| `empty` | number of empty cells | Room to move and to merge. Running out of space is how games end. |
| `monotonic` | for each row and column, how much the values go "the wrong way" (minimum of the up-going and down-going drops), summed, negated | A line that is sorted can merge from one end like a chain. Values that go up and down trap small tiles between large ones. |
| `smooth` | sum of `log2` differences between every pair of neighbours, negated | Equal neighbours are the ones that can merge. Large jumps between neighbours mean tiles that will not merge for a long time. |
| `corner_bonus` | the `log2` of the largest tile if it sits in any corner, else 0 | The standard strategy: anchor the biggest tile in a corner and build a descending staircase from it. |

The final score is:

```
WEIGHT_EMPTY * empty
+ WEIGHT_MONOTONIC * monotonic
+ WEIGHT_SMOOTH * smooth
+ WEIGHT_MAX_IN_CORNER * corner_bonus
```

`monotonic` and `smooth` are penalties, so they are zero or negative; the
weights for them are positive and the sign is built into the feature.

### A worked example

```
row: 2  4  8 16      row: 2 16  4  8
```

Both rows have the same tiles. In `log2` they read `1 2 3 4` and `1 4 2 3`.
The first is monotone (values only go up left to right), so its monotonic
penalty is 0. Its smoothness penalty is `|1-2| + |2-3| + |3-4| = 3`. The
second row goes up 3, down 2, up 1: the increases sum to 4 and the decreases
to 2, so its monotonic penalty is `min(4, 2) = 2`. Its smoothness penalty is
`3 + 2 + 1 = 6`. The search will prefer positions that keep lines like the
first one.

## 4. Tweaking

All knobs are in `settings.py`. The AI reads them at call time, so a change
takes effect on the next run.

### Search depth

| Setting | Default | Effect |
|---|---|---|
| `DEPTH_OPEN_BOARD` | 2 | Depth when the board has many empty cells. Raising it to 3 makes every move about 80 times slower. |
| `DEPTH_CROWDED_BOARD` | 3 | Depth when few cells are empty. Crowded boards are where games are lost, and the tree is small, so deeper search is affordable here. |
| `CROWDED_THRESHOLD` | 4 | "Crowded" means this many empty cells or fewer. Raising it uses the deeper search more often; the slowest moves get slower. |

Deeper search is the most reliable way to play better, and the most
expensive. If you want depth 3 everywhere, expect a game to take several
minutes and consider making the engine faster first (for example, a move
table indexed by row instead of the loop in `Game._slide_line`).

### Heuristic weights

| Setting | Default | What happens if you raise it |
|---|---|---|
| `WEIGHT_EMPTY` | 2.7 | The player merges eagerly to free cells. Too high and it merges small tiles in the wrong place, breaking the staircase. |
| `WEIGHT_MONOTONIC` | 1.0 | The player protects sorted lines. Too high and it refuses good merges that would briefly disturb the order. |
| `WEIGHT_SMOOTH` | 0.1 | The player keeps similar tiles together. This overlaps with monotonicity; it is kept small so it acts as a tiebreaker. |
| `WEIGHT_MAX_IN_CORNER` | 1.0 | The player is reluctant to move the big tile out of its corner. Too high and it sacrifices everything to keep it there. |
| `GAME_OVER_PENALTY` | 1,000,000 | Only needs to be larger than any heuristic score. Leave it. |

Only the ratios matter. Doubling every weight changes nothing. A sensible
experiment changes one weight at a time by a factor of two and measures.

### Adding a feature

Compute it in `evaluate`, add a weight in `settings.py`, and add it to the
sum. Ideas people use: number of possible merges on the board, a penalty for
the largest tile not being in a specific corner (rather than any corner), or
a "snake" weight matrix that rewards values decreasing along a zigzag path.
Keep features cheap: `evaluate` runs thousands of times per move.

## 5. Measuring with the benchmark

Playing a few games by hand tells you very little. Luck varies enormously
between games, so compare configurations on many seeded games.

1. Set `GAMES`, `FIRST_SEED` and `WORKERS` in `settings.py`. Twenty games is
   a rough comparison; a hundred is a decent one. `WORKERS = None` uses every
   CPU core.
2. Run `python benchmark.py`, or press **Benchmark** in the game window.
3. Read the summary. `won (4096)` is the success rate at `TARGET_TILE`;
   `reached 2048` is a softer measure; `average score` and `median score`
   show how far games typically get. `average ms/move` tells you what a
   change in depth cost.
4. Change one thing, keep the same seeds, run again, compare.

Because the seeds are fixed, two runs with identical settings give identical
results, and any difference between runs comes from your change. Change the
seeds too if you suspect you are tuning to a handful of lucky starts.

Rough expectations for the defaults, from a two-game run: both games reached
2048, one reached 4096, at about 50 milliseconds per move and one to three
minutes per game.
