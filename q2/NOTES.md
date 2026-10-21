# Q2: Word Search Generation, work notes

Status: work in progress, paused at the user's request. Nothing here is committed yet.

## Problem (from the screenshots in this folder)
- `generate_grid(required_words: list[str], forbidden_words: list[str]) -> list[str]`, returning N strings of length N, uppercase A–Z.
- Every required word must appear in a straight line in one of 8 directions, forwards or backwards, on a torus (wrap-around). No forbidden word may appear anywhere in any direction.
- Score per test: `t = (N - L) / (U - L)`, `score = 100 * 10^-t`, where L is the longest required word (hard lower bound) and U is the number of required words. An invalid grid scores 0.
- One example is visible: required `ACE`, `FIG`, `OAK`, no forbidden words, a valid 3×3 grid. The 6×6 torus picture in the first screenshot uses 8 programming-language words.
- Not known: time limit, input sizes, whether the screenshots were complete (the last one was cut off at "Constraints").

## Implementation: `solution.py`
- `_placements`: all consistent (cell → letter) placements of a word, 8 directions, wrapped.
- `_try(n, ...)`: randomized DFS over required words (longest first). It prefers placements that overlap existing letters, and rejects a placement when it completes a forbidden word. Blank cells are then filled one at a time, preferring letters that appear in no forbidden word and never completing a forbidden word.
- `verify`: independent checker, used before returning any grid.
- `generate_grid`:
  - phase 1: find any valid grid, starting at N = max(L, U) and growing N;
  - phase 2: binary search N downward toward L within `total_seconds` (default 3s).
- Safeguard: if no valid grid exists (e.g. a required word contains a forbidden one, forwards or backwards), it gives up at N > 3·start+10 and returns a dummy grid instead of looping forever.

## Test results so far
- 6×6 example (8 language words, forbidden `GO`, `ZIG`, `JS`, which I made up): N=6 (= L, the optimum), valid, 0.1s.
- `ACE`/`FIG`/`OAK`: valid 3×3, instant.
- Random stress case, 25 required words (3–9 letters) and 10 forbidden words: valid but N=30, which is above U=25 and so scores about 10 or less, and it took 15.5s, well over the 3s budget. The 40-word and 10-word stress cases had not finished when work was stopped.

## Known problems and next steps
1. Large inputs are weak. Phase 1 starts at N = U, but the DFS often fails there and walks N upward. Starting around N = L plus a small margin and shrinking down would probably do better, and a smarter initial placement (a greedy overlap-maximizing construction) would help.
2. The 3s budget is only exceeded because phase 1 and `_placements` precomputation are not bounded by it. Phase 1 needs a deadline tied to `total_seconds`.
3. `_placements` is recomputed for every `_try`. Cache it per (N, word).
4. Need the real time limit and input sizes before tuning further.
5. Early exit: stop as soon as N equals L, since that is already the maximum score.
6. Mistakes found while testing, so they aren't repeated: my first made-up forbidden word `C` is a substring of `SCALA`, and a random required word contained a forbidden word reversed. Both made the instance infeasible, so check feasibility before blaming the solver.
