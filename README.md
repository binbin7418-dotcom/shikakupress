# ShikakuPress

Build print-ready **Shikaku (divide-by-rectangles) puzzle books for Amazon KDP** where every puzzle is *proven* to have exactly one solution.

## Why

Shikaku is a pure tiling puzzle — carve the grid into rectangles, one area clue per rectangle — which makes it dangerously easy to fake: partition a grid, print the clues, call the partition "the solution", and never ask whether a second, different tiling also fits the clues. ShikakuPress partitions the grid with recursive guillotine cuts, then hands the printed clues to an **independent exact-cover solver** that counts the tilings from the clues alone. If an alternative tiling exists, the clue of a rectangle it re-shapes is relocated inside its own rectangle — the alternative cannot survive the move — and the puzzle is re-counted. A puzzle enters the book only when the solver finds **exactly one** tiling and it is the generated partition.

## Use

**App (Windows):** launch `ShikakuPress.exe`, choose the puzzle count, difficulty (Easy / Medium / Hard / Mixed), grid size (6/8/10 — Mixed follows difficulty: 6×6 Easy, 8×8 Medium, 10×10 Hard) and a seed, click **Build the book**. Output: `shikaku_book.pdf` in a `shikakupress_out` folder — title page, one puzzle per page, then full solutions. 8.5×11in (612×792pt).

**Command line:** `python shikaku_press.py out/ --puzzles=100 --difficulty=Mixed --size=Mixed --seed=42`

A 6-puzzle sample book is included (`sample_book.pdf`).

## Verified

Acceptance test (9/9 PASS, `test/acceptance_results.txt`): a 6-puzzle mixed book (6×6/8×8/10×10) re-verified by a *second* checker that enumerates rectangles by top-left corner and dimensions, sharing no code with the engine's solver — every puzzle exactly one tiling, equal to the printed solution; rectangle audit exact (tiling complete, one clue per rectangle, clue number equals rectangle area); a tamper check (one clue bumped by 1) breaks the proof, leaving 0 tilings; PDF exactly 14 pages at 612×792pt; the book generated and verified in about 9 seconds; deterministic for a fixed seed.

## Scope

Classic Shikaku on 6×6–10×10 grids, rectangles up to area 8 (Easy) / 12 (Medium, Hard). Rectangle counts per puzzle in the acceptance book ran 7–12. Deterministic seeds make series production repeatable. 100% local — no uploads, no accounts, no per-book fees.

## Build from source

`pip install pyinstaller reportlab`, then `pyinstaller shikakupress.spec`. Or push to GitHub and let the included Actions workflow build the Windows package.
