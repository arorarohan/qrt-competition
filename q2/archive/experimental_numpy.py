"""EXPERIMENT, not used: copy of solution.py with a numpy min-conflicts local
search (_local_search). It currently loses to the pure-Python greedy, see NOTES.md."""
import math
import random
import re
import string
import time

try:
    import numpy as np
except ImportError:  # fall back to the pure-Python greedy
    np = None

DIRS = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
AXES = [(0, 1), (1, 0), (1, 1), (1, -1)]  # the other 4 directions are covered by reversed words


def _lines(grid):
    """Every torus line (row, column, both diagonals) as a cyclic string of length n."""
    n = len(grid)
    for dr, dc in AXES:
        for s in range(n):
            r, c = (s, 0) if (dr, dc) == (0, 1) else (0, s)
            yield "".join(grid[(r + k * dr) % n][(c + k * dc) % n] for k in range(n))


def count_occurrences(grid, word):
    """Brute force over every start cell and direction (slow, independent check)."""
    n = len(grid)
    return sum(all(grid[(r + k * dr) % n][(c + k * dc) % n] == ch for k, ch in enumerate(word))
               for r in range(n) for c in range(n) for dr, dc in DIRS)


def verify(grid, required, forbidden):
    n = len(grid)
    if n == 0 or any(len(row) != n for row in grid):
        return False
    if any(ch not in string.ascii_uppercase for row in grid for ch in row):
        return False
    # a word may wrap a line more than once, so repeat each cycle enough times
    reps = max([len(w) for w in list(required) + list(forbidden)] + [1]) // n + 2
    lines = [s * reps for s in _lines(grid)]

    def present(w):
        return any(w in s or w[::-1] in s for s in lines)

    return all(present(w) for w in required) and not any(present(w) for w in forbidden)


def _hit_checker(n, forbidden):
    """hit(grid, cells): does any forbidden word run through one of these cells?
    grid is a flat list with "." for empty cells, which never match."""
    if not forbidden:
        return lambda grid, cells: False
    words = {v for f in forbidden for v in (f, f[::-1])}
    pat = re.compile("|".join(map(re.escape, sorted(words, key=len, reverse=True))))
    m = max(map(len, forbidden))

    def hit(grid, cells):
        for cell in cells:
            r, c = divmod(cell, n)
            for dr, dc in AXES:
                s = "".join(grid[((r + k * dr) % n) * n + (c + k * dc) % n] for k in range(1 - m, m))
                if pat.search(s):
                    return True
        return False

    return hit


def _greedy(n, words, hit, safe, rng):
    """Place words one by one, preferring maximum overlap with letters already
    down, else the first free spot in a scan. Returns rows or None."""
    grid = ["."] * (n * n)
    where = {}  # letter -> cells holding it

    def cells_of(r0, c0, dr, dc, length):
        return [((r0 + j * dr) % n) * n + (c0 + j * dc) % n for j in range(length)]

    def place(cells, w):
        new = [p for p in cells if grid[p] == "."]
        for p, ch in zip(cells, w):
            grid[p] = ch
        if hit(grid, new):
            for p in new:
                grid[p] = "."
            return False
        for p in new:
            where.setdefault(grid[p], []).append(p)
        return True

    def overlap_options(w):
        """Placements sharing at least one letter, as (new cells + noise, cells),
        or None if the word is already fully in the grid."""
        seen, opts = set(), []
        for k, ch in enumerate(w):
            for cell in where.get(ch, ()):
                r, c = divmod(cell, n)
                for dr, dc in DIRS:
                    key = ((r - k * dr) % n, (c - k * dc) % n, dr, dc)
                    if key in seen:
                        continue
                    seen.add(key)
                    cells = cells_of(*key, len(w))
                    new = 0
                    for p, x in zip(cells, w):
                        if grid[p] == ".":
                            new += 1
                        elif grid[p] != x:
                            break
                    else:
                        if new == 0:
                            return None
                        opts.append((new + rng.random(), cells))
        return sorted(opts, key=lambda t: t[0])

    dir_order = DIRS[:]
    rng.shuffle(dir_order)
    for w in words:
        opts = overlap_options(w)
        if opts is None or any(place(cells, w) for _, cells in opts[:20]):
            continue
        # no overlap possible: first free spot, scanning from a random offset
        off = rng.randrange(n * n)
        if not any(place(cells, w)
                   for dr, dc in dir_order
                   for i in range(n * n)
                   for cells in [cells_of(*divmod((i + off) % (n * n), n), dr, dc, len(w))]
                   if all(grid[p] == "." or grid[p] == x for p, x in zip(cells, w))):
            return None
    # fill: letters absent from every forbidden word can never complete one
    blanks = [p for p in range(n * n) if grid[p] == "."]
    for p in blanks:
        if safe:
            grid[p] = rng.choice(safe)
            continue
        letters = list(string.ascii_uppercase)
        rng.shuffle(letters)
        for ch in letters:
            grid[p] = ch
            if not hit(grid, [p]):
                break
        else:
            return None
    return ["".join(grid[r * n:(r + 1) * n]) for r in range(n)]


def _local_search(n, words, hit, safe, seed, until):
    """Min-conflicts search at fixed n (needs numpy): every word always has a
    placement; repeatedly move a word in conflict to the placement that clashes
    least with the others (ties broken by most overlap). Returns rows or None."""
    gen = np.random.default_rng(seed)
    nn = n * n
    dirs = np.array(DIRS)
    r0, c0 = np.divmod(np.arange(nn), n)
    plc = {}  # word length -> (8*nn, length) flat cell indices of every placement
    for length in {len(w) for w in words}:
        k = np.arange(length)
        rr = (r0[None, :, None] + dirs[:, 0, None, None] * k) % n
        cc = (c0[None, :, None] + dirs[:, 1, None, None] * k) % n
        plc[length] = (rr * n + cc).reshape(-1, length)
    letters = [np.array([ord(ch) - 65 for ch in w]) for w in words]
    counts = np.zeros((nn, 26), dtype=np.int32)  # words covering each cell, per letter
    tot = np.zeros(nn, dtype=np.int32)
    pos = [int(gen.integers(len(plc[len(w)]))) for w in words]

    def move(i, sign):
        cells = plc[len(words[i])][pos[i]]
        counts[cells, letters[i]] += sign
        tot[cells] += sign

    for i in range(len(words)):
        move(i, 1)
    all_letters = np.concatenate(letters)
    starts = np.cumsum([0] + [len(w) for w in words[:-1]])

    while time.time() < until:
        for _ in range(50):
            all_cells = np.concatenate([plc[len(w)][p] for w, p in zip(words, pos)])
            clash = np.add.reduceat(tot[all_cells] - counts[all_cells, all_letters], starts)
            bad = np.flatnonzero(clash)
            if len(bad) == 0:
                grid = ["."] * nn
                for cell in np.flatnonzero(tot):
                    grid[cell] = chr(65 + int(counts[cell].argmax()))
                if hit(grid, [c for c in range(nn) if grid[c] != "."]):
                    bad = [int(gen.integers(len(words)))]  # forbidden word formed: kick one
                else:
                    break
            i = int(gen.choice(bad))
            move(i, -1)
            P, a = plc[len(words[i])], letters[i]
            same = counts[P, a]
            score = (tot[P] - same).sum(1) * 1000 - same.sum(1) + gen.random(len(P)) * 2
            score[pos[i]] = np.inf  # must actually move
            pos[i] = int(score.argmin()) if gen.random() > 0.03 else int(gen.integers(len(P)))
            move(i, 1)
        else:
            continue
        # conflict-free and no forbidden word among placed letters: fill blanks
        for p in range(nn):
            if grid[p] != ".":
                continue
            if safe:
                grid[p] = safe[int(gen.integers(len(safe)))]
                continue
            for ch in gen.permutation(list(string.ascii_uppercase)):
                grid[p] = str(ch)
                if not hit(grid, [p]):
                    break
            else:
                return None
        return ["".join(grid[r * n:(r + 1) * n]) for r in range(n)]
    return None


def _row_layout(n, words, sep):
    """Guaranteed-valid construction (if the input is feasible): words packed
    into every other row, each followed by a separator letter that appears in
    no forbidden word, other rows all separator. Any line of 2+ letters other
    than inside one word then contains a separator. Returns rows or None."""
    rows = [[] for _ in range(n // 2)]
    space = [n] * len(rows)
    for w in sorted(words, key=len, reverse=True):  # first-fit decreasing
        for i in range(len(rows)):
            if space[i] >= len(w) + 1:
                rows[i].append(w)
                space[i] -= len(w) + 1
                break
        else:
            return None
    out = [sep * n] * n
    for i, ws in enumerate(rows):
        out[2 * i] = "".join(w + sep for w in ws).ljust(n, sep)
    return out


def generate_grid(required_words, forbidden_words, total_seconds=3.0, seed=0):
    """Validity first (invalid scores 0), then shrink N toward the longest word."""
    deadline = time.time() + total_seconds
    rng = random.Random(seed)
    required = list(dict.fromkeys(w.upper() for w in required_words if w))
    forbidden = list(dict.fromkeys(w.upper() for w in forbidden_words if w))
    forb_letters = set("".join(forbidden))
    safe = [ch for ch in string.ascii_uppercase if ch not in forb_letters]
    if not required:
        return [safe[0] if safe else "A"]
    # words contained in a longer one (either direction) come for free
    core = []
    for w in sorted(required, key=len, reverse=True):
        if not any(w in v or w[::-1] in v for v in core):
            core.append(w)
    lo = len(core[0])  # hard lower bound
    best = None

    if safe:
        n = max(lo + 1, 2)
        while (g := _row_layout(n, core, safe[0])) is None:
            n += 1
        if verify(g, required, forbidden):
            best = g

    def attempt(n, until):
        hit = _hit_checker(n, forbidden)
        if np is not None:
            while time.time() < until:
                g = _local_search(n, core, hit, safe, rng.randrange(1 << 30), until)
                if g and verify(g, required, forbidden):
                    return g
            return None
        while time.time() < until:
            words = sorted(core, key=lambda w: -len(w) - rng.random() * 2)
            g = _greedy(n, words, hit, safe, rng)
            if g and verify(g, required, forbidden):
                return g
        return None

    if best is None:  # no separator letter: grow N from an area estimate
        n = max(lo, math.isqrt(sum(map(len, core))))
        while best is None and time.time() < deadline:
            best = attempt(n, min(deadline, time.time() + 0.3))
            n += 1
        if best is None:
            return ["A" * lo] * lo  # infeasible input or out of time

    # binary search below the best size found so far
    hi = len(best)
    while lo < hi and time.time() < deadline:
        steps = max(1, math.ceil(math.log2(hi - lo + 1)))
        mid = (lo + hi) // 2
        g = attempt(mid, time.time() + (deadline - time.time()) / (steps + 1))
        if g:
            best, hi = g, mid
        else:
            lo = mid + 1
    # spend any leftover time one step below the best
    while len(best) - 1 >= len(core[0]) and time.time() < deadline:
        g = attempt(len(best) - 1, deadline)
        if not g:
            break
        best = g
    return best


if __name__ == "__main__":
    req = ["PYTHON", "JAVA", "RUBY", "PERL", "RUST", "SWIFT", "SCALA", "LUA"]
    forb = ["GO", "ZIG", "JS"]  # example only; real forbidden list not shown in the screenshot
    t = time.time()
    g = generate_grid(req, forb)
    print(*g, sep="\n")
    print(f"N={len(g)} verified={verify(g, req, forb)} in {time.time() - t:.1f}s")
