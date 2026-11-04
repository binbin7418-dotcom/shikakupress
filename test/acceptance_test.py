#!/usr/bin/env python3
"""ShikakuPress acceptance test.

Proof method: build a real book (2 puzzles of each difficulty, sizes
following difficulty 6/8/10), then verify every puzzle with a tiling
checker written independently of the engine's solver -- it works from
the first empty cell and enumerates rectangles by top-left corner and
dimensions, sharing no code with the engine's divisor-based placement
search. Each puzzle must have exactly one tiling, identical to the
printed solution. Also: rectangle audit (each printed rectangle really
has the clue's area, clues inside their rectangles, rectangles tile the
grid), a tamper check (one altered clue must break the proof), PDF
geometry, determinism, timing.
"""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shikaku_press import run_shikakupress  # noqa: E402

OUT = os.path.join(os.path.dirname(__file__), "out")
results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name} {detail}")


def count_tilings_plain(n, clues, limit=2):
    """Independent checker: first-empty-cell recursion; candidate
    rectangles enumerated by (top, left, height, width) directly."""
    clue_at = {}
    for i, (r, c, a) in enumerate(clues):
        clue_at[(r, c)] = (i, a)
    grid = [[-1] * n for _ in range(n)]
    sols = []

    def rec():
        if len(sols) >= limit:
            return
        # first empty cell
        pos = None
        for r in range(n):
            for c in range(n):
                if grid[r][c] == -1:
                    pos = (r, c)
                    break
            if pos:
                break
        if pos is None:
            sols.append([row[:] for row in grid])
            return
        r, c = pos
        # every rectangle covering (r, c): iterate top-left + dims
        for top in range(r, -1, -1):
            for left in range(c, -1, -1):
                for h in range(r - top + 1, n - top + 1):
                    for w in range(c - left + 1, n - left + 1):
                        area = h * w
                        cells = [(top + dr, left + dc)
                                 for dr in range(h) for dc in range(w)]
                        if any(grid[x][y] != -1 for x, y in cells):
                            continue
                        inside = [clue_at[(x, y)] for (x, y) in cells
                                  if (x, y) in clue_at]
                        if len(inside) != 1 or inside[0][1] != area:
                            continue
                        ci = inside[0][0]
                        for x, y in cells:
                            grid[x][y] = ci
                        rec()
                        for x, y in cells:
                            grid[x][y] = -1
                        if len(sols) >= limit:
                            return

    rec()
    return sols


def main():
    t0 = time.time()
    s = run_shikakupress(6, OUT, seed=42, difficulty="Mixed", size="Mixed")
    dt = time.time() - t0
    ps = s["puzzles"]
    check("counts: 6 puzzles", len(ps) == 6, f"({len(ps)})")
    check("sizes follow difficulty (6/8/10)",
          [p["n"] for p in ps] == [6, 8, 10, 6, 8, 10],
          f"({[p['n'] for p in ps]})")

    all_unique, audit_ok = True, True
    for p in ps:
        sols = count_tilings_plain(p["n"], p["clues"], limit=2)
        if len(sols) != 1 or sols[0] != p["solution"]:
            all_unique = False
        # audit: rectangles tile the grid, areas match clues, clue inside
        seen = [[0] * p["n"] for _ in range(p["n"])]
        clue_cells = {(r, c): a for (r, c, a) in p["clues"]}
        if len(clue_cells) != len(p["rects"]):
            audit_ok = False
        for (top, left, h, w) in p["rects"]:
            inside = []
            for dr in range(h):
                for dc in range(w):
                    seen[top + dr][left + dc] += 1
                    if (top + dr, left + dc) in clue_cells:
                        inside.append(clue_cells[(top + dr, left + dc)])
            if inside != [h * w]:
                audit_ok = False
        if any(v != 1 for row in seen for v in row):
            audit_ok = False
    check("every puzzle: exactly one tiling (independent checker), "
          "equal to printed solution", all_unique, "")
    check("rectangle audit: tiling exact, one clue per rectangle, "
          "clue number == rectangle area", audit_ok, "")
    check("rectangles were actually cut (not one giant piece)",
          all(p["rect_count"] >= 5 for p in ps),
          f"(rects: {[p['rect_count'] for p in ps]})")

    # tamper: bump one clue's area by 1 -> proof must break
    p0 = ps[0]
    bad_clues = list(p0["clues"])
    r, c, a = bad_clues[0]
    bad_clues[0] = (r, c, a + 1)
    sols = count_tilings_plain(p0["n"], bad_clues, limit=2)
    broken = not (len(sols) == 1 and sols[0] == p0["solution"])
    check("tamper check: one altered clue breaks the uniqueness proof",
          broken, f"(tampered puzzle now has {len(sols)} tilings)")

    with open(s["pdf_path"], "rb") as fh:
        data = fh.read()
    pages = data.count(b"/Type /Page") - data.count(b"/Type /Pages")
    check("PDF 612x792pt, pages = title + 6 puzzles + solutions header + 6 solutions",
          b"612 792" in data and pages == 14, f"({pages} pages)")
    check("6-puzzle mixed book builds in under 120s", dt < 120, f"({dt:.1f}s)")

    s2 = run_shikakupress(6, OUT, seed=42, difficulty="Mixed", size="Mixed")
    same = [p["clues"] for p in s2["puzzles"]] == [p["clues"] for p in ps]
    check("deterministic for fixed seed", same, "")

    npass = sum(1 for _, ok, _ in results if ok)
    print(f"\n{npass}/{len(results)} PASS")
    with open(os.path.join(os.path.dirname(__file__), "acceptance_results.txt"), "w") as fh:
        for name, ok, detail in results:
            fh.write(f"[{'PASS' if ok else 'FAIL'}] {name} {detail}\n")
        fh.write(f"\n{npass}/{len(results)} PASS\n")
    return 0 if npass == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
