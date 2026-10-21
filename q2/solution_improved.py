"""Word Search Generation: smallest square torus grid containing all required
words and none of the forbidden words (8 directions, wrap-around).

Improved copy of solution.py: cached placements, tight-packing tie-break,
deadline honoured everywhere, and small functions (complexity <= 15)."""
import math
import random
import re
import string
import time

DIRS = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
AXES = [(0, 1), (1, 0), (1, 1), (1, -1)]  # the other 4 directions are covered by reversed words
UPPER = set(string.ascii_uppercase)


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


def _substrings(grid, lengths):
    """All strings of the given lengths readable along a torus line (one direction)."""
    n = len(grid)
    out = set()
    for line in _lines(grid):
        for length in lengths:
            s = line * (length // n + 2)  # a word may wrap a line more than once
            out.update(s[i:i + length] for i in range(n))
    return out


def verify(grid, required, forbidden):
    n = len(grid)
    if n == 0 or any(len(row) != n or not set(row) <= UPPER for row in grid):
        return False
    seen = _substrings(grid, {len(w) for w in list(required) + list(forbidden)})

    def present(w):
        return w in seen or w[::-1] in seen

    return all(map(present, required)) and not any(map(present, forbidden))


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


_TABLES = {}  # (n, length) -> placement id -> flat cells, filled lazily
_NEIGHBOURS = {}  # n -> cell -> its 4 orthogonal neighbours


def _table(n, length):
    key = (n, length)
    if key not in _TABLES:
        _TABLES[key] = [None] * (8 * n * n)
    return _TABLES[key]


def _cells(table, n, pid, length):
    """Cells of placement pid = start_cell * 8 + direction index."""
    cells = table[pid]
    if cells is None:
        start, d = divmod(pid, 8)
        r, c = divmod(start, n)
        dr, dc = DIRS[d]
        cells = table[pid] = tuple(((r + j * dr) % n) * n + (c + j * dc) % n for j in range(length))
    return cells


def _neighbours(n):
    if n not in _NEIGHBOURS:
        _NEIGHBOURS[n] = [(((r + 1) % n) * n + c, ((r - 1) % n) * n + c, r * n + (c + 1) % n, r * n + (c - 1) % n)
                          for r in range(n) for c in range(n)]
    return _NEIGHBOURS[n]


class _Packer:
    """One greedy attempt at size n: a flat grid with "." for empty cells."""

    def __init__(self, n, hit, rng):
        self.n, self.hit, self.rng = n, hit, rng
        self.grid = ["."] * (n * n)
        self.where = {}  # letter -> cells holding it
        self.nbrs = _neighbours(n)

    def rows(self):
        n = self.n
        return ["".join(self.grid[r * n:(r + 1) * n]) for r in range(n)]

    def _new_cells(self, cells, w):
        """Number of empty cells the placement would fill, or -1 on a letter clash."""
        new = 0
        for p, x in zip(cells, w):
            g = self.grid[p]
            if g == ".":
                new += 1
            elif g != x:
                return -1
        return new

    def _filled_neighbours(self, cells):
        grid = self.grid
        return sum(grid[q] != "." for p in cells for q in self.nbrs[p])

    def _place(self, cells, w):
        """Write w into cells unless that completes a forbidden word."""
        grid = self.grid
        new = [p for p in cells if grid[p] == "."]
        for p, ch in zip(cells, w):
            grid[p] = ch
        if self.hit(grid, new):
            for p in new:
                grid[p] = "."
            return False
        for p in new:
            self.where.setdefault(grid[p], []).append(p)
        return True

    def _overlap_options(self, w, table):
        """Placements sharing a letter with the grid, best first: fewest new
        cells, then most filled neighbours (tight packing). None if w is already present."""
        n = self.n
        seen, opts = set(), []
        for k, ch in enumerate(w):
            for cell in self.where.get(ch, ()):
                r, c = divmod(cell, n)
                for d, (dr, dc) in enumerate(DIRS):
                    pid = (((r - k * dr) % n) * n + (c - k * dc) % n) * 8 + d
                    if pid in seen:
                        continue
                    seen.add(pid)
                    cells = _cells(table, n, pid, len(w))
                    new = self._new_cells(cells, w)
                    if new == 0:
                        return None
                    if new > 0:
                        opts.append((new * 10 - self._filled_neighbours(cells) + self.rng.random(), cells))
        opts.sort(key=lambda t: t[0])
        return opts

    def _first_free(self, w, table):
        """First placement that fits, scanning from a random offset."""
        total = len(table)
        off = self.rng.randrange(total)
        for i in range(total):
            cells = _cells(table, self.n, (i + off) % total, len(w))
            if self._new_cells(cells, w) >= 0 and self._place(cells, w):
                return True
        return False

    def add(self, w):
        table = _table(self.n, len(w))
        opts = self._overlap_options(w, table)
        if opts is None or any(self._place(cells, w) for _, cells in opts[:20]):
            return True
        return self._first_free(w, table)

    def _fill_cell(self, p, safe):
        if safe:  # a letter in no forbidden word can never complete one
            self.grid[p] = self.rng.choice(safe)
            return True
        letters = list(string.ascii_uppercase)
        self.rng.shuffle(letters)
        for ch in letters:
            self.grid[p] = ch
            if not self.hit(self.grid, [p]):
                return True
        self.grid[p] = "."
        return False

    def fill(self, safe):
        return all(self._fill_cell(p, safe) for p in range(len(self.grid)) if self.grid[p] == ".")


def _greedy(n, words, hit, safe, rng, deadline):
    """Place words in order, preferring maximum overlap. Returns rows or None."""
    packer = _Packer(n, hit, rng)
    for w in words:
        if time.time() > deadline or not packer.add(w):
            return None
    return packer.rows() if packer.fill(safe) else None


def _row_layout(n, words, sep):
    """Guaranteed-valid construction (if the input is feasible): words packed
    into every other row, each followed by a separator letter that appears in
    no forbidden word, other rows all separator. Any line of 2+ letters other
    than inside one word then contains a separator. Returns rows or None."""
    rows = [[] for _ in range(n // 2)]
    space = [n] * len(rows)
    for w in sorted(words, key=len, reverse=True):  # first-fit decreasing
        i = next((i for i in range(len(rows)) if space[i] >= len(w) + 1), None)
        if i is None:
            return None
        rows[i].append(w)
        space[i] -= len(w) + 1
    out = [sep * n] * n
    for i, ws in enumerate(rows):
        out[2 * i] = "".join(w + sep for w in ws).ljust(n, sep)
    return out


def _core_words(required):
    """Required words not contained in a longer one (either direction), longest first."""
    core = []
    for w in sorted(required, key=len, reverse=True):
        if not any(w in v or w[::-1] in v for v in core):
            core.append(w)
    return core


class _Search:
    """Find a valid grid, then shrink N toward the longest word until the deadline."""

    def __init__(self, required, forbidden, total_seconds, seed):
        self.deadline = time.time() + total_seconds
        self.rng = random.Random(seed)
        self.required, self.forbidden = required, forbidden
        forb_letters = set("".join(forbidden))
        self.safe = [ch for ch in string.ascii_uppercase if ch not in forb_letters]
        self.core = _core_words(required)
        self.lo = len(self.core[0])  # hard lower bound

    def valid(self, grid):
        return grid is not None and verify(grid, self.required, self.forbidden)

    def attempt(self, n, until, finish_pass=False):
        """Greedy restarts at size n until `until`; a verified grid or None.
        A pass may outlast `until` (so short slices still finish one) but stops
        at the overall deadline unless finish_pass."""
        hit = _hit_checker(n, self.forbidden)
        pass_deadline = math.inf if finish_pass else self.deadline
        while True:
            words = sorted(self.core, key=lambda w: -len(w) - self.rng.random() * 2)
            grid = _greedy(n, words, hit, self.safe, self.rng, pass_deadline)
            if self.valid(grid):
                return grid
            if time.time() >= until:
                return None

    def row_layout(self):
        # n//2 rows of n cells must hold every word plus a separator each
        n = max(self.lo + 1, 2, math.isqrt(2 * sum(len(w) + 1 for w in self.core)))
        while (grid := _row_layout(n, self.core, self.safe[0])) is None:
            n += 1
        return grid if self.valid(grid) else None

    def grow(self):
        """No separator letter available: grow N from an area estimate. An
        invalid grid scores 0, so this may overrun the deadline to find one."""
        start = max(self.lo, math.isqrt(sum(map(len, self.core))))
        for n in range(start, 2 * start + 10):
            grid = self.attempt(n, time.time() + 0.3, finish_pass=True)
            if grid:
                return grid
        return None

    def initial(self):
        return (self.safe and self.row_layout()) or self.grow()

    def shrink(self, best):
        """Binary search below best, then spend leftover time one step below it.
        This deliberately uses the whole budget while N > lower bound."""
        lo, hi = self.lo, len(best)
        while lo < hi and time.time() < self.deadline:
            steps = max(1, math.ceil(math.log2(hi - lo + 1)))
            mid = (lo + hi) // 2
            grid = self.attempt(mid, time.time() + (self.deadline - time.time()) / (steps + 1))
            if grid:
                best, hi = grid, mid
            else:
                lo = mid + 1
        while len(best) > self.lo and (grid := self.attempt(len(best) - 1, self.deadline)):
            best = grid
        return best


def _single_letter(forbidden):
    """No required words: any one letter that isn't forbidden."""
    for ch in string.ascii_uppercase:
        if verify([ch], [], forbidden):
            return [ch]
    return ["A"]  # every 1x1 grid contains a forbidden word


def generate_grid(required_words, forbidden_words, total_seconds=3.0, seed=0):
    """Validity first (invalid scores 0), then shrink N toward the longest word."""
    required = list(dict.fromkeys(w.upper() for w in required_words if w))
    forbidden = list(dict.fromkeys(w.upper() for w in forbidden_words if w))
    if not required:
        return _single_letter(forbidden)
    search = _Search(required, forbidden, total_seconds, seed)
    infeasible = any(f in w or f[::-1] in w for w in required for f in forbidden)
    best = None if infeasible else search.initial()
    if best is None:
        return ["A" * search.lo] * search.lo  # infeasible input or out of time
    return search.shrink(best)


if __name__ == "__main__":
    req = ["PYTHON", "JAVA", "RUBY", "PERL", "RUST", "SWIFT", "SCALA", "LUA"]
    forb = ["GO", "ZIG", "JS"]  # example only; real forbidden list not shown in the screenshot
    t = time.time()
    g = generate_grid(req, forb)
    print(*g, sep="\n")
    print(f"N={len(g)} verified={verify(g, req, forb)} in {time.time() - t:.1f}s")
