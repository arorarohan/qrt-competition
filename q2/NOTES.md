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

## Possible next steps
- Get the real time limit and input sizes. A longer budget will directly improve large-input N.
- The greedy is slow for 100+ words, because overlap enumeration scales with N². Indexing placements could help.
- Smarter packing: score placements by compactness as well as overlap, or try a local-search repair at N−1.
