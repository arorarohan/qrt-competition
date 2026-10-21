"""Harder Masyu benchmark: long winding loops with many pearls.

usage: python gen_hard.py N [seed] [exe ...]
       python gen_hard.py --dump N seed DIR   (write puzzles as DIR/NNN.txt)

bench.py grows compact blobs, whose boundary loops are smooth and carry few
pearls; the hidden tests are harder.  Here the region grows as a thin,
branching shape (new cells prefer touching only one existing cell), so its
boundary snakes across the whole board with many turns, and a large share of
the eligible pearls is kept.  `ref` is the generating loop's length (an upper
bound on the optimum, so quality can read high when a shorter loop exists).
"""
import math
import os
import random
import subprocess
import sys
import time

from bench import RING, region_loop
from solution import valid_solution

N4 = ((-1, 0), (0, 1), (1, 0), (0, -1))


def can_add(inside, f, fr, fc):
    if f in inside or not (0 <= f[0] < fr and 0 <= f[1] < fc):
        return False
    v = [(f[0] + dr, f[1] + dc) in inside for dr, dc in RING]
    if not (v[0] or v[2] or v[4] or v[6]):
        return False
    if sum(1 for i in range(8) if v[i] and not v[i - 1]) != 1:
        return False
    for a, mid, b in ((0, 1, 2), (2, 3, 4), (4, 5, 6), (6, 7, 0)):
        if v[mid] and not v[a] and not v[b]:
            return False
    return True


def thin_region(fr, fc, rng, fill, thin):
    """Grow a hole-free region; with prob `thin` reject cells touching 2+ cells."""
    inside = {(rng.randrange(fr), rng.randrange(fc))}
    cells = list(inside)
    target = max(3, int(fr * fc * fill))
    for _ in range(target * 60):
        if len(inside) >= target:
            break
        r, c = rng.choice(cells)
        dr, dc = N4[rng.randrange(4)]
        f = (r + dr, c + dc)
        if not can_add(inside, f, fr, fc):
            continue
        touching = sum((f[0] + a, f[1] + b) in inside for a, b in N4)
        if touching > 1 and rng.random() < thin:
            continue
        inside.add(f)
        cells.append(f)
    return inside


def eligible_pearls(m):
    R, C = len(m), len(m[0])
    turn = {5, 6, 9, 10}
    sh, sv = 3, 12
    out = []
    for i in range(R):
        for j in range(C):
            x = m[i][j]
            if x in (sh, sv):
                nbrs = [(i, j - 1), (i, j + 1)] if x == sh else [(i - 1, j), (i + 1, j)]
                if any(m[a][b] in turn for a, b in nbrs):
                    out.append(((i, j), "W"))
            elif x in turn:
                ok = all(not (x & bit) or m[i + di][j + dj] == need
                         for bit, di, dj, need in ((4, -1, 0, sv), (8, 1, 0, sv),
                                                   (1, 0, -1, sh), (2, 0, 1, sh)))
                if ok:
                    out.append(((i, j), "B"))
    return out


def make_puzzle(R, C, rng, density, fill=0.45, thin=0.9):
    m = region_loop(R, C, thin_region(R - 1, C - 1, rng, fill, thin))
    cand = eligible_pearls(m)
    chosen = [x for x in cand if rng.random() < density]
    if len(chosen) < 2:
        if len(cand) < 2:
            return None
        chosen = rng.sample(cand, 2)
    g = [["."] * C for _ in range(R)]
    for (i, j), ch in chosen:
        g[i][j] = ch
    ref = sum(1 for row in m for x in row if x)
    return ["".join(row) for row in g], ref


def puzzles(n, seed):
    rng = random.Random(seed)
    made = 0
    while made < n:
        # sizes grow with the index, like the hidden tests
        hi = 6 + (44 * (made + 1)) // n
        R, C = rng.randint(max(6, hi - 10), hi), rng.randint(max(6, hi - 10), hi)
        density = rng.choice([0.15, 0.4, 0.7, 1.0])
        pz = make_puzzle(R, C, rng, density)
        if pz is None:
            continue
        made += 1
        yield made, density, pz


def run(exe, grid, limit=12.0):
    inp = f"{len(grid)}\n" + "\n".join(grid) + "\n"
    cmd = [sys.executable, exe] if exe.endswith(".py") else [exe]
    t = time.perf_counter()
    try:
        p = subprocess.run(cmd, input=inp, capture_output=True, text=True, timeout=limit)
    except subprocess.TimeoutExpired:
        return None, limit
    return [ln.strip() for ln in p.stdout.splitlines() if ln.strip()], time.perf_counter() - t


def score(out, grid, dt, ref):
    if dt > 10 or not out or not valid_solution(grid, out):
        return 0.0, 0
    L = sum(ch != "." for row in out for ch in row)
    q = min(1.0, ref / L) ** 2
    return 100 * q * (0.5 + 0.5 * math.exp(-max(0.0, dt - 1) / 5)), L


def main():
    if sys.argv[1] == "--dump":
        n, seed, d = int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
        os.makedirs(d, exist_ok=True)
        for k, _, (grid, ref) in puzzles(n, seed):
            with open(os.path.join(d, f"{k:03d}.txt"), "w") as f:
                f.write(f"{len(grid)}\n" + "\n".join(grid) + "\n")
        return
    n = int(sys.argv[1])
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    exes = sys.argv[3:]
    totals = [0.0] * len(exes)
    for k, density, (grid, ref) in puzzles(n, seed):
        np_ = sum(ch != "." for row in grid for ch in row)
        cols = []
        for i, exe in enumerate(exes):
            out, dt = run(exe, grid)
            s, L = score(out, grid, dt, ref)
            totals[i] += s
            cols.append(f"{'OK ' if L else 'BAD'} L={L:<4} t={dt:5.2f} s={s:5.1f}")
        print(f"#{k:<3} {len(grid):2}x{len(grid[0]):<2} d={density:<4} pearls={np_:<4} "
              f"ref={ref:<4} | " + " | ".join(cols), flush=True)
    print("TOTAL:", " | ".join(f"{os.path.basename(e)}: {t:.1f}" for e, t in zip(exes, totals)))


if __name__ == "__main__":
    main()
