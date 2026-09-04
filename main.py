"""2048 with a tkinter GUI. Run with: python main.py

Keys: arrows or WASD to move, R for a new game.
The "AI" button hands the current game over to AI.choose_move.
The "Benchmark" button opens the benchmark windows (see benchmark.py).
Timings and other tweaks live in settings.py.
"""

import tkinter as tk
import traceback

import AI
import settings
from game import DIRECTIONS, SIZE, Game, TileMove

# Layout at scale 1.0, in pixels. Benchmark windows use a smaller scale.
TILE = 100  # tile size
GAP = 12  # gap between tiles

KEY_TO_DIR = {
    "Up": "up", "Down": "down", "Left": "left", "Right": "right",
    "w": "up", "s": "down", "a": "left", "d": "right",
}

BG = "#bbada0"
EMPTY = "#cdc1b4"
TILE_COLORS = {
    2: "#eee4da", 4: "#ede0c8", 8: "#f2b179", 16: "#f59563",
    32: "#f67c5f", 64: "#f65e3b", 128: "#edcf72", 256: "#edcc61",
    512: "#edc850", 1024: "#edc53f", 2048: "#edc22e",
}
DARK_TEXT = "#776e65"
LIGHT_TEXT = "#f9f6f2"


class App:
    """One game window.

    root         a tk.Tk (or a tk.Toplevel)
    game         start from this game instead of a fresh one
    controls     keyboard and buttons (off for benchmark windows)
    animate      slide tiles and pause between AI moves (off to run fast)
    on_finished  called with the Game when it ends: won, no move left, or the
                 AI stopped because it returned an illegal move or crashed
    scale        size of everything relative to the normal game window
    """

    def __init__(self, root, game: Game | None = None, controls: bool = True,
                 animate: bool = True, on_finished=None, scale: float = 1.0):
        self.root = root
        root.title("2048")
        root.resizable(False, False)

        self.game = game or Game()
        self.animate_moves = animate
        self.ai_delay = settings.AI_DELAY_MS if animate else 0
        self.on_finished = on_finished
        self.moves = 0
        self.animating = False
        self.ai_on = False
        self.finished = False  # won or no moves left; ignore moves until R

        self.controls = controls
        self.scale = scale
        self.tile = self.px(TILE)
        self.gap = self.px(GAP)
        self.size = SIZE * self.tile + (SIZE + 1) * self.gap  # canvas width and height

        top = tk.Frame(root, padx=self.gap, pady=self.gap)
        top.pack(fill="x")
        self.score_var = tk.StringVar()
        tk.Label(top, textvariable=self.score_var, font=self.font(16, bold=True)).pack(side="left")
        self.ai_button = None
        if controls:
            self.ai_button = tk.Button(top, text="AI: Off", width=8, command=self.toggle_ai)
            self.ai_button.pack(side="right")
            tk.Button(top, text="New Game", command=self.new_game).pack(side="right", padx=(0, GAP))
            tk.Button(top, text="Benchmark", command=self.start_benchmark).pack(side="right", padx=(0, GAP))
            root.bind("<Key>", self.on_key)

        self.status_var = tk.StringVar()
        tk.Label(root, textvariable=self.status_var, font=self.font(12)).pack()

        self.canvas = tk.Canvas(root, width=self.size, height=self.size, bg=BG, highlightthickness=0)
        self.canvas.pack(padx=self.gap, pady=(0, self.gap))

        self.draw_board()
        self.update_labels()

    # ---- geometry ----------------------------------------------------------

    def px(self, n: float) -> int:
        """Scale a length given for the normal window size."""
        return max(1, round(n * self.scale))

    def font(self, size: int, bold: bool = False) -> tuple:
        return ("Helvetica", max(6, round(size * self.scale)), "bold") if bold else ("Helvetica", max(6, round(size * self.scale)))

    def cell_xy(self, row: int, col: int) -> tuple[int, int]:
        """Top-left pixel of a cell."""
        step = self.tile + self.gap
        return self.gap + col * step, self.gap + row * step

    # ---- drawing -----------------------------------------------------------

    def draw_cells(self) -> None:
        self.canvas.delete("all")
        for r in range(SIZE):
            for c in range(SIZE):
                x, y = self.cell_xy(r, c)
                self.canvas.create_rectangle(x, y, x + self.tile, y + self.tile, fill=EMPTY, width=0)

    def draw_tile(self, x: int, y: int, value: int) -> tuple[int, int]:
        color = TILE_COLORS.get(value, "#3c3a32")
        text_color = DARK_TEXT if value <= 4 else LIGHT_TEXT
        size = 36 if value < 100 else 30 if value < 1000 else 24
        rect = self.canvas.create_rectangle(x, y, x + self.tile, y + self.tile, fill=color, width=0)
        text = self.canvas.create_text(
            x + self.tile / 2, y + self.tile / 2, text=str(value), fill=text_color, font=self.font(size, bold=True)
        )
        return rect, text

    def draw_board(self) -> None:
        self.draw_cells()
        for r in range(SIZE):
            for c in range(SIZE):
                value = self.game.board[r][c]
                if value:
                    self.draw_tile(*self.cell_xy(r, c), value)

    def draw_end(self, title: str, subtitle: str) -> None:
        mid = self.size / 2
        self.canvas.create_rectangle(0, 0, self.size, self.size, fill=EMPTY, stipple="gray50", width=0)
        self.canvas.create_text(mid, mid - self.px(20), text=title, fill=DARK_TEXT, font=self.font(40, bold=True))
        self.canvas.create_text(mid, mid + self.px(30), text=subtitle, fill=DARK_TEXT, font=self.font(16))

    def update_labels(self) -> None:
        self.score_var.set(f"Score: {self.game.score}")

    # ---- animation ---------------------------------------------------------

    def animate(self, moves: list[TileMove], on_done) -> None:
        if not self.animate_moves:
            on_done()
            return
        self.animating = True
        self.draw_cells()
        sliding = []  # (canvas items, dx per frame, dy per frame)
        for m in moves:
            sx, sy = self.cell_xy(*m.src)
            dx, dy = self.cell_xy(*m.dst)
            items = self.draw_tile(sx, sy, m.value)
            frames = settings.ANIM_FRAMES
            sliding.append((items, (dx - sx) / frames, (dy - sy) / frames))

        def step(frame: int) -> None:
            for items, dx, dy in sliding:
                for item in items:
                    self.canvas.move(item, dx, dy)
            if frame < settings.ANIM_FRAMES:
                self.root.after(settings.ANIM_INTERVAL_MS, step, frame + 1)
            else:
                self.animating = False
                on_done()

        step(1)

    # ---- game flow ---------------------------------------------------------

    def new_game(self) -> None:
        if self.animating:
            return
        self.game = Game()
        self.moves = 0
        self.finished = False
        self.status_var.set("")
        self.draw_board()
        self.update_labels()
        if self.ai_on:
            self.root.after(self.ai_delay, self.ai_step)

    def do_move(self, direction: str) -> bool:
        """Start a move. Returns False if the move does nothing."""
        if self.animating or self.finished:
            return False
        if not self.game.move(direction, spawn=False):
            return False
        self.animate(self.game.last_moves, self.finish_move)
        return True

    def finish_move(self) -> None:
        self.game.spawn_tile()
        self.moves += 1
        self.draw_board()
        self.update_labels()
        if not self.animate_moves:
            # Tk redraws in idle handlers, which only run when no timer is
            # due. Back-to-back AI moves never leave idle time, so force it.
            self.root.update_idletasks()
        if self.game.has_won(settings.TARGET_TILE):
            self.end_game("You win!", f"{settings.TARGET_TILE} reached")
        elif self.game.is_over():
            self.end_game("Game over", "No moves left")
        elif self.ai_on:
            self.root.after(self.ai_delay, self.ai_step)

    def end_game(self, title: str, subtitle: str) -> None:
        self.finished = True
        if self.controls:
            subtitle += ". Press R for a new game"
        self.draw_end(title, subtitle)
        self.set_ai(False)
        if self.on_finished:
            self.on_finished(self.game)

    def on_key(self, event: tk.Event) -> None:
        key = event.keysym
        if key.lower() == "r":
            self.new_game()
        elif key in KEY_TO_DIR and not self.ai_on:
            self.do_move(KEY_TO_DIR[key])

    # ---- AI ----------------------------------------------------------------

    def set_ai(self, on: bool) -> None:
        self.ai_on = on
        if self.ai_button:
            self.ai_button.config(text="AI: On" if on else "AI: Off")

    def toggle_ai(self) -> None:
        self.set_ai(not self.ai_on)
        if self.ai_on:
            self.status_var.set("")
            self.ai_step()

    def ai_step(self) -> None:
        if not self.ai_on or self.animating or self.finished:
            return
        try:
            direction = AI.choose_move(self.game)
        except Exception:
            traceback.print_exc()
            self.stop_ai("AI crashed, see console.")
            return
        if direction not in DIRECTIONS or not self.do_move(direction):
            self.stop_ai(f"AI stopped: returned {direction!r}, which is not a legal move.")

    def stop_ai(self, message: str) -> None:
        """The AI gave up. Report why, and tell a benchmark the game is done."""
        self.set_ai(False)
        self.status_var.set(message)
        if self.on_finished:
            self.on_finished(self.game)

    # ---- benchmark ---------------------------------------------------------

    def start_benchmark(self) -> None:
        import benchmark  # imported here because benchmark.py imports this module

        worker = benchmark.run_in_background()
        self.status_var.set("Benchmark running, results print to the console.")

        def poll() -> None:
            if worker.is_alive():
                self.root.after(500, poll)
            else:
                self.status_var.set("Benchmark finished, results are in the console.")

        poll()


def main() -> None:
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
