"""All tweakable settings in one place. Nothing here is required by the rules
of 2048; change freely."""

# ---- Winning -----------------------------------------------------------------

# The game is won and stops when a tile of this value appears. Applies to
# human play, the AI button, and the benchmark (where it counts as a win).
TARGET_TILE = 4096

# ---- AI search (AI.py) -------------------------------------------------------

# How many of our own moves to look ahead. Each level multiplies the work by
# roughly (4 moves x empty cells x 2 tile values), so 3 is already slow in
# pure Python when the board is empty. We look deeper when the board is
# crowded, because that is when mistakes are fatal and the tree is small.
DEPTH_OPEN_BOARD = 2
DEPTH_CROWDED_BOARD = 3
CROWDED_THRESHOLD = 4  # empty cells or fewer -> use the deeper search

# Heuristic weights. Tuned by hand; only their relative sizes matter.
WEIGHT_EMPTY = 2.7  # reward free cells (room to move and to merge)
WEIGHT_MONOTONIC = 1.0  # reward rows/columns that decrease steadily toward a corner
WEIGHT_SMOOTH = 0.1  # penalise neighbours with very different values
WEIGHT_MAX_IN_CORNER = 1.0  # reward keeping the biggest tile in a corner
GAME_OVER_PENALTY = 1_000_000  # a dead board is worse than any heuristic score

# ---- Game window (main.py) ---------------------------------------------------

ANIM_FRAMES = 6  # frames per tile slide
ANIM_INTERVAL_MS = 15  # milliseconds per frame
AI_DELAY_MS = 80  # pause between AI moves, after the animation

# ---- Benchmark (benchmark.py and the Benchmark button) -----------------------

GAMES = 2  # how many games to play
FIRST_SEED = 0  # games use seeds FIRST_SEED, FIRST_SEED + 1, ...
WORKERS = 2  # parallel games (one process each); None = number of CPU cores
ANIMATE = False  # slide tiles and pause between moves (much slower)
CLOSE_DELAY_MS = 1000  # how long a finished game window stays open
WINDOW_SCALE = 0.5  # benchmark window size relative to the game window (0.5 = a quarter of the area)
WINDOWS_PER_ROW = 6  # each worker owns one window slot in this grid
WINDOW_STEP = (260, 340)  # pixel offset between neighbouring windows; shrink with WINDOW_SCALE
