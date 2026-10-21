#!/usr/bin/env python3
"""
Local stress tests for the Masyu HackerRank puzzle.

The hidden tests are unknown, so this file builds a broad set of guaranteed
solvable puzzles from known-valid loops, then checks whether a solver returns
a valid single loop obeying all pearl rules.

Usage:
    python q4/test_masyu_cases.py
    python q4/test_masyu_cases.py --case large_50x50_sparse
    python q4/test_masyu_cases.py --command ./solution

When no command is supplied, the harness imports q4/solution.py and calls
solve(grid).  With --command, it sends HackerRank-style stdin and reads stdout.
"""

from __future__ import annotations

import argparse
import importlib.util
import random
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path


DIRS = {
    ".": (),
    "-": ((0, -1), (0, 1)),
    "|": ((-1, 0), (1, 0)),
    "L": ((-1, 0), (0, 1)),
    "J": ((-1, 0), (0, -1)),
    "F": ((1, 0), (0, 1)),
    "7": ((1, 0), (0, -1)),
}
TURNS = set("LJF7")


@dataclass(frozen=True)
class Case:
    name: str
    grid: list[str]
    reference_length: int | None = None
    note: str = ""


def tile_from_dirs(dirs):
    dirs = frozenset(dirs)
    for tile, tile_dirs in DIRS.items():
        if tile != "." and dirs == frozenset(tile_dirs):
            return tile
    raise ValueError(f"bad directions: {dirs}")


def path_to_output(rows, cols, path):
    out = [["."] * cols for _ in range(rows)]
    n = len(path)
    if len(set(path)) != n:
        raise ValueError("path repeats a cell")
    for i, (r, c) in enumerate(path):
        pr, pc = path[(i - 1) % n]
        nr, nc = path[(i + 1) % n]
        out[r][c] = tile_from_dirs(((pr - r, pc - c), (nr - r, nc - c)))
    return ["".join(row) for row in out]


def loop_length(out):
    return sum(ch != "." for row in out for ch in row)


def perimeter_loop(rows, cols, top, left, bottom, right):
    path = []
    for c in range(left, right + 1):
        path.append((top, c))
    for r in range(top + 1, bottom + 1):
        path.append((r, right))
    for c in range(right - 1, left - 1, -1):
        path.append((bottom, c))
    for r in range(bottom - 1, top, -1):
        path.append((r, left))
    return path_to_output(rows, cols, path)


def hamiltonian_rect_path(top, left, height, width):
    if height < 2 or width < 2:
        return None

    if height % 2 == 0:
        bottom = top + height - 1
        right = left + width - 1
        path = []
        for c in range(left, right + 1):
            path.append((top, c))
        for r in range(top + 1, bottom + 1):
            if (r - top) % 2 == 1:
                for c in range(right, left, -1):
                    path.append((r, c))
            else:
                for c in range(left + 1, right + 1):
                    path.append((r, c))
        path.append((bottom, left))
        for r in range(bottom - 1, top, -1):
            path.append((r, left))
        return path

    if width % 2 == 0:
        transposed = hamiltonian_rect_path(left, top, width, height)
        return [(c, r) for r, c in transposed]

    return None


def hamiltonian_loop(rows, cols, top, left, bottom, right):
    path = hamiltonian_rect_path(top, left, bottom - top + 1, right - left + 1)
    if path is None:
        raise ValueError("Hamiltonian rectangle needs an even side")
    return path_to_output(rows, cols, path)


def can_be_white(loop, r, c):
    tile = loop[r][c]
    rows = len(loop)
    cols = len(loop[0])
    if tile == "-":
        return (c > 0 and loop[r][c - 1] in TURNS) or (
            c + 1 < cols and loop[r][c + 1] in TURNS
        )
    if tile == "|":
        return (r > 0 and loop[r - 1][c] in TURNS) or (
            r + 1 < rows and loop[r + 1][c] in TURNS
        )
    return False


def can_be_black(loop, r, c):
    tile = loop[r][c]
    if tile not in TURNS:
        return False
    rows = len(loop)
    cols = len(loop[0])
    for dr, dc in DIRS[tile]:
        rr, cc = r + dr, c + dc
        if not (0 <= rr < rows and 0 <= cc < cols):
            return False
        if dr and loop[rr][cc] != "|":
            return False
        if dc and loop[rr][cc] != "-":
            return False
    return True


def pearl_candidates(loop):
    whites = []
    blacks = []
    for r, row in enumerate(loop):
        for c, _ in enumerate(row):
            if can_be_white(loop, r, c):
                whites.append((r, c))
            if can_be_black(loop, r, c):
                blacks.append((r, c))
    return whites, blacks


def grid_from_loop(loop, mode, seed=0, density=0.2):
    rows = len(loop)
    cols = len(loop[0])
    grid = [["."] * cols for _ in range(rows)]
    whites, blacks = pearl_candidates(loop)
    rng = random.Random(seed)

    if mode == "all":
        chosen = [(r, c, "W") for r, c in whites] + [(r, c, "B") for r, c in blacks]
    elif mode == "sparse":
        pool = [(r, c, "W") for r, c in whites] + [(r, c, "B") for r, c in blacks]
        rng.shuffle(pool)
        take = max(2, min(len(pool), int(len(pool) * density)))
        chosen = pool[:take]
    elif mode == "corners":
        chosen = [(r, c, "B") for r, c in blacks[:]]
        chosen += [(r, c, "W") for r, c in whites[:]]
        chosen = chosen[: max(2, min(12, len(chosen)))]
    elif mode == "white_run":
        chosen = []
        for r in range(rows):
            run = []
            for c in range(cols):
                if (r, c) in whites:
                    run.append((r, c))
                    if len(run) >= 3:
                        chosen = [(rr, cc, "W") for rr, cc in run[-3:]]
                        break
                else:
                    run = []
            if chosen:
                break
        if not chosen:
            return grid_from_loop(loop, "sparse", seed, density)
        if blacks:
            chosen.append((*blacks[0], "B"))
    else:
        raise ValueError(mode)

    if len(chosen) < 2:
        raise ValueError("not enough pearl candidates")
    for r, c, ch in chosen:
        grid[r][c] = ch
    return ["".join(row) for row in grid]


def checkerboard_pearls(loop, seed=0):
    rows = len(loop)
    cols = len(loop[0])
    whites, blacks = pearl_candidates(loop)
    wset = set(whites)
    bset = set(blacks)
    grid = [["."] * cols for _ in range(rows)]
    offset = seed & 1
    for r in range(rows):
        for c in range(cols):
            if (r + c + offset) % 3 == 0 and (r, c) in wset:
                grid[r][c] = "W"
            elif (r * 2 + c + offset) % 5 == 0 and (r, c) in bset:
                grid[r][c] = "B"
    if sum(ch in "WB" for row in grid for ch in row) < 2:
        return grid_from_loop(loop, "sparse", seed=seed, density=0.1)
    return ["".join(row) for row in grid]


def alternating_pearls(loop, seed=0, step=7):
    whites, blacks = pearl_candidates(loop)
    pool = [(r, c, "W") for r, c in whites] + [(r, c, "B") for r, c in blacks]
    pool.sort(key=lambda x: (x[0] * 131 + x[1] * 17 + seed) % 997)
    rows = len(loop)
    cols = len(loop[0])
    grid = [["."] * cols for _ in range(rows)]
    chosen = pool[::step]
    if len(chosen) < 2:
        chosen = pool[:2]
    for i, (r, c, _) in enumerate(chosen):
        if (r, c) in whites and (i + seed) % 2 == 0:
            grid[r][c] = "W"
        elif (r, c) in blacks:
            grid[r][c] = "B"
        else:
            grid[r][c] = "W" if (r, c) in whites else "B"
    return ["".join(row) for row in grid]


def valid_solution(grid, out):
    if len(out) != len(grid):
        return False, "wrong row count"
    if any(len(a) != len(b) for a, b in zip(out, grid)):
        return False, "wrong column count"

    rows = len(grid)
    cols = len(grid[0])
    cells = []
    for r in range(rows):
        for c in range(cols):
            if out[r][c] not in DIRS:
                return False, f"illegal output char {out[r][c]!r} at {(r, c)}"
            if grid[r][c] in "WB" and out[r][c] == ".":
                return False, f"missed pearl at {(r, c)}"
            if out[r][c] != ".":
                cells.append((r, c))

    if not cells:
        return False, "empty loop"

    adj = {}
    for r, c in cells:
        neighbours = []
        for dr, dc in DIRS[out[r][c]]:
            rr, cc = r + dr, c + dc
            if not (0 <= rr < rows and 0 <= cc < cols):
                return False, f"edge leaves grid at {(r, c)}"
            if (-dr, -dc) not in DIRS[out[rr][cc]]:
                return False, f"one-way edge between {(r, c)} and {(rr, cc)}"
            neighbours.append((rr, cc))
        if len(neighbours) != 2:
            return False, f"degree is not 2 at {(r, c)}"
        adj[(r, c)] = neighbours

    seen = set()
    stack = [cells[0]]
    while stack:
        cell = stack.pop()
        if cell in seen:
            continue
        seen.add(cell)
        stack.extend(adj[cell])
    if len(seen) != len(cells):
        return False, "multiple loops"

    for r in range(rows):
        for c in range(cols):
            pearl = grid[r][c]
            tile = out[r][c]
            if pearl == "W":
                if tile not in "-|":
                    return False, f"white pearl turns at {(r, c)}"
                if tile == "-":
                    ok = (c > 0 and out[r][c - 1] in TURNS) or (
                        c + 1 < cols and out[r][c + 1] in TURNS
                    )
                else:
                    ok = (r > 0 and out[r - 1][c] in TURNS) or (
                        r + 1 < rows and out[r + 1][c] in TURNS
                    )
                if not ok:
                    return False, f"white pearl lacks adjacent turn at {(r, c)}"
            elif pearl == "B":
                if tile not in TURNS:
                    return False, f"black pearl does not turn at {(r, c)}"
                for dr, dc in DIRS[tile]:
                    rr, cc = r + dr, c + dc
                    if dr and out[rr][cc] != "|":
                        return False, f"black pearl lacks vertical straight at {(r, c)}"
                    if dc and out[rr][cc] != "-":
                        return False, f"black pearl lacks horizontal straight at {(r, c)}"

    return True, "ok"


def approximate_score(valid, elapsed, produced_length, reference_length, s_factor=1.0):
    if not valid or produced_length <= 0:
        return 0.0, 0.0, 0.0
    if reference_length is None:
        quality = 1.0
    else:
        quality = min(1.0, s_factor * reference_length / produced_length) ** 2
    speed = 0.5 + 0.5 * pow(2.718281828, -max(0.0, elapsed - 1.0) / 5.0)
    return 100.0 * quality * speed, quality, speed


def build_cases():
    cases = []

    def add_case(name, grid, reference_length=None, note=""):
        cases.append(Case(name, grid, reference_length, note))

    def add_from_loop(name, loop, grid, note=""):
        add_case(name, grid, loop_length(loop), note)

    def add_loop_family(prefix, loop, variants):
        for suffix, mode, seed, density in variants:
            add_from_loop(
                f"{prefix}_{suffix}",
                loop,
                grid_from_loop(loop, mode, seed=seed, density=density),
                note=f"{mode} density={density}",
            )

    def add_extra_loop_family(prefix, loop, seed):
        add_from_loop(
            f"{prefix}_checker",
            loop,
            checkerboard_pearls(loop, seed=seed),
            note="checkerboard-style mixed constraints",
        )
        add_from_loop(
            f"{prefix}_alternating",
            loop,
            alternating_pearls(loop, seed=seed, step=5),
            note="alternating white/black along loop",
        )

    standard_variants = (
        ("sparse", "sparse", 101, 0.06),
        ("mixed", "sparse", 102, 0.18),
        ("dense", "sparse", 103, 0.34),
    )

    sample = [
        "......",
        ".W....",
        "....B.",
        "......",
        ".B....",
        "....W.",
    ]
    add_case("statement_sample", sample, 18, "from prompt")

    loop = perimeter_loop(6, 6, 0, 0, 5, 5)
    add_from_loop("small_border_dense", loop, grid_from_loop(loop, "all"))
    add_from_loop("small_border_sparse", loop, grid_from_loop(loop, "sparse", seed=1, density=0.25))

    loop = hamiltonian_loop(6, 8, 0, 0, 5, 7)
    add_from_loop("small_hamiltonian_dense", loop, grid_from_loop(loop, "all"))
    add_from_loop("small_hamiltonian_white_run", loop, grid_from_loop(loop, "white_run"))

    loop = hamiltonian_loop(7, 10, 0, 0, 6, 9)
    add_from_loop("odd_by_even_mixed", loop, grid_from_loop(loop, "sparse", seed=2, density=0.35))

    loop = hamiltonian_loop(50, 6, 0, 0, 49, 5)
    add_from_loop("tall_narrow_50x6", loop, grid_from_loop(loop, "sparse", seed=3, density=0.18))

    loop = hamiltonian_loop(6, 50, 0, 0, 5, 49)
    add_from_loop("wide_short_6x50", loop, grid_from_loop(loop, "sparse", seed=4, density=0.18))

    loop = hamiltonian_loop(12, 14, 0, 0, 11, 13)
    add_from_loop("medium_12x14_sparse", loop, grid_from_loop(loop, "sparse", seed=5, density=0.12))
    add_from_loop("medium_12x14_dense", loop, grid_from_loop(loop, "sparse", seed=6, density=0.35))

    loop = hamiltonian_loop(20, 20, 0, 0, 19, 19)
    add_from_loop("medium_20x20_sparse", loop, grid_from_loop(loop, "sparse", seed=7, density=0.08))
    add_from_loop("medium_20x20_dense", loop, grid_from_loop(loop, "sparse", seed=8, density=0.3))

    loop = perimeter_loop(50, 50, 0, 0, 49, 49)
    add_from_loop("large_50x50_border", loop, grid_from_loop(loop, "sparse", seed=9, density=0.4))

    loop = hamiltonian_loop(50, 50, 0, 0, 49, 49)
    add_from_loop("large_50x50_sparse", loop, grid_from_loop(loop, "sparse", seed=10, density=0.03))
    add_from_loop("large_50x50_mixed", loop, grid_from_loop(loop, "sparse", seed=11, density=0.12))

    loop = hamiltonian_loop(50, 50, 5, 3, 44, 42)
    add_from_loop("large_internal_bbox", loop, grid_from_loop(loop, "sparse", seed=12, density=0.1))

    families = [
        ("tiny_6x7_perimeter", perimeter_loop(6, 7, 0, 0, 5, 6)),
        ("tiny_7x6_perimeter", perimeter_loop(7, 6, 0, 0, 6, 5)),
        ("small_8x8_ham", hamiltonian_loop(8, 8, 0, 0, 7, 7)),
        ("small_8x10_ham", hamiltonian_loop(8, 10, 0, 0, 7, 9)),
        ("small_10x8_ham", hamiltonian_loop(10, 8, 0, 0, 9, 7)),
        ("small_9x12_ham", hamiltonian_loop(9, 12, 0, 0, 8, 11)),
        ("small_12x9_ham", hamiltonian_loop(12, 9, 0, 0, 11, 8)),
        ("medium_10x30_ham", hamiltonian_loop(10, 30, 0, 0, 9, 29)),
        ("medium_30x10_ham", hamiltonian_loop(30, 10, 0, 0, 29, 9)),
        ("medium_16x16_ham", hamiltonian_loop(16, 16, 0, 0, 15, 15)),
        ("medium_18x22_ham", hamiltonian_loop(18, 22, 0, 0, 17, 21)),
        ("medium_22x18_ham", hamiltonian_loop(22, 18, 0, 0, 21, 17)),
        ("medium_25x26_ham", hamiltonian_loop(25, 26, 0, 0, 24, 25)),
        ("medium_26x25_ham", hamiltonian_loop(26, 25, 0, 0, 25, 24)),
        ("large_6x50_ham", hamiltonian_loop(6, 50, 0, 0, 5, 49)),
        ("large_50x6_ham", hamiltonian_loop(50, 6, 0, 0, 49, 5)),
        ("large_10x50_ham", hamiltonian_loop(10, 50, 0, 0, 9, 49)),
        ("large_50x10_ham", hamiltonian_loop(50, 10, 0, 0, 49, 9)),
        ("large_14x50_ham", hamiltonian_loop(14, 50, 0, 0, 13, 49)),
        ("large_50x14_ham", hamiltonian_loop(50, 14, 0, 0, 49, 13)),
        ("large_30x50_ham", hamiltonian_loop(30, 50, 0, 0, 29, 49)),
        ("large_50x30_ham", hamiltonian_loop(50, 30, 0, 0, 49, 29)),
        ("large_40x42_ham", hamiltonian_loop(40, 42, 0, 0, 39, 41)),
        ("large_42x40_ham", hamiltonian_loop(42, 40, 0, 0, 41, 39)),
        ("offset_20x20_ham", hamiltonian_loop(30, 30, 4, 5, 23, 24)),
        ("offset_24x28_ham", hamiltonian_loop(35, 40, 6, 4, 29, 31)),
        ("offset_32x20_ham", hamiltonian_loop(45, 31, 7, 5, 38, 24)),
        ("offset_20x32_ham", hamiltonian_loop(31, 45, 5, 7, 24, 38)),
        ("offset_large_40x40_ham", hamiltonian_loop(50, 50, 4, 4, 43, 43)),
    ]
    for idx, (prefix, loop) in enumerate(families):
        variants = tuple(
            (suffix, mode, seed + idx * 17, density)
            for suffix, mode, seed, density in standard_variants
        )
        add_loop_family(prefix, loop, variants)

    hard_extra_loops = [
        ("hard_8x50", hamiltonian_loop(8, 50, 0, 0, 7, 49)),
        ("hard_50x8", hamiltonian_loop(50, 8, 0, 0, 49, 7)),
        ("hard_12x48", hamiltonian_loop(12, 48, 0, 0, 11, 47)),
        ("hard_48x12", hamiltonian_loop(48, 12, 0, 0, 47, 11)),
        ("hard_offset_36x36", hamiltonian_loop(50, 50, 7, 6, 42, 41)),
        ("hard_offset_42x24", hamiltonian_loop(50, 40, 4, 8, 45, 31)),
        ("hard_offset_24x42", hamiltonian_loop(40, 50, 8, 4, 31, 45)),
        ("hard_perimeter_40x50", perimeter_loop(50, 50, 5, 0, 44, 49)),
        ("hard_perimeter_50x40", perimeter_loop(50, 50, 0, 5, 49, 44)),
        ("hard_full_50x50", hamiltonian_loop(50, 50, 0, 0, 49, 49)),
    ]
    for idx, (prefix, loop) in enumerate(hard_extra_loops):
        add_extra_loop_family(prefix, loop, 900 + idx)

    return cases


def load_python_solver():
    here = Path(__file__).resolve().parent
    spec = importlib.util.spec_from_file_location("masyu_solution", here / "solution.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module.solve


def run_command(command, grid, timeout):
    data = str(len(grid)) + "\n" + "\n".join(grid) + "\n"
    proc = subprocess.run(
        command,
        input=data,
        text=True,
        capture_output=True,
        timeout=timeout,
        shell=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"exit code {proc.returncode}")
    return [line.rstrip("\n") for line in proc.stdout.splitlines() if line.strip()]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", help="run one named case")
    parser.add_argument("--list", action="store_true", help="list available cases")
    parser.add_argument("--command", help="external solver command to run")
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument(
        "--first",
        type=int,
        help="run only the first N generated cases, e.g. --first 103",
    )
    parser.add_argument(
        "--failures-only",
        action="store_true",
        help="print only failed cases and the final summary",
    )
    args = parser.parse_args()

    cases = build_cases()
    if args.first is not None:
        cases = cases[:args.first]
    if args.list:
        for case in cases:
            print(
                f"{case.name:34s} {len(case.grid)}x{len(case.grid[0])} "
                f"ref={case.reference_length or '-'} {case.note}"
            )
        print(f"\nTotal cases: {len(cases)}")
        return

    if args.case:
        cases = [case for case in cases if case.name == args.case]
        if not cases:
            raise SystemExit(f"unknown case: {args.case}")

    solve = None if args.command else load_python_solver()
    failures = 0
    total_score = 0.0
    total_quality = 0.0
    total_speed = 0.0
    total_time = 0.0
    for case in cases:
        start = time.perf_counter()
        try:
            if args.command:
                out = run_command(args.command, case.grid, args.timeout)
            else:
                out = solve(case.grid)
            elapsed = time.perf_counter() - start
            ok, reason = valid_solution(case.grid, out)
        except Exception as exc:  # noqa: BLE001 - test harness should report all failures.
            elapsed = time.perf_counter() - start
            ok, reason = False, str(exc)
            out = []

        length = sum(ch != "." for row in out for ch in row)
        score, quality, speed = approximate_score(
            ok, elapsed, length, case.reference_length
        )
        total_score += score
        total_quality += quality
        total_speed += speed
        total_time += elapsed
        status = "PASS" if ok else "FAIL"
        if not args.failures_only or not ok:
            ref = case.reference_length if case.reference_length is not None else 0
            print(
                f"{status:4s} {case.name:34s} {len(case.grid):2d}x{len(case.grid[0]):2d} "
                f"len={length:4d} ref={ref:4d} q={quality:5.3f} "
                f"spd={speed:5.3f} score={score:6.2f} time={elapsed:6.3f}s {reason}"
            )
        if not ok:
            failures += 1

    count = len(cases)
    passed = count - failures
    print(
        f"\nSummary: {passed}/{count} valid, "
        f"avg_score={total_score / count:6.2f}, "
        f"avg_quality={total_quality / count:5.3f}, "
        f"avg_speed={total_speed / count:5.3f}, "
        f"total_time={total_time:6.2f}s"
    )
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
