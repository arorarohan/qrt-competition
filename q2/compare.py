"""Compare solution.py and solution_improved.py: validity (brute-force checked),
grid size, score and runtime. Usage: python3 compare.py [seconds_per_case]"""
import random
import string
import sys
import time

import solution
import solution_improved

SOLVERS = {"original": solution, "improved": solution_improved}


def valid(grid, req, forb):
    n = len(grid)
    if n == 0 or any(len(r) != n or not set(r) <= set(string.ascii_uppercase) for r in grid):
        return False
    occ = solution_improved.count_occurrences
    return all(occ(grid, w) for w in req) and not any(occ(grid, w) for w in forb)


def random_case(seed, n_req, n_forb, lengths=(3, 9), forb_len=3):
    rng = random.Random(seed)

    def word(k):
        return "".join(rng.choice(string.ascii_uppercase) for _ in range(k))

    req = [word(rng.randint(*lengths)) for _ in range(n_req)]
    forb = []
    while len(forb) < n_forb:  # keep the case feasible
        f = word(forb_len)
        if not any(f in r or f[::-1] in r for r in req):
            forb.append(f)
    return req, forb


def score(n, req):
    lo, hi = max(map(len, req)), len(set(req))
    return 100.0 if n <= lo or hi <= lo else 100 * 10 ** (-(n - lo) / (hi - lo))


CASES = {
    "example ACE/FIG/OAK": (["ACE", "FIG", "OAK"], []),
    "example 6x6 languages": (["PYTHON", "JAVA", "RUBY", "PERL", "RUST", "SWIFT", "SCALA", "LUA"], ["GO", "ZIG", "JS"]),
    "lowercase + duplicates": (["cat", "CAT", "dog", "a"], ["xyz"]),
    "wrap forms forbidden": (["ABCDEFGHIJ"], ["JA"]),
    "no safe letter": (["PYTHON", "JAVA", "RUBY", "PERL"],
                       ["Q" + c + "X" for c in string.ascii_uppercase if c not in "QX"] + ["XQ", "QQ", "XX"]),
    "empty required, AA forbidden": ([], ["AA"] + [c + "B" for c in string.ascii_uppercase if c != "A"]),
}
for i, (nr, nf) in enumerate([(25, 10), (40, 15), (100, 20)]):
    CASES[f"random {nr} words"] = random_case(i + 2, nr, nf)
CASES["random 1000 words (deadline)"] = random_case(9, 1000, 40, lengths=(3, 12), forb_len=4)

if __name__ == "__main__":
    budget = float(sys.argv[1]) if len(sys.argv) > 1 else 2.0
    print(f"budget {budget}s per case")
    for name, (req, forb) in CASES.items():
        out = []
        for label, mod in SOLVERS.items():
            t = time.time()
            g = mod.generate_grid(req, forb, total_seconds=budget)
            dt = time.time() - t
            up = [w.upper() for w in req]
            ok = valid(g, up, [w.upper() for w in forb]) if len(g) <= 40 else mod.verify(g, up, [w.upper() for w in forb])
            sc = f" score={score(len(g), up):.0f}" if up and ok else ""
            out.append(f"{label}: N={len(g)} valid={ok}{sc} {dt:.1f}s")
        print(f"{name:30s} | " + " | ".join(out), flush=True)
