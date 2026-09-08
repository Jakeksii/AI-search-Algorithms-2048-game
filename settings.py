"""Project configuration and AI settings."""

# ---- Winning Condition ----
# Tile needed to trigger a win (2048 standard or 4096)
TARGET_TILE = 4096

# ---- AI Search Settings (ai.py) ----
# We use depth 2 when the board is open to keep the search fast,
# and depth 3 when crowded to plan carefully.
DEPTH_OPEN_BOARD = 2
DEPTH_CROWDED_BOARD = 3
CROWDED_THRESHOLD = 4  # 4 or fewer empty cells = crowded board

# ---- Heuristic Weights ----
# Weights tuned through benchmark testing
WEIGHT_MATRIX_PATTERN = 1.0   # Reward keeping tiles aligned with our snake grid
WEIGHT_EMPTY = 100.0          # Reward keeping free space on the board
WEIGHT_MERGES = 50.0          # Reward adjacent tiles that can immediately merge
WEIGHT_CORNER = 2.0           # Extra bonus if the highest tile stays in (0,0)
GAME_OVER_PENALTY = 100000.0  # Big penalty to avoid fatal deadlocks

# ---- GUI & Animation Settings (main.py) ----
ANIM_FRAMES = 5
ANIM_INTERVAL_MS = 15
AI_DELAY_MS = 60  # Small delay so humans can watch the AI play

# ---- Benchmark Settings (benchmark.py) ----
GAMES = 4                  # Number of games for quick testing
FIRST_SEED = 10            # Starting seed for reproducible testing
WORKERS = None             # None uses all available CPU cores
ANIMATE = False            # Set to True only if you want visual windows during benchmark
CLOSE_DELAY_MS = 500
WINDOW_SCALE = 0.5
WINDOWS_PER_ROW = 4
WINDOW_STEP = (260, 340)