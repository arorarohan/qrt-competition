"""Headroom diagnostic: does a longer budget shrink N, and do English words
(more shared letter runs) behave differently from random ones?
Usage: python3 diagnostic.py random|english [budgets...]"""
import random
import sys
import time

import compare
import solution_improved as si

ENGLISH = """APPLE BANANA CHERRY GRAPE LEMON MANGO ORANGE PEACH PEAR PLUM MELON BERRY
TIGER LION ZEBRA HORSE MOUSE SNAKE EAGLE SHARK WHALE OTTER RABBIT MONKEY DONKEY TURTLE
PYTHON JAVA RUBY PERL RUST SWIFT SCALA KOTLIN HASKELL ERLANG ELIXIR CLOJURE FORTRAN COBOL
PASCAL LISP JULIA DART GROOVY BASH MATLAB PROLOG OCAML SPARK KAFKA REDIS NGINX DOCKER
RED BLUE GREEN YELLOW PURPLE ORANGE SILVER GOLDEN BLACK WHITE BROWN PINK
TABLE CHAIR SOFA LAMP DESK SHELF CARPET MIRROR WINDOW DOOR ROOF FLOOR WALL STAIR
RIVER OCEAN LAKE MOUNTAIN VALLEY FOREST DESERT ISLAND CANYON GLACIER VOLCANO MEADOW
MARKET STOCK BOND OPTION FUTURE HEDGE ALPHA BETA GAMMA DELTA THETA SIGMA OMEGA
TRADE PRICE SPREAD VOLUME RETURN YIELD CREDIT EQUITY ASSET MARGIN BROKER DEALER
QUANT MODEL SIGNAL FACTOR RISK VALUE GROWTH MOMENTUM CARRY BASIS TENOR STRIKE
WINTER SPRING SUMMER AUTUMN MORNING EVENING NIGHT NOON SUNRISE SUNSET
PIANO GUITAR VIOLIN DRUM FLUTE TRUMPET CELLO HARP ORGAN BANJO""".split()
SHORT_FORB = "CAT DOG ZIP QUA XYZ JIG VEX FOX WAX ZAP KEG HUB JAB MUG NUT OAF PUG RIB SOB TUX".split()


def english_case(seed, n_req, n_forb):
    rng = random.Random(seed)
    req = rng.sample(sorted(set(ENGLISH)), n_req)
    pool = [f for f in SHORT_FORB if not any(f in r or f[::-1] in r for r in req)]
    return req, rng.sample(pool, min(n_forb, len(pool)))


def main():
    kind = sys.argv[1]
    budgets = [float(b) for b in sys.argv[2:]] or [1.0, 5.0, 15.0]
    for i, (nr, nf) in enumerate([(25, 10), (40, 15), (100, 20)]):
        req, forb = (compare.random_case(i + 2, nr, nf) if kind == "random"
                     else english_case(i, nr, nf))
        lo = max(map(len, req))
        letters = sum(map(len, si._core_words(req)))
        out = []
        for b in budgets:
            t = time.time()
            g = si.generate_grid(req, forb, total_seconds=b)
            ok = si.verify(g, req, forb)
            out.append(f"{b:>4.0f}s: N={len(g)} score={compare.score(len(g), req) if ok else 0:.0f}"
                       f" ({time.time() - t:.0f}s)")
        print(f"{kind} U={nr} L={lo} letters={letters} area-bound~{letters ** 0.5:.1f} | " + " | ".join(out), flush=True)


if __name__ == "__main__":
    main()
