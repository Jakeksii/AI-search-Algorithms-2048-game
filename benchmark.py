"""Play many AI games in parallel and report statistics.

    python benchmark.py

Settings live in settings.py. Every game runs in its own worker process,
because the AI is pure Python and threads would all share one core. A worker
opens a game window, lets the AI play, closes the window when the game ends,
and returns the result. The parent prints one row per game as they finish and
a summary once all of them are done.

The game window's Benchmark button calls run_in_background() so the window
itself stays responsive; the games still run in their own processes.
"""

import multiprocessing
import statistics
import threading
import time
from collections import Counter

import settings
from game import Game


# ---- worker process --------------------------------------------------------

def play_in_window(seed: int) -> dict:
    """Play one game in a window. Runs inside a worker process."""
    import tkinter as tk
    from main import App

    root = tk.Tk()
    root.title(f"2048  seed {seed}")
    root.geometry("+%d+%d" % window_position())
    start = time.perf_counter()
    result = {"seed": seed}

    def finished(game: Game) -> None:
        result.update(
            score=game.score,
            max_tile=game.max_tile(),
            moves=app.moves,
            seconds=time.perf_counter() - start,
            won=game.has_won(settings.TARGET_TILE),
            # Empty when the game ended normally; the AI's error message
            # when it stopped early.
            note="" if app.finished else app.status_var.get(),
        )
        root.after(settings.CLOSE_DELAY_MS, root.destroy)

    app = App(root, game=Game(seed=seed), controls=False, animate=settings.ANIMATE,
              on_finished=finished, scale=settings.WINDOW_SCALE)
    app.toggle_ai()
    root.mainloop()
    return result


def window_position() -> tuple[int, int]:
    """Screen position for this worker's window.

    Pool workers are numbered from 1 in current_process()._identity. Each
    worker keeps the same slot for every game it plays, so at most WORKERS
    windows are on screen at once.
    """
    identity = multiprocessing.current_process()._identity
    slot = identity[0] - 1 if identity else 0
    return (
        settings.WINDOW_STEP[0] * (slot % settings.WINDOWS_PER_ROW),
        settings.WINDOW_STEP[1] * (slot // settings.WINDOWS_PER_ROW),
    )


# ---- parent process --------------------------------------------------------

def run(games: int | None = None, first_seed: int | None = None, workers: int | None = None) -> list[dict]:
    """Play the games and print the results. Arguments default to settings.py."""
    games = settings.GAMES if games is None else games
    first_seed = settings.FIRST_SEED if first_seed is None else first_seed
    workers = settings.WORKERS if workers is None else workers

    seeds = range(first_seed, first_seed + games)
    start = time.perf_counter()
    results: list[dict] = []
    print(f"{'done':>7}  {'seed':>4} {'result':>6} {'score':>7} {'max':>5} {'moves':>5} {'ms/move':>8} {'time':>7}")
    with multiprocessing.Pool(workers) as pool:
        # imap_unordered yields results in the order games finish.
        for r in pool.imap_unordered(play_in_window, seeds):
            results.append(r)
            outcome = "WIN" if r["won"] else "loss"
            note = f"  ({r['note']})" if r["note"] else ""
            print(
                f"{len(results):>3}/{games:<3}  {r['seed']:>4} {outcome:>6} {r['score']:>7} {r['max_tile']:>5} "
                f"{r['moves']:>5} {ms_per_move(r):>8.1f} {r['seconds']:>6.1f}s{note}",
                flush=True,
            )
    summarize(results, time.perf_counter() - start, workers)
    return results


def run_in_background() -> threading.Thread:
    """Run in a thread so a Tk window can keep handling events meanwhile."""
    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return thread


def ms_per_move(r: dict) -> float:
    return 1000 * r["seconds"] / max(r["moves"], 1)


def summarize(results: list[dict], total_seconds: float, workers: int | None) -> None:
    n = len(results)
    scores = [r["score"] for r in results]
    print()
    print(f"games:            {n}  ({workers or multiprocessing.cpu_count()} workers, {total_seconds:.0f} s total)")
    won_label = f"won ({settings.TARGET_TILE}):"
    print(f"{won_label:<18}{100 * sum(r['won'] for r in results) / n:.0f} %")
    print(f"reached 2048:     {100 * sum(r['max_tile'] >= 2048 for r in results) / n:.0f} %")
    print(f"average score:    {statistics.mean(scores):.0f}")
    print(f"median score:     {statistics.median(scores):.0f}")
    print(f"best score:       {max(scores)}")
    print(f"average moves:    {statistics.mean(r['moves'] for r in results):.0f}")
    print(f"average time:     {statistics.mean(r['seconds'] for r in results):.1f} s per game")
    print(f"average ms/move:  {statistics.mean(ms_per_move(r) for r in results):.1f}")
    print("max tiles:        " + ", ".join(
        f"{tile}: {count}" for tile, count in sorted(Counter(r["max_tile"] for r in results).items())
    ))
    failed = [r for r in results if r["note"]]
    if failed:
        print(f"AI stopped early: {len(failed)} game(s), seeds {[r['seed'] for r in failed]}")


if __name__ == "__main__":
    run()
