# Q2: Word Search Generation, work notes

## Problem (from the screenshots in this folder)
- `generate_grid(required_words: list[str], forbidden_words: list[str]) -> list[str]`, returning N strings of length N, uppercase A–Z.
- Every required word must appear in a straight line in one of 8 directions, forwards or backwards, on a torus (wrap-around). No forbidden word may appear anywhere in any direction.
- Score per test: `t = (N - L) / (U - L)`, `score = 100 * 10^-t`, where L is the longest required word (hard lower bound) and U is the number of required words. An invalid grid scores 0.
- Examples: `ACE`/`FIG`/`OAK` → 3×3; the 6×6 torus picture with 8 programming-language words.
- Not known: time limit, input sizes (last screenshot cut off at "Constraints"). Default budget is `total_seconds=3.0`; change it once the limit is known.

## Implementation: `solution.py` (pure Python, numpy isn't installed)
1. Words contained in a longer required word (either direction) are dropped, since they come for free.
2. **Guaranteed fallback** (`_row_layout`): a "safe" letter appears in no forbidden word.
   - Required words are packed into every other row, each followed by a safe letter, and all other cells are safe letters.
   - Every line other than inside one word then contains a safe letter, so this is valid whenever the input is feasible.
3. **Greedy packer** (`_greedy`), with random restarts:
   - Words are placed longest first, preferring the placement that adds the fewest new cells (max overlap).
   - When no word overlaps, it takes the first free spot from a random offset.
   - Each placement is rejected if it completes a forbidden word. The local regex check (`_hit_checker`) covers the 4 axes plus reversed words.
   - Blanks are filled with safe letters. If no safe letter exists, it falls back to checking each letter.
4. **Search**: binary search on N between L and the best grid found so far, then leftover time goes to best−1. Everything is bounded by the deadline.
5. Every returned grid passes `verify`, which checks each torus line as a repeated cyclic string. `count_occurrences` is a slow brute-force checker kept for testing.
6. Infeasible input (a required word contains a forbidden one): it returns a dummy grid after the budget, which scores 0 anyway.

## Test results (3s budget, random words of 3–9 letters, random 3-letter forbidden words)
| U | L | N | score |
|---|---|---|---|
| 8 | 9 | 9 | 100 |
| 10 | 9 | 9 | 100 |
| 25 | 9 | 11 | 75 |
| 40 | 9 | 15 | 64 |
| 100 | 9 | 23 | 70 |

Both examples are optimal. Edge cases tested:
- every letter forbidden somewhere;
- infeasible input;
- a single word whose wrap would form a forbidden word.

The fast and slow checkers agreed on all of these.

Before this rewrite, 25 words gave N=30 in 15s.

## Status
The current `solution.py` (pure-Python greedy) passed all the official test cases.

## `solution_improved.py` (copy of `solution.py` with review fixes, not yet submitted)
- **Greedy:**
  - placements are cached per (N, length) and filled lazily;
  - ties are broken toward tight packing (most filled neighbours);
  - the code is split into the `_Packer` and `_Search` classes. No function exceeds complexity 10 (`.venv/bin/python -m mccabe --min 11`). The original has `_greedy` at 23 and `generate_grid` at 17, which is the judge's "complexity too high" warning.
- **Deadlines:**
  - the fallback layout starts from an area estimate instead of looping up from L;
  - `verify` uses a set of line substrings;
  - each greedy pass stops at the overall deadline.
  - Before any valid grid exists (no separator letter), a pass may overrun, because invalid scores 0.
- **Review fixes:**
  - an empty required list returns a verified single letter;
  - an obviously infeasible input (a required word contains a forbidden one) returns immediately instead of after the budget.
- **`compare.py [seconds]`** runs both versions on the examples, edge cases and random cases, with a brute-force validity check.
  - Results: same N on every case at 0.5s and 2s budgets.
  - Improved is valid where the original isn't (empty required list).
  - 1000 words: 7.5s against 10–16s for the original. Both overrun, because that case has no separator letter.
  - The 2–3× greedy success-rate gain in the scratch benchmark did not translate into smaller N on these cases.

## numpy experiment (`experimental_numpy.py`, not used)
- numpy is installed in `q2/.venv`, which is gitignored. Create it with `python3 -m venv .venv && .venv/bin/pip install numpy`; system pip is blocked by PEP 668.
- I tried a min-conflicts local search at fixed N. It vectorizes scoring every placement of one word, but with a 2s budget it lost to the greedy:

| U | N | local search | greedy |
|---|---|---|---|
| 25 | 11 | failed | 0.38s |
| 40 | 15 | failed | 0.01s |

- Profile: about 5k moves/s. Half the time goes to Python overhead and half to recomputing the per-word clash every move.
- Ideas if revisited:
  - start from the greedy result instead of random placements;
  - update clash counts incrementally;
  - add breakout clause weighting to escape local minima.

## Possible next steps
- Get the real time limit and input sizes. A longer budget will directly improve large-input N.
- The greedy is slow for 100+ words, because overlap enumeration scales with N². Indexing placements could help.
- Smarter packing: score placements by compactness as well as overlap, or try a local-search repair at N−1.
