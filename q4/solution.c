/*
 * Masyu solver for the HackerRank stub:
 *
 *     char** solve(int grid_count, char** grid, int* result_count)
 *
 * C port of solution.py's strategy, run against a wall clock:
 *   1. rectangle constructions (perimeters, serpentine cycles)
 *   2. row-by-row frontier search with memoised dead states
 *   3. annealing on 2x2 flips of a rectangle cycle cover, then merging cycles
 *
 * Every candidate goes through loop_len() (full validator) before it can be
 * kept, and the shortest valid loop wins.  Once a valid loop exists we stop
 * improving at ~0.9 s (the first second is free); with none we keep searching
 * up to 8.8 s, since a slow valid answer beats an invalid one.
 *
 * Paste everything above the LOCAL main into HackerRank (keep its own main).
 * Local build:  python -m ziglang cc -O2 -DLOCAL solution.c -o masyu.exe
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <limits.h>
#include <math.h>
#ifdef _WIN32
#include <windows.h>
#else
#include <time.h>
#endif

#define MAXN 52
#define WB 1
#define EB 2
#define NB 4
#define SB 8

typedef unsigned char Grid[MAXN][MAXN];

static int R, C;
static char G[MAXN][MAXN];
static int npearl, pearl_r[MAXN * MAXN], pearl_c[MAXN * MAXN];
static int minr, maxr, minc, maxc;

static Grid best;
static int best_len;

/* N, E, S, W; opposite direction is (k + 2) & 3 */
static const int DBIT[4] = {NB, EB, SB, WB};
static const int DRow[4] = {-1, 0, 1, 0};
static const int DCol[4] = {0, 1, 0, -1};

/* ---------- timing and rng ---------- */

static double t_start;

static double wall_now(void) {
#ifdef _WIN32
    LARGE_INTEGER f, c;
    QueryPerformanceFrequency(&f);
    QueryPerformanceCounter(&c);
    return (double)c.QuadPart / (double)f.QuadPart;
#elif defined(CLOCK_MONOTONIC)
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec + ts.tv_nsec * 1e-9;
#else
    struct timespec ts;
    timespec_get(&ts, TIME_UTC);
    return ts.tv_sec + ts.tv_nsec * 1e-9;
#endif
}

static double elapsed(void) { return wall_now() - t_start; }

static uint64_t rng_state = 88172645463325252ULL;

static uint64_t rng(void) {
    rng_state ^= rng_state << 13;
    rng_state ^= rng_state >> 7;
    rng_state ^= rng_state << 17;
    return rng_state;
}

static double rng01(void) { return (rng() >> 11) * (1.0 / 9007199254740992.0); }

/* ---------- validation ---------- */

static int is_turn(int m) {
    return m == (NB | EB) || m == (NB | WB) || m == (SB | EB) || m == (SB | WB);
}

static int is_tile(int m) {
    return m == (WB | EB) || m == (NB | SB) || is_turn(m);
}

static int pearl_cost(Grid m, int r, int c) {
    int mask = m[r][c];
    if (G[r][c] == 'W') {
        if (mask != (WB | EB) && mask != (NB | SB)) return 3;
        if (mask == (WB | EB))
            return ((c > 0 && is_turn(m[r][c - 1])) ||
                    (c + 1 < C && is_turn(m[r][c + 1]))) ? 0 : 1;
        return ((r > 0 && is_turn(m[r - 1][c])) ||
                (r + 1 < R && is_turn(m[r + 1][c]))) ? 0 : 1;
    }
    if (G[r][c] == 'B') {
        if (!is_turn(mask)) return 3;
        int cost = 0;
        for (int k = 0; k < 4; ++k) {
            if (!(mask & DBIT[k])) continue;
            int rr = r + DRow[k], cc = c + DCol[k];
            int straight = (k & 1) ? (WB | EB) : (NB | SB);
            if (rr < 0 || rr >= R || cc < 0 || cc >= C || m[rr][cc] != straight)
                cost++;
        }
        return cost;
    }
    return 0;
}

/* Loop length if m is a valid answer, else 0. */
static int loop_len(Grid m) {
    int cells = 0, sr = -1, sc = -1;
    for (int r = 0; r < R; ++r) {
        for (int c = 0; c < C; ++c) {
            int mask = m[r][c];
            if (!mask) {
                if (G[r][c] != '.') return 0;
                continue;
            }
            if (!is_tile(mask)) return 0;
            for (int k = 0; k < 4; ++k) {
                if (!(mask & DBIT[k])) continue;
                int rr = r + DRow[k], cc = c + DCol[k];
                if (rr < 0 || rr >= R || cc < 0 || cc >= C) return 0;
                if (!(m[rr][cc] & DBIT[(k + 2) & 3])) return 0;
            }
            if (sr < 0) { sr = r; sc = c; }
            cells++;
        }
    }
    if (!cells) return 0;

    int r = sr, c = sc, from = -1, steps = 0;
    do {
        int mask = m[r][c], k;
        for (k = 0; k < 4; ++k)
            if ((mask & DBIT[k]) && k != from) break;
        r += DRow[k];
        c += DCol[k];
        from = (k + 2) & 3;
        steps++;
    } while ((r != sr || c != sc) && steps <= cells);
    if (steps != cells) return 0;

    for (int i = 0; i < npearl; ++i)
        if (pearl_cost(m, pearl_r[i], pearl_c[i])) return 0;
    return cells;
}

static int consider(Grid m) {
    int len = loop_len(m);
    if (len && len < best_len) {
        memcpy(best, m, sizeof(Grid));
        best_len = len;
    }
    return len != 0;
}

static int have_answer(void) { return best_len != INT_MAX; }

/* ---------- rectangle constructions ---------- */

static int path_r[MAXN * MAXN], path_c[MAXN * MAXN];

static void path_to_masks(Grid m, int n) {
    memset(m, 0, sizeof(Grid));
    for (int i = 0; i < n; ++i) {
        int j = (i + 1) % n;
        int dr = path_r[j] - path_r[i], dc = path_c[j] - path_c[i];
        for (int k = 0; k < 4; ++k) {
            if (DRow[k] == dr && DCol[k] == dc) {
                m[path_r[i]][path_c[i]] |= DBIT[k];
                m[path_r[j]][path_c[j]] |= DBIT[(k + 2) & 3];
            }
        }
    }
}

/* Hamiltonian cycle of an h x w block (h even) in local coordinates. */
static int gen_snake(int h, int w, int *pi, int *pj) {
    int n = 0;
    for (int j = 0; j < w; ++j) { pi[n] = 0; pj[n++] = j; }
    for (int i = 1; i < h; ++i) {
        if (i & 1)
            for (int j = w - 1; j >= 1; --j) { pi[n] = i; pj[n++] = j; }
        else
            for (int j = 1; j < w; ++j) { pi[n] = i; pj[n++] = j; }
    }
    pi[n] = h - 1; pj[n++] = 0;
    for (int i = h - 2; i >= 1; --i) { pi[n] = i; pj[n++] = 0; }
    return n;
}

/* Serpentine cycle filling a rectangle; variant bits: 1 transpose, 2 flip rows, 4 flip cols. */
static int build_snake(Grid m, int top, int left, int h, int w, int variant) {
    static int li[MAXN * MAXN], lj[MAXN * MAXN];
    int n;
    if (variant & 1) {
        if (w & 1) return 0;
        n = gen_snake(w, h, li, lj);
        for (int i = 0; i < n; ++i) { int t = li[i]; li[i] = lj[i]; lj[i] = t; }
    } else {
        if (h & 1) return 0;
        n = gen_snake(h, w, li, lj);
    }
    for (int i = 0; i < n; ++i) {
        int a = li[i], b = lj[i];
        if (variant & 2) a = h - 1 - a;
        if (variant & 4) b = w - 1 - b;
        path_r[i] = top + a;
        path_c[i] = left + b;
    }
    path_to_masks(m, n);
    return 1;
}

static void build_perimeter(Grid m, int t, int l, int b, int rt) {
    memset(m, 0, sizeof(Grid));
    for (int c = l + 1; c < rt; ++c) m[t][c] = m[b][c] = WB | EB;
    for (int r = t + 1; r < b; ++r) m[r][l] = m[r][rt] = NB | SB;
    m[t][l] = SB | EB;
    m[t][rt] = SB | WB;
    m[b][l] = NB | EB;
    m[b][rt] = NB | WB;
}

typedef struct { short t, l, b, r; int area; } Rect;

static int cmp_rect(const void *x, const void *y) {
    return ((const Rect *)x)->area - ((const Rect *)y)->area;
}

static void constructive(double deadline) {
    static Grid m;

    /* Perimeters of every rectangle containing the pearls' bounding box. */
    for (int t = 0; t <= minr; ++t)
        for (int b = maxr; b < R; ++b) {
            if (b <= t) continue;
            for (int l = 0; l <= minc; ++l)
                for (int rt = maxc; rt < C; ++rt) {
                    if (rt <= l) continue;
                    if (2 * ((b - t) + (rt - l)) >= best_len) continue;
                    int ok = 1;
                    for (int i = 0; i < npearl && ok; ++i) {
                        int r = pearl_r[i], c = pearl_c[i];
                        ok = (r == t || r == b || c == l || c == rt);
                    }
                    if (!ok) continue;
                    build_perimeter(m, t, l, b, rt);
                    consider(m);
                }
        }

    /* Serpentine cycles (length = area), smallest rectangles first. */
    int cap = (minr + 1) * (R - maxr) * (minc + 1) * (C - maxc);
    Rect *rects = malloc(sizeof(Rect) * (cap > 0 ? cap : 1));
    if (!rects) return;
    int n = 0;
    for (int t = 0; t <= minr; ++t)
        for (int b = maxr; b < R; ++b)
            for (int l = 0; l <= minc; ++l)
                for (int rt = maxc; rt < C; ++rt) {
                    int h = b - t + 1, w = rt - l + 1;
                    if (h < 2 || w < 2 || ((h & 1) && (w & 1))) continue;
                    rects[n].t = t; rects[n].l = l; rects[n].b = b; rects[n].r = rt;
                    rects[n].area = h * w;
                    n++;
                }
    qsort(rects, n, sizeof(Rect), cmp_rect);
    for (int i = 0; i < n; ++i) {
        if (rects[i].area >= best_len || elapsed() > deadline) break;
        int h = rects[i].b - rects[i].t + 1, w = rects[i].r - rects[i].l + 1;
        for (int v = 0; v < 8; ++v)
            if (build_snake(m, rects[i].t, rects[i].l, h, w, v) && consider(m)) break;
    }
    free(rects);
}

/* ---------- row-by-row frontier search ---------- */

enum { T_DOT, T_H, T_V, T_L, T_J, T_F, T_7 };
static const int TILE_MASK[7] = {0, WB | EB, NB | SB, NB | EB, NB | WB, SB | EB, SB | WB};
#define RQ_ALL 0x7f
#define RQ_TURN 0x78
#define RQ_H 0x02
#define RQ_V 0x04
#define RQ_WHITE 0x06

/* Neighbour shape classes the pearl rules need: 0 other, 1 straight along the link, 2 turn. */
static int top_class(int t) { return t == T_V ? 1 : t >= T_L ? 2 : 0; }
static int left_class(int t) { return t == T_H ? 1 : t >= T_L ? 2 : 0; }

#define MAXCELLS (MAXN * MAXN)
static int dpR, dpC, dpTot;
static char dpG[MAXN][MAXN];
static unsigned char rem_pearl[MAXCELLS + 1];
static unsigned char st_lab[MAXCELLS + 1][MAXN], st_req[MAXCELLS + 1][MAXN], st_shp[MAXCELLS + 1][MAXN];
static unsigned char st_ll[MAXCELLS + 1], st_lq[MAXCELLS + 1], st_ls[MAXCELLS + 1], st_cl[MAXCELLS + 1];
static unsigned char dp_tile[MAXCELLS];

#define MEMO_BITS 22
#define MEMO_CAP ((size_t)1 << MEMO_BITS)
#define MEMO_LIMIT (MEMO_CAP / 10 * 7)
static uint64_t *memo;
static uint32_t *memo_slots;   /* filled slots, so clearing costs O(entries) */
static size_t memo_count;
static int dp_abort, dp_dot_first;
static long dp_calls;
static double dp_deadline;

static uint64_t mix(uint64_t h, uint64_t v) {
    h = (h ^ v) * 0x9E3779B97F4A7C15ULL;
    return h ^ (h >> 31);
}

static uint64_t dp_hash(int idx) {
    uint64_t h = mix(0x1234567ULL, (uint64_t)idx);
    for (int c = 0; c < dpC; ++c)
        h = mix(h, st_lab[idx][c] | (st_req[idx][c] << 6) | (st_shp[idx][c] << 13));
    h = mix(h, st_ll[idx] | (st_lq[idx] << 6) | (st_ls[idx] << 13) | (st_cl[idx] << 15));
    return h | 1;
}

static int memo_has(uint64_t k) {
    size_t i = (size_t)(k >> 7) & (MEMO_CAP - 1);
    while (memo[i]) {
        if (memo[i] == k) return 1;
        i = (i + 1) & (MEMO_CAP - 1);
    }
    return 0;
}

static void memo_add(uint64_t k) {
    if (memo_count >= MEMO_LIMIT) { dp_abort = 1; return; }
    size_t i = (size_t)(k >> 7) & (MEMO_CAP - 1);
    while (memo[i]) {
        if (memo[i] == k) return;
        i = (i + 1) & (MEMO_CAP - 1);
    }
    memo[i] = k;
    memo_slots[memo_count++] = (uint32_t)i;
}

static int dp_search(int idx) {
    if (dp_abort) return 0;
    if ((++dp_calls & 4095) == 0 && elapsed() > dp_deadline) { dp_abort = 1; return 0; }

    unsigned char *tl = st_lab[idx], *tq = st_req[idx], *ts = st_shp[idx];
    int ll = st_ll[idx], lq = st_lq[idx], ls = st_ls[idx], closed = st_cl[idx];

    if (idx == dpTot) {
        if (!closed) return 0;
        for (int c = 0; c < dpC; ++c)
            if (tl[c] || tq[c] != RQ_ALL) return 0;
        return 1;
    }

    uint64_t key = dp_hash(idx);
    if (memo_has(key)) return 0;

    int r = idx / dpC, c = idx % dpC;
    char pearl = dpG[r][c];
    int nlab = tl[c], wlab = ll;
    int req = tq[c] & lq;
    if (pearl == 'W') req &= RQ_WHITE;
    else if (pearl == 'B') req &= RQ_TURN;
    if (!req) { memo_add(key); return 0; }

    int cand[7], nc = 0;
    if (closed) {
        if (req & 1) cand[nc++] = T_DOT;
    } else {
        for (int t = 0; t < 7; ++t) {
            int m = TILE_MASK[t];
            if (((m & NB) != 0) != (nlab != 0)) continue;
            if (((m & WB) != 0) != (wlab != 0)) continue;
            if (c == dpC - 1 && (m & EB)) continue;
            if (r == dpR - 1 && (m & SB)) continue;
            if (!(req & (1 << t))) continue;
            cand[nc++] = t;
        }
        /* Empty cells are optional; trying skip first usually keeps loops short. */
        if (!dp_dot_first && nc > 1 && cand[0] == T_DOT) {
            for (int i = 1; i < nc; ++i) cand[i - 1] = cand[i];
            cand[nc - 1] = T_DOT;
        }
    }

    for (int i = 0; i < nc; ++i) {
        int t = cand[i], m = TILE_MASK[t];
        int e_on = m & EB, s_on = m & SB, n_on = m & NB, w_on = m & WB;
        int east_req = RQ_ALL, south_req = RQ_ALL;

        if (pearl == 'W') {
            if (t == T_H) { if (ls != 2) east_req = RQ_TURN; }
            else if (t == T_V) { if (ts[c] != 2) south_req = RQ_TURN; }
            else continue;
        } else if (pearl == 'B') {
            if (n_on && ts[c] != 1) continue;
            if (w_on && ls != 1) continue;
            if (e_on) east_req = RQ_H;
            if (s_on) south_req = RQ_V;
        }

        unsigned char *nl = st_lab[idx + 1], *nq = st_req[idx + 1], *ns = st_shp[idx + 1];
        memcpy(nl, tl, dpC);
        memcpy(nq, tq, dpC);
        memcpy(ns, ts, dpC);
        nl[c] = 0;
        nq[c] = (unsigned char)south_req;
        ns[c] = (unsigned char)top_class(t);

        int next_left = 0, next_closed = closed;
        int nin = (n_on ? 1 : 0) + (w_on ? 1 : 0);
        if (t != T_DOT) {
            if (nin == 0) {
                int mx = ll;
                for (int k = 0; k < dpC; ++k) if (tl[k] > mx) mx = tl[k];
                if (e_on) next_left = mx + 1;
                if (s_on) nl[c] = (unsigned char)(mx + 1);
            } else if (nin == 1) {
                int lab = n_on ? nlab : wlab;
                if (e_on) next_left = lab;
                if (s_on) nl[c] = (unsigned char)lab;
            } else if (nlab == wlab) {
                int open = 0;
                for (int k = 0; k < dpC && !open; ++k) open = nl[k] != 0;
                if (open || rem_pearl[idx + 1]) continue;
                next_closed = 1;
            } else {
                for (int k = 0; k < dpC; ++k) if (nl[k] == wlab) nl[k] = (unsigned char)nlab;
            }
        }

        int nlq, nls;
        if (c == dpC - 1) {
            if (next_left || east_req != RQ_ALL) continue;
            nlq = RQ_ALL;
            nls = 0;
        } else {
            nlq = east_req;
            nls = left_class(t);
        }

        /* Renumber labels in order of appearance so equal frontiers hash equal. */
        unsigned char map[64] = {0};
        int nxt = 1;
        for (int k = 0; k < dpC; ++k) {
            if (!nl[k]) continue;
            if (!map[nl[k]]) map[nl[k]] = (unsigned char)nxt++;
            nl[k] = map[nl[k]];
        }
        if (next_left) {
            if (!map[next_left]) map[next_left] = (unsigned char)nxt++;
            next_left = map[next_left];
        }

        st_ll[idx + 1] = (unsigned char)next_left;
        st_lq[idx + 1] = (unsigned char)nlq;
        st_ls[idx + 1] = (unsigned char)nls;
        st_cl[idx + 1] = (unsigned char)next_closed;
        dp_tile[idx] = (unsigned char)t;
        if (dp_search(idx + 1)) return 1;
        if (dp_abort) return 0;
    }

    memo_add(key);
    return 0;
}

/*
 * Search the h x w sub-rectangle at (r0, c0), transposed when trans, until
 * deadline.  Cells outside it stay empty.  Keeps the loop if valid.
 */
static int dp_run(int trans, int r0, int c0, int h, int w, double deadline, int dot_first) {
    if (elapsed() >= deadline || h < 2 || w < 2) return 0;
    if (!memo) {
        memo = calloc(MEMO_CAP, sizeof(uint64_t));
        memo_slots = malloc(MEMO_LIMIT * sizeof(uint32_t));
        if (!memo || !memo_slots) return 0;
    }
    for (size_t i = 0; i < memo_count; ++i) memo[memo_slots[i]] = 0;
    memo_count = 0;

    dpR = trans ? w : h;
    dpC = trans ? h : w;
    dpTot = dpR * dpC;
    for (int r = 0; r < dpR; ++r)
        for (int c = 0; c < dpC; ++c)
            dpG[r][c] = trans ? G[r0 + c][c0 + r] : G[r0 + r][c0 + c];
    rem_pearl[dpTot] = 0;
    for (int idx = dpTot - 1; idx >= 0; --idx)
        rem_pearl[idx] = rem_pearl[idx + 1] || dpG[idx / dpC][idx % dpC] != '.';

    memset(st_lab[0], 0, dpC);
    memset(st_req[0], RQ_ALL, dpC);
    memset(st_shp[0], 0, dpC);
    st_ll[0] = 0;
    st_lq[0] = RQ_ALL;
    st_ls[0] = 0;
    st_cl[0] = 0;

    dp_abort = 0;
    dp_calls = 0;
    dp_deadline = deadline;
    dp_dot_first = dot_first;
    if (!dp_search(0)) return 0;

    static Grid m;
    memset(m, 0, sizeof(Grid));
    for (int idx = 0; idx < dpTot; ++idx) {
        int r = idx / dpC, c = idx % dpC, mask = TILE_MASK[dp_tile[idx]];
        if (trans) {
            int t = 0;
            if (mask & NB) t |= WB;
            if (mask & WB) t |= NB;
            if (mask & SB) t |= EB;
            if (mask & EB) t |= SB;
            m[r0 + c][c0 + r] = (unsigned char)t;
        } else {
            m[r0 + r][c0 + c] = (unsigned char)mask;
        }
    }
    return consider(m);
}

static int dp_full(int trans, double deadline, int dot_first) {
    return dp_run(trans, 0, 0, R, C, deadline, dot_first);
}

/*
 * Frontier search on crops around the pearls, smallest area first: a small
 * crop keeps the frontier narrow and forces a short loop.  Crops grow the
 * pearl box by up to 4 per side, then by symmetric pads out to the full grid.
 */
static void subrect_search(double deadline, double per_rect) {
    static Rect rects[700];
    int n = 0;
    for (int et = 0; et <= 4 && et <= minr; ++et)
        for (int eb = 0; eb <= 4 && maxr + eb < R; ++eb)
            for (int el = 0; el <= 4 && el <= minc; ++el)
                for (int er = 0; er <= 4 && maxc + er < C; ++er) {
                    Rect x = {(short)(minr - et), (short)(minc - el), (short)(maxr + eb), (short)(maxc + er), 0};
                    x.area = (x.b - x.t + 1) * (x.r - x.l + 1);
                    if (x.b > x.t && x.r > x.l) rects[n++] = x;
                }
    for (int p = 5; n < 700; ++p) {
        Rect x;
        x.t = (short)(minr - p < 0 ? 0 : minr - p);
        x.l = (short)(minc - p < 0 ? 0 : minc - p);
        x.b = (short)(maxr + p >= R ? R - 1 : maxr + p);
        x.r = (short)(maxc + p >= C ? C - 1 : maxc + p);
        x.area = (x.b - x.t + 1) * (x.r - x.l + 1);
        if (x.b > x.t && x.r > x.l) rects[n++] = x;
        if (x.t == 0 && x.l == 0 && x.b == R - 1 && x.r == C - 1) break;
    }
    qsort(rects, n, sizeof(Rect), cmp_rect);

    for (int i = 0; i < n; ++i) {
        double now = elapsed();
        if (now >= deadline) break;
        double d = now + per_rect < deadline ? now + per_rect : deadline;
        int h = rects[i].b - rects[i].t + 1, w = rects[i].r - rects[i].l + 1;
        dp_run(w > h, rects[i].t, rects[i].l, h, w, d, 1);
    }
}

/* ---------- annealing on a rectangle cycle cover ---------- */

static Grid hm;
static int clab[MAXN][MAXN];

static int window_cost(int r, int c) {
    int s = 0;
    for (int rr = r - 1; rr <= r + 2; ++rr)
        for (int cc = c - 1; cc <= c + 2; ++cc)
            if (rr >= 0 && rr < R && cc >= 0 && cc < C && G[rr][cc] != '.')
                s += pearl_cost(hm, rr, cc);
    return s;
}

/* Swap two parallel edges across the 2x2 square at (r, c) for the other pair. */
static int try_flip(int r, int c) {
    int a = hm[r][c], b = hm[r][c + 1], d = hm[r + 1][c], e = hm[r + 1][c + 1];
    int horizontal = (a & EB) && (b & WB) && (d & EB) && (e & WB) &&
                     !(a & SB) && !(b & SB) && !(d & NB) && !(e & NB);
    int vertical = (a & SB) && (d & NB) && (b & SB) && (e & NB) &&
                   !(a & EB) && !(d & EB) && !(b & WB) && !(e & WB);
    if (!horizontal && !vertical) return 0;
    hm[r][c] ^= EB | SB;
    hm[r][c + 1] ^= WB | SB;
    hm[r + 1][c] ^= EB | NB;
    hm[r + 1][c + 1] ^= WB | NB;
    return 1;
}

static int label_components(void) {
    static int stk[MAXN * MAXN];
    int count = 0;
    memset(clab, 0, sizeof(clab));
    for (int r = 0; r < R; ++r)
        for (int c = 0; c < C; ++c) {
            if (!hm[r][c] || clab[r][c]) continue;
            int sp = 0;
            clab[r][c] = ++count;
            stk[sp++] = r * MAXN + c;
            while (sp) {
                int cur = stk[--sp], rr = cur / MAXN, cc = cur % MAXN;
                for (int k = 0; k < 4; ++k) {
                    if (!(hm[rr][cc] & DBIT[k])) continue;
                    int nr = rr + DRow[k], nc = cc + DCol[k];
                    if (!clab[nr][nc]) {
                        clab[nr][nc] = count;
                        stk[sp++] = nr * MAXN + nc;
                    }
                }
            }
        }
    return count;
}

static int merge_cycles(int r0, int r1, int c0, int c1, double deadline) {
    static int sq[MAXN * MAXN];
    int nsq = 0;
    for (int r = r0; r < r1; ++r)
        for (int c = c0; c < c1; ++c) sq[nsq++] = r * MAXN + c;

    while (elapsed() < deadline) {
        if (label_components() <= 1) return 1;
        for (int i = nsq - 1; i > 0; --i) {
            int j = (int)(rng() % (uint64_t)(i + 1)), t = sq[i];
            sq[i] = sq[j];
            sq[j] = t;
        }
        int changed = 0;
        for (int i = 0; i < nsq && !changed; ++i) {
            int r = sq[i] / MAXN, c = sq[i] % MAXN;
            int a = hm[r][c], b = hm[r][c + 1], d = hm[r + 1][c], e = hm[r + 1][c + 1];
            int horizontal = (a & EB) && (b & WB) && (d & EB) && (e & WB) &&
                             clab[r][c] != clab[r + 1][c];
            int vertical = (a & SB) && (d & NB) && (b & SB) && (e & NB) &&
                           clab[r][c] != clab[r][c + 1];
            if (!horizontal && !vertical) continue;
            int before = window_cost(r, c);
            if (!try_flip(r, c)) continue;
            if (before == 0 && window_cost(r, c) == 0) changed = 1;
            else try_flip(r, c);
        }
        if (!changed) return 0;
    }
    return 0;
}

static int heuristic(double deadline) {
    if (elapsed() >= deadline) return 0;

    int r0 = minr, r1 = maxr, c0 = minc, c1 = maxc;
    if (r0 == r1) { if (r0 > 0) r0--; else r1++; }
    if (c0 == c1) { if (c0 > 0) c0--; else c1++; }

    /* Smallest rectangle around the pearls with a Hamiltonian cycle (an even side). */
    int bt = -1, bl = 0, bb = 0, br = 0, barea = INT_MAX;
    for (int t = 0; t <= r0; ++t)
        for (int b = r1; b < R; ++b)
            for (int l = 0; l <= c0; ++l)
                for (int rt = c1; rt < C; ++rt) {
                    int h = b - t + 1, w = rt - l + 1;
                    if ((h & 1) && (w & 1)) continue;
                    if (h * w < barea) { barea = h * w; bt = t; bb = b; bl = l; br = rt; }
                }
    if (bt < 0 || barea >= best_len) return 0;  /* result length is the area */
    r0 = bt; r1 = bb; c0 = bl; c1 = br;
    build_snake(hm, r0, c0, r1 - r0 + 1, c1 - c0 + 1, ((r1 - r0 + 1) & 1) ? 1 : 0);

    int cost = 0;
    for (int i = 0; i < npearl; ++i) cost += pearl_cost(hm, pearl_r[i], pearl_c[i]);
    if (cost == 0 && consider(hm)) return 1;

    rng_state ^= (uint64_t)(R * 131 + C) * 0x9E3779B97F4A7C15ULL;
    const long period = 1500000;
    long it = 0, phase = 0, last_merge = -1000000;
    while (1) {
        if ((it & 255) == 0 && elapsed() > deadline) break;
        it++;
        phase++;
        if (cost == 0 && it - last_merge > 2000) {
            last_merge = it;
            double md = elapsed() + 0.25;
            if (md > deadline) md = deadline;
            if (merge_cycles(r0, r1, c0, c1, md) && consider(hm)) return 1;
        }

        int r = r0 + (int)(rng() % (uint64_t)(r1 - r0));
        int c = c0 + (int)(rng() % (uint64_t)(c1 - c0));
        int before = window_cost(r, c);
        unsigned char sa = hm[r][c], sb = hm[r][c + 1], sd = hm[r + 1][c], se = hm[r + 1][c + 1];
        if (!try_flip(r, c)) continue;
        int delta = window_cost(r, c) - before;
        double temp = 2.5 * (1.0 - (double)phase / period);
        if (temp < 0.05) temp = 0.05;
        if (delta <= 0 || rng01() < exp(-delta / temp)) {
            cost += delta;
        } else {
            hm[r][c] = sa; hm[r][c + 1] = sb; hm[r + 1][c] = sd; hm[r + 1][c + 1] = se;
        }
        if (phase >= 2 * period && cost > 0) phase = 0;  /* reheat when stuck */
    }
    return 0;
}

/* ---------- driver ---------- */

static char tile_char(int m) {
    if (m == (WB | EB)) return '-';
    if (m == (NB | SB)) return '|';
    if (m == (NB | EB)) return 'L';
    if (m == (NB | WB)) return 'J';
    if (m == (SB | EB)) return 'F';
    if (m == (SB | WB)) return '7';
    return '.';
}

char **solve(int grid_count, char **grid, int *result_count) {
    t_start = wall_now();
    R = grid_count;
    C = 0;
    while (grid[0][C] == '.' || grid[0][C] == 'W' || grid[0][C] == 'B') C++;

    npearl = 0;
    minr = R; maxr = -1; minc = C; maxc = -1;
    for (int r = 0; r < R; ++r)
        for (int c = 0; c < C; ++c) {
            char ch = grid[r][c];
            G[r][c] = (ch == 'W' || ch == 'B') ? ch : '.';
            if (G[r][c] == '.') continue;
            pearl_r[npearl] = r;
            pearl_c[npearl++] = c;
            if (r < minr) minr = r;
            if (r > maxr) maxr = r;
            if (c < minc) minc = c;
            if (c > maxc) maxc = c;
        }
    if (!npearl) { minr = maxr = minc = maxc = 0; }
    best_len = INT_MAX;

    int trans = C > R;              /* frontier runs along the narrower side */
    int narrow = R < C ? R : C;

    /* Inside the free first second every phase runs; the shortest loop wins. */
    constructive(0.15);
    subrect_search(0.6, 0.03);
    dp_full(trans, 0.7, 1);
    heuristic(0.85);
    dp_full(!trans, 0.9, 1);

    if (have_answer()) {
        /* done */
    } else if (narrow <= 8) {
        if (!have_answer()) dp_full(trans, 7.0, 1);
        if (!have_answer()) dp_full(trans, 8.0, 0);
        if (!have_answer()) dp_full(!trans, 8.5, 1);
        if (!have_answer()) dp_full(!trans, 8.8, 0);
    } else {
        if (!have_answer()) subrect_search(2.5, 0.3);
        if (!have_answer()) heuristic(6.0);
        if (!have_answer()) dp_full(trans, 7.5, 1);
        if (!have_answer()) dp_full(trans, 8.0, 0);
        if (!have_answer()) dp_full(!trans, 8.4, 1);
        if (!have_answer()) dp_full(!trans, 8.8, 0);
        if (!have_answer()) heuristic(8.8);
    }

    if (!have_answer()) {
        /* No valid loop found: border loop (only kept if valid), else dots. */
        static Grid m;
        if (R >= 2 && C >= 2) {
            build_perimeter(m, 0, 0, R - 1, C - 1);
            consider(m);
        }
        if (!have_answer()) memset(best, 0, sizeof(Grid));
    }

    char **ans = malloc(R * sizeof(char *));
    for (int r = 0; r < R; ++r) {
        ans[r] = malloc(C + 1);
        for (int c = 0; c < C; ++c) ans[r][c] = tile_char(best[r][c]);
        ans[r][C] = '\0';
    }
    *result_count = R;
    return ans;
}

#ifdef LOCAL
int main(void) {
    int grid_count;
    if (scanf("%d", &grid_count) != 1) return 0;
    char **grid = malloc(grid_count * sizeof(char *));
    for (int i = 0; i < grid_count; ++i) {
        char buf[128];
        if (scanf("%127s", buf) != 1) return 0;
        grid[i] = malloc(strlen(buf) + 1);
        strcpy(grid[i], buf);
    }
    int result_count = 0;
    char **result = solve(grid_count, grid, &result_count);
    for (int i = 0; i < result_count; ++i) printf("%s\n", result[i]);
    fprintf(stderr, "time %.3f len %d\n", elapsed(), have_answer() ? best_len : -1);
    return 0;
}
#endif
