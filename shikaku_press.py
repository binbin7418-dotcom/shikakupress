#!/usr/bin/env python3
"""ShikakuPress engine: Shikaku (divide-by-rectangles) puzzle books (PDF)
where every puzzle is PROVEN to have exactly one solution.

How a puzzle is made: the grid is partitioned into rectangles by
recursive guillotine cuts. One clue per rectangle states its area. An
independent exact-cover solver (written separately from the partitioner)
then counts the tilings the printed clues allow. If the count is not
exactly one, the clue of a rectangle whose placement an alternative
tiling disagrees with is relocated inside its own rectangle -- the
alternative cannot survive the move -- and the puzzle is re-counted.
Only a puzzle the solver proves unique, with the found tiling identical
to the generated partition, may enter the book.

Deterministic for a fixed seed. 100% local. Requires: reportlab.

Usage:
    python shikaku_press.py out/ [--puzzles 20] [--size Mixed]
                              [--difficulty Mixed] [--seed 42]
"""
import os
import random
import sys

PAGE_W, PAGE_H = 612, 792
SIZES = {"Easy": 6, "Medium": 8, "Hard": 10}
MAX_AREA = {"Easy": 8, "Medium": 12, "Hard": 12}

# ---------------------------------------------------------------- solver
# A placement is (top, left, height, width). A clue is (r, c, area):
# its rectangle must contain cell (r, c) and have exactly `area` cells.

def _placements_for_clue(n, clue):
    r, c, area = clue
    out = []
    for h in range(1, n + 1):
        if area % h:
            continue
        w = area // h
        if w > n:
            continue
        for top in range(max(0, r - h + 1), min(r, n - h) + 1):
            for left in range(max(0, c - w + 1), min(c, n - w) + 1):
                out.append((top, left, h, w))
    return out


def count_solutions(n, clues, limit=2):
    """Count tilings consistent with the clues. Returns (count, first)
    where first is a dict {(r, c): rect_id} or None."""
    per_clue = [_placements_for_clue(n, cl) for cl in clues]
    order = sorted(range(len(clues)), key=lambda i: len(per_clue[i]))
    grid = [[-1] * n for _ in range(n)]
    found = []

    def rec(k):
        if len(found) >= limit:
            return
        if k == len(order):
            if all(grid[r][c] >= 0 for r in range(n) for c in range(n)):
                found.append([row[:] for row in grid])
            return
        ci = order[k]
        for (top, left, h, w) in per_clue[ci]:
            cells = [(top + dr, left + dc) for dr in range(h) for dc in range(w)]
            if any(grid[r][c] >= 0 for r, c in cells):
                continue
            for r, c in cells:
                grid[r][c] = ci
            rec(k + 1)
            for r, c in cells:
                grid[r][c] = -1
            if len(found) >= limit:
                return

    rec(0)
    return len(found), (found[0] if found else None)


def rects_to_grid(n, rects):
    grid = [[-1] * n for _ in range(n)]
    for i, (top, left, h, w) in enumerate(rects):
        for dr in range(h):
            for dc in range(w):
                grid[top + dr][left + dc] = i
    return grid

# -------------------------------------------------------------- generator

def partition(rng, n, max_area):
    """Recursive guillotine cuts -> list of (top, left, h, w) rectangles
    tiling the n x n grid, each of area <= max_area (when splittable)."""
    rects = [(0, 0, n, n)]

    def splittable(rect):
        top, left, h, w = rect
        return h * w > max_area and (h >= 2 or w >= 2)

    changed = True
    while changed:
        changed = False
        for i, rect in enumerate(rects):
            if not splittable(rect):
                continue
            top, left, h, w = rect
            # stop splitting some pieces early for shape variety
            if h * w > max_area * 1.6 and rng.random() < 0.25:
                continue
            vertical_options = [k for k in range(1, w)]
            horizontal_options = [k for k in range(1, h)]
            if vertical_options and (not horizontal_options or rng.random() < 0.5):
                k = rng.choice(vertical_options)
                rects[i] = (top, left, h, k)
                rects.append((top, left + k, h, w - k))
            elif horizontal_options:
                k = rng.choice(horizontal_options)
                rects[i] = (top, left, k, w)
                rects.append((top + k, left, h - k, w))
            else:
                continue
            changed = True
            break
    # any piece still too large and splittable gets force-split
    final = []
    stack = list(rects)
    while stack:
        rect = stack.pop()
        top, left, h, w = rect
        if h * w > max_area and (h >= 2 or w >= 2):
            if w >= h and w >= 2:
                k = w // 2
                stack.append((top, left, h, k))
                stack.append((top, left + k, h, w - k))
            else:
                k = h // 2
                stack.append((top, left, k, w))
                stack.append((top + k, left, h - k, w))
        else:
            final.append(rect)
    return final


def make_puzzle(rng, n, difficulty, max_attempts=60):
    max_area = MAX_AREA[difficulty]
    for _attempt in range(max_attempts):
        rects = partition(rng, n, max_area)
        clues = []
        for (top, left, h, w) in rects:
            cells = [(top + dr, left + dc) for dr in range(h) for dc in range(w)]
            cr, cc = cells[rng.randrange(len(cells))]
            clues.append((cr, cc, h * w))
        intended = rects_to_grid(n, rects)
        # uniqueness forcing: relocate clues to kill alternative tilings
        for _nudge in range(40):
            cnt, found = count_solutions(n, clues, limit=2)
            if cnt == 1 and found == intended:
                return {"n": n, "rects": rects, "clues": clues,
                        "solution": intended, "difficulty": difficulty,
                        "rect_count": len(rects)}
            if cnt == 0 or found is None:
                break  # partition itself inconsistent (should not happen)
            # find a clue whose intended rectangle the alternative re-tiles:
            # the alt rectangle covering the clue cell differs from intended
            moved = False
            order = list(range(len(rects)))
            rng.shuffle(order)
            for i in order:
                cr, cc, area = clues[i]
                if found[cr][cc] == i:
                    continue
                top, left, h, w = rects[i]
                cells = [(top + dr, left + dc) for dr in range(h) for dc in range(w)]
                # move the clue to a cell of its own rectangle that the
                # alternative assigns to a DIFFERENT rectangle -- the alt
                # tiling has no rectangle of this clue to put there
                targets = [(r, c) for (r, c) in cells
                           if found[r][c] != i and (r, c) != (cr, cc)]
                if targets:
                    nr, nc = targets[rng.randrange(len(targets))]
                    clues[i] = (nr, nc, area)
                    moved = True
                    break
            if not moved:
                break
    raise RuntimeError("could not build a unique-solution shikaku puzzle")


# -------------------------------------------------------------------- PDF

def _draw_grid(c, p, x0, y_top, cell, solved=False):
    from reportlab.lib.colors import HexColor
    ink = HexColor("#1a1a1a")
    light = HexColor("#bbbbbb")
    n = p["n"]
    c.setStrokeColor(light)
    c.setLineWidth(0.6)
    for i in range(n + 1):
        c.line(x0, y_top - i * cell, x0 + n * cell, y_top - i * cell)
        c.line(x0 + i * cell, y_top, x0 + i * cell, y_top - n * cell)
    c.setStrokeColor(ink)
    c.setLineWidth(2.4)
    for (top, left, h, w) in p["rects"]:
        c.rect(x0 + left * cell, y_top - (top + h) * cell, w * cell, h * cell,
               stroke=1, fill=0)
    c.setFillColor(ink)
    for (cr, cc, area) in p["clues"]:
        c.setFont("Helvetica-Bold", cell * 0.42)
        c.drawCentredString(x0 + cc * cell + cell / 2,
                            y_top - cr * cell - cell * 0.64, str(area))


def render_pdf(path, puzzles):
    from reportlab.pdfgen import canvas as rl_canvas
    from reportlab.lib.colors import HexColor
    ink = HexColor("#1a1a1a")
    accent = HexColor("#2050a0")
    c = rl_canvas.Canvas(path, pagesize=(PAGE_W, PAGE_H))
    c.setFillColor(ink)
    c.setFont("Helvetica-Bold", 30)
    c.drawString(72, 640, "ShikakuPress")
    c.setFont("Helvetica", 15)
    c.drawString(72, 606, "Rectangle-division puzzle books with proven unique solutions.")
    c.setFont("Helvetica", 11.5)
    lines = [
        "Divide the grid into rectangles. Each rectangle holds exactly",
        "one number, and the number is the rectangle's area. Every puzzle",
        "here was re-counted by an independent exact-cover solver from",
        "its printed clues alone: exactly one tiling fits, and it is the",
        "one in the back of the book.",
        "",
        f"{len(puzzles)} puzzles with full solutions at the back.",
    ]
    y = 540
    for ln in lines:
        c.drawString(72, y, ln)
        y -= 20
    c.showPage()
    for i, p in enumerate(puzzles, 1):
        n = p["n"]
        cell = min(64, 460 // n)
        x0 = (PAGE_W - n * cell) // 2
        c.setFillColor(ink)
        c.setFont("Helvetica-Bold", 15)
        c.drawString(54, 748, f"Puzzle {i} -- {p['difficulty']} ({n}x{n})")
        c.setFont("Helvetica", 10.5)
        c.setFillColor(accent)
        c.drawString(54, 730, f"{p['rect_count']} rectangles -- one solution, proven")
        _draw_grid(c, p, x0, 700, cell)
        c.showPage()
    c.setFont("Helvetica-Bold", 16)
    c.setFillColor(ink)
    c.drawString(54, 748, "Solutions")
    c.showPage()
    for i, p in enumerate(puzzles, 1):
        n = p["n"]
        cell = min(52, 460 // n)
        x0 = (PAGE_W - n * cell) // 2
        c.setFillColor(ink)
        c.setFont("Helvetica-Bold", 13)
        c.drawString(54, 748, f"Solution {i}")
        _draw_grid(c, p, x0, 716, cell, solved=True)
        c.showPage()
    c.save()
    with open(path, "rb") as fh:
        data = fh.read()
    return data.count(b"/Type /Page") - data.count(b"/Type /Pages")

# -------------------------------------------------------------------- run

def run_shikakupress(count, outdir, seed=42, difficulty="Mixed", size="Mixed", **kw):
    if difficulty not in ("Easy", "Medium", "Hard", "Mixed"):
        raise ValueError("difficulty must be Easy, Medium, Hard or Mixed")
    if size not in ("6", "8", "10", "Mixed"):
        raise ValueError("size must be 6, 8, 10 or Mixed")
    os.makedirs(outdir, exist_ok=True)
    rng = random.Random(seed)
    puzzles = []
    diffs = ["Easy", "Medium", "Hard"]
    for i in range(count):
        d = diffs[i % 3] if difficulty == "Mixed" else difficulty
        n = SIZES[d] if size == "Mixed" else int(size)
        puzzles.append(make_puzzle(rng, n, d))
    pdf_path = os.path.join(outdir, "shikaku_book.pdf")
    pages = render_pdf(pdf_path, puzzles)
    return {"puzzles": puzzles, "pages": pages, "pdf_path": pdf_path,
            "count": len(puzzles)}


def main(argv):
    outdir = argv[1] if len(argv) > 1 else "out"
    opts = {"puzzles": 20, "difficulty": "Mixed", "size": "Mixed", "seed": 42}
    for a in argv[2:]:
        if a.startswith("--") and "=" in a:
            k, v = a[2:].split("=", 1)
            if k in ("puzzles", "seed"):
                v = int(v)
            opts[k] = v
    s = run_shikakupress(opts["puzzles"], outdir, seed=opts["seed"],
                         difficulty=opts["difficulty"], size=opts["size"])
    for i, p in enumerate(s["puzzles"], 1):
        print(f"Puzzle {i}: {p['difficulty']} {p['n']}x{p['n']}, "
              f"{p['rect_count']} rectangles, unique solution proven")
    print(f"Pages: {s['pages']}")
    print(f"PDF: {s['pdf_path']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
