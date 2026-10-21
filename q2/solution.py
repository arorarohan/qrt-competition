"""Word Search Generation: smallest square torus grid containing all required
words and none of the forbidden words (8 directions, wrap-around)."""
import random
import string
import time

DIRS = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


def _walk(n, r, c, dr, dc, length):
    return [((r + k * dr) % n, (c + k * dc) % n) for k in range(length)]


def count_occurrences(grid, word):
    n = len(grid)
    cnt = 0
    for r in range(n):
        for c in range(n):
            for dr, dc in DIRS:
                if all(grid[y][x] == ch for (y, x), ch in zip(_walk(n, r, c, dr, dc, len(word)), word)):
                    cnt += 1
    return cnt


def verify(grid, required, forbidden):
    n = len(grid)
    if any(len(row) != n for row in grid):
        return False
    if any(not ch.isupper() or ch not in string.ascii_uppercase for row in grid for ch in row):
        return False
    return (all(count_occurrences(grid, w) for w in required)
            and not any(count_occurrences(grid, w) for w in forbidden))


def _placements(cells, n, word):
    """All (cell->letter) assignments for placing word, as dicts, consistent within themselves."""
    seen = set()
    for r in range(n):
        for c in range(n):
            for dr, dc in DIRS:
                asg = {}
                ok = True
                for pos, ch in zip(_walk(n, r, c, dr, dc, len(word)), word):
                    if asg.setdefault(pos, ch) != ch:
                        ok = False
                        break
                if ok:
                    key = tuple(sorted(asg.items()))
                    if key not in seen:
                        seen.add(key)
                        yield asg


def _forbidden_hit(grid, n, forbidden, cells):
    """True if a forbidden word is fully present in the partially filled grid
    along a line through any of the given cells (others were already checked)."""
    for (y, x) in cells:
        for w in forbidden:
            L = len(w)
            for k in range(L):
                for dr, dc in DIRS:
                    r0, c0 = (y - k * dr) % n, (x - k * dc) % n
                    if all(grid[(r0 + j * dr) % n][(c0 + j * dc) % n] == w[j] for j in range(L)):
                        return True
    return False


def _try(n, required, forbidden, deadline, rng):
    grid = [[None] * n for _ in range(n)]
    cand = {w: list(_placements(None, n, w)) for w in set(required)}
    if any(not v for v in cand.values()):
        return None
    words = sorted(set(required), key=lambda w: (-len(w), w))
    forb_letters = set("".join(forbidden))

    def fill():
        blanks = [(r, c) for r in range(n) for c in range(n) if grid[r][c] is None]
        rng.shuffle(blanks)
        done = []
        letters = list(string.ascii_uppercase)
        for r, c in blanks:
            # prefer letters absent from every forbidden word, else any that doesn't complete one
            rng.shuffle(letters)
            letters.sort(key=lambda ch: ch in forb_letters)
            for ch in letters:
                grid[r][c] = ch
                if not _forbidden_hit(grid, n, forbidden, [(r, c)]):
                    break
            else:
                grid[r][c] = None
                for y, x in done:
                    grid[y][x] = None
                return False
            done.append((r, c))
        return True

    def dfs(i):
        if time.time() > deadline:
            return False
        if i == len(words):
            return fill()
        w = words[i]
        opts = []
        for asg in cand[w]:
            conflict = False
            new = 0
            for (r, c), ch in asg.items():
                cur = grid[r][c]
                if cur is None:
                    new += 1
                elif cur != ch:
                    conflict = True
                    break
            if not conflict:
                opts.append((new + rng.random(), asg))  # prefer max overlap
        opts.sort(key=lambda t: t[0])
        for _, asg in opts[:40]:
            newcells = [p for p in asg if grid[p[0]][p[1]] is None]
            for (r, c), ch in asg.items():
                grid[r][c] = ch
            if not _forbidden_hit(grid, n, forbidden, newcells) and dfs(i + 1):
                return True
            for r, c in newcells:
                grid[r][c] = None
            if time.time() > deadline:
                return False
        return False

    return ["".join(row) for row in grid] if dfs(0) else None


def _solve_size(n, required, forbidden, budget, rng):
    end = time.time() + budget
    while time.time() < end:
        g = _try(n, required, forbidden, min(end, time.time() + 0.5), rng)
        if g and verify(g, required, forbidden):
            return g
    return None


def generate_grid(required_words, forbidden_words, total_seconds=3.0, seed=0):
    """Validity first (invalid scores 0), then shrink N toward the longest word."""
    required = list(dict.fromkeys(w.upper() for w in required_words))
    forbidden = [w.upper() for w in forbidden_words]
    rng = random.Random(seed)
    start = time.time()
    lo = max([1] + [len(w) for w in required])  # hard lower bound
    hi = max(lo, len(required))                  # score-10 upper bound
    best = None
    # phase 1: any valid grid, growing N until one is found
    cap = 3 * hi + 10  # infeasible input (e.g. a required word contains a forbidden one): give up
    while best is None:
        best = _solve_size(hi, required, forbidden, 2.0, rng)
        if best is None:
            hi += 1
            if hi > cap:
                return ["A" * lo] * lo
    # phase 2: binary search for smaller N within the time budget
    hi = len(best)
    while lo < hi and time.time() - start < total_seconds:
        mid = (lo + hi) // 2
        g = _solve_size(mid, required, forbidden,
                        min(1.0, max(0.2, total_seconds - (time.time() - start))), rng)
        if g:
            best, hi = g, mid
        else:
            lo = mid + 1
    return best


if __name__ == "__main__":
    req = ["PYTHON", "JAVA", "RUBY", "PERL", "RUST", "SWIFT", "SCALA", "LUA"]
    forb = ["GO", "ZIG", "JS"]  # example only; real forbidden list not shown in the screenshot
    t = time.time()
    g = generate_grid(req, forb)
    print(*g, sep="\n")
    print(f"N={len(g)} verified={verify(g, req, forb)} in {time.time() - t:.1f}s")
