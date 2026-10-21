"""Generate random Masyu puzzles and compare solvers on them.

usage: python bench.py N [seed] [exe ...]
  exe defaults to ./masyu.exe (build: python -m ziglang cc -O2 -DLOCAL solution.c -o masyu.exe)
  an exe ending in .py is run with this Python interpreter.

Puzzles come from random hole-free regions whose boundary is the loop; pearls
are placed only where the rules hold, so every puzzle is solvable.  The
generated loop's length is printed as `ref` (an upper bound on the optimum).
"""
import math
import random
import subprocess
import sys
import time

from solution import valid_solution

RING = [(-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1)]


def gen_region(fr, fc, rng, target):
    inside = {(rng.randrange(fr), rng.randrange(fc))}
    cells = list(inside)

    def can_add(f):
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

    for _ in range(target * 30):
        if len(inside) >= target:
            break
        r, c = rng.choice(cells)
        dr, dc = RING[rng.randrange(0, 8, 2)]
        f = (r + dr, c + dc)
        if can_add(f):
            inside.add(f)
            cells.append(f)
    return inside


def region_loop(R, C, inside):
    # bits: W=1 E=2 N=4 S=8
    m = [[0] * C for _ in range(R)]
    for i in range(R):
        for j in range(C - 1):
            if ((i - 1, j) in inside) != ((i, j) in inside):
                m[i][j] |= 2
                m[i][j + 1] |= 1
    for i in range(R - 1):
        for j in range(C):
            if ((i, j - 1) in inside) != ((i, j) in inside):
                m[i][j] |= 8
                m[i + 1][j] |= 4
    return m


def gen_puzzle(R, C, rng, mode):
    fr, fc = R - 1, C - 1
    target = rng.randint(max(3, fr * fc // 10), max(4, fr * fc // 2))
    m = region_loop(R, C, gen_region(fr, fc, rng, target))
    turn = {5, 6, 9, 10}
    straight_h, straight_v = 3, 12
    whites, blacks = [], []
    for i in range(R):
        for j in range(C):
            x = m[i][j]
            if x in (straight_h, straight_v):
                nbrs = [(i, j - 1), (i, j + 1)] if x == straight_h else [(i - 1, j), (i + 1, j)]
                if any(m[a][b] in turn for a, b in nbrs):
                    whites.append((i, j))
            elif x in turn:
                ok = True
                for bit, di, dj, need in ((4, -1, 0, straight_v), (8, 1, 0, straight_v),
                                          (1, 0, -1, straight_h), (2, 0, 1, straight_h)):
                    if x & bit and m[i + di][j + dj] != need:
                        ok = False
                if ok:
                    blacks.append((i, j))
    cand = [(p, "W") for p in whites] + [(p, "B") for p in blacks]
    if len(cand) < 2:
        return None
    if mode == "sparse":
        chosen = rng.sample(cand, min(len(cand), rng.randint(2, 8)))
    else:
        p = rng.uniform(0.4, 0.9)
        chosen = [x for x in cand if rng.random() < p]
        if len(chosen) < 2:
            chosen = rng.sample(cand, 2)
    g = [["."] * C for _ in range(R)]
    for (i, j), ch in chosen:
        g[i][j] = ch
    ref = sum(1 for row in m for x in row if x)
    return ["".join(row) for row in g], ref


def run(exe, grid):
    inp = f"{len(grid)}\n" + "\n".join(grid) + "\n"
    cmd = [sys.executable, exe] if exe.endswith(".py") else [exe]
    t = time.perf_counter()
    try:
        p = subprocess.run(cmd, input=inp, capture_output=True, text=True, timeout=12)
    except subprocess.TimeoutExpired:
        return None, 12.0
    dt = time.perf_counter() - t
    return [line.strip() for line in p.stdout.splitlines() if line.strip()], dt


def score(out, grid, dt, ref):
    if dt > 10 or not out or not valid_solution(grid, out):
        return 0.0, 0
    L = sum(ch != "." for row in out for ch in row)
    q = min(1.0, ref / L) ** 2
    return 100 * q * (0.5 + 0.5 * math.exp(-max(0.0, dt - 1) / 5)), L


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    exes = sys.argv[3:] or ["./masyu.exe"]
    rng = random.Random(seed)
    totals = [0.0] * len(exes)
    done = 0
    while done < n:
        R, C = rng.randint(6, 50), rng.randint(6, 50)
        mode = rng.choice(["sparse", "dense"])
        pz = gen_puzzle(R, C, rng, mode)
        if pz is None:
            continue
        grid, ref = pz
        done += 1
        np_ = sum(ch != "." for row in grid for ch in row)
        cols = []
        for k, exe in enumerate(exes):
            out, dt = run(exe, grid)
            s, L = score(out, grid, dt, ref)
            totals[k] += s
            cols.append(f"{'OK ' if L else 'BAD'} L={L:<4} t={dt:5.2f} s={s:5.1f}")
        print(f"#{done:<3} {R:2}x{C:<2} {mode:6} pearls={np_:<4} ref={ref:<4} | " + " | ".join(cols),
              flush=True)
    print("TOTAL (proxy score, ref = generated loop):",
          " | ".join(f"{e}: {t:.1f}" for e, t in zip(exes, totals)))


if __name__ == "__main__":
    main()
