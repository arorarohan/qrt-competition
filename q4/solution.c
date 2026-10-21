/*
 * Masyu solver v2 for the HackerRank stub:
 *
 *     char** solve(int grid_count, char** grid, int* result_count)
 *
 * Edge-based constraint propagation with backtracking (the standard way to
 * solve Masyu).  Every edge between neighbouring cells is UNKNOWN, ON or OFF.
 * Rules applied to a fixpoint after every change:
 *   - a cell has 0 or 2 ON edges (a pearl exactly 2);
 *   - black: turn, and go straight through the next cell on both sides;
 *   - white: go straight, and turn in at least one neighbour;
 *   - no premature loop: the two ends of a partial path may only be joined
 *     when that closes the final loop (every ON edge and every pearl on it).
 * When propagation stalls we branch on an edge at the end of a path (ON
 * first, towards the nearest unvisited pearl, which keeps loops short).
 *
 * Once a loop is found we keep searching with branch and bound for a
 * shorter one until ~0.9 s (the first second is free).  With no loop yet we
 * search until HARD_LIMIT.
 *
 * Paste everything above the LOCAL main into HackerRank (keep its own main).
 * Local build:  gcc -O2 -DLOCAL solution.c -o masyu -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#ifdef _WIN32
#include <windows.h>
#else
#include <time.h>
#endif

#define MAXN 50
#define MAXCELL (MAXN * MAXN)
#define MAXE (2 * MAXCELL + 1)
#define TRAIL_MAX (1 << 21)

#define UNK 0
#define ON 1
#define OFF 2

#ifndef DFS_FIND
#define DFS_FIND 0.35
#endif
#define IMPROVE_UNTIL 0.9
#define HARD_LIMIT 6.0

/* N, E, S, W; opposite direction is (d + 2) & 3 */
static const int DR[4] = {-1, 0, 1, 0};
static const int DC[4] = {0, 1, 0, -1};

/* ---------- timing ---------- */

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

/* ---------- board ---------- */

static int R, C, NCELL, NE, EOFF;   /* EOFF: sentinel edge, always OFF (borders) */
static char pearl[MAXCELL];         /* 0, 'W' or 'B' */
static int npearl, pearl_list[MAXCELL];
static int nb[MAXCELL][4];          /* neighbour cell or -1 */
static int ce[MAXCELL][4];          /* edge id towards direction d (EOFF at border) */
static int eu[MAXE], ev[MAXE];      /* edge endpoints */
static int near_cnt[MAXCELL], near_list[MAXCELL][25];  /* pearls within 2 */

/* ---------- search state (every write goes through the trail) ---------- */

static int st[MAXE];
static int don[MAXCELL], dunk[MAXCELL];   /* ON / UNKNOWN edge counts */
static int mate[MAXCELL], plen[MAXCELL];  /* valid at path ends (don == 1) */
static int total_on, touched, nends, closed_;

static int *tr_addr[TRAIL_MAX];
static int tr_old[TRAIL_MAX];
static int tp;

static void tset(int *a, int v) {
    tr_addr[tp] = a;
    tr_old[tp] = *a;
    tp++;
    *a = v;
}

static void undo(int mark) {
    while (tp > mark) {
        tp--;
        *tr_addr[tp] = tr_old[tp];
    }
}

/* ---------- propagation queue ---------- */

static int queue[MAXCELL + 1], qh, qt;
static char inq[MAXCELL];

static void push(int x) {
    if (inq[x]) return;
    inq[x] = 1;
    queue[qt] = x;
    qt = qt == MAXCELL ? 0 : qt + 1;
}

static void clear_queue(void) {
    while (qh != qt) {
        inq[queue[qh]] = 0;
        qh = qh == MAXCELL ? 0 : qh + 1;
    }
}

static void touch(int x) {
    push(x);
    for (int i = 0; i < near_cnt[x]; ++i) push(near_list[x][i]);
}

static int edge_between(int x, int y) {
    for (int d = 0; d < 4; ++d)
        if (nb[x][d] == y) return ce[x][d];
    return -1;
}

static int is_on(int e) { return st[e] == ON; }
static int is_off(int e) { return st[e] == OFF; }

/* Returns 0 on contradiction. */
static int set_edge(int e, int v) {
    if (st[e] == v) return 1;
    if (st[e] != UNK) return 0;
    if (v == ON && closed_) return 0;
    int a = eu[e], b = ev[e];
    tset(&st[e], v);
    tset(&dunk[a], dunk[a] - 1);
    tset(&dunk[b], dunk[b] - 1);
    touch(a);
    touch(b);
    if (v == OFF) return 1;

    if (don[a] == 2 || don[b] == 2) return 0;
    int closing = don[a] == 1 && don[b] == 1 && mate[a] == b;
    int ea = don[a] ? mate[a] : a, la = don[a] ? plen[a] : 0;
    int eb = don[b] ? mate[b] : b, lb = don[b] ? plen[b] : 0;
    int ends = nends;
    ends += don[a] ? -1 : 1;
    ends += don[b] ? -1 : 1;
    tset(&nends, ends);
    tset(&don[a], don[a] + 1);
    tset(&don[b], don[b] + 1);
    tset(&total_on, total_on + 1);
    if (pearl[a] && don[a] == 1) tset(&touched, touched + 1);
    if (pearl[b] && don[b] == 1) tset(&touched, touched + 1);

    if (closing) {
        if (la + 1 != total_on || touched != npearl) return 0;
        tset(&closed_, 1);
        return 1;
    }
    int len = la + lb + 1;
    tset(&mate[ea], eb);
    tset(&mate[eb], ea);
    tset(&plen[ea], len);
    tset(&plen[eb], len);
    /* Joining the new ends would close a loop; only allowed if it is final. */
    int f = edge_between(ea, eb);
    if (f >= 0 && st[f] == UNK && !(len == total_on && touched == npearl))
        return set_edge(f, OFF);
    return 1;
}

static int cell_rule(int x) {
    int on = don[x], unk = dunk[x];
    if (on > 2) return 0;
    if (on == 2) {
        if (unk)
            for (int d = 0; d < 4; ++d)
                if (st[ce[x][d]] == UNK && !set_edge(ce[x][d], OFF)) return 0;
        return 1;
    }
    if (on == 1) {
        if (unk == 0) return 0;
        if (unk == 1)
            for (int d = 0; d < 4; ++d)
                if (st[ce[x][d]] == UNK) return set_edge(ce[x][d], ON);
        return 1;
    }
    if (pearl[x]) {
        if (unk < 2) return 0;
        if (unk == 2)
            for (int d = 0; d < 4; ++d)
                if (st[ce[x][d]] == UNK && !set_edge(ce[x][d], ON)) return 0;
        return 1;
    }
    if (unk == 1 || closed_)
        for (int d = 0; d < 4; ++d)
            if (st[ce[x][d]] == UNK && !set_edge(ce[x][d], OFF)) return 0;
    return 1;
}

static int black_rule(int p) {
    for (int d = 0; d < 4; ++d) {
        int q = nb[p][d];
        if (q < 0) continue;  /* edge is the OFF sentinel */
        int e = ce[p][d];
        int ok = !is_off(e) && !is_off(ce[q][d]) &&
                 !is_on(ce[q][(d + 1) & 3]) && !is_on(ce[q][(d + 3) & 3]);
        if (!ok && !set_edge(e, OFF)) return 0;
    }
    for (int d = 0; d < 2; ++d) {
        int a = ce[p][d], b = ce[p][d + 2];
        if (is_off(a) && !set_edge(b, ON)) return 0;
        if (is_off(b) && !set_edge(a, ON)) return 0;
        if (is_on(a) && !set_edge(b, OFF)) return 0;
        if (is_on(b) && !set_edge(a, OFF)) return 0;
    }
    for (int d = 0; d < 4; ++d)
        if (is_on(ce[p][d]) && !set_edge(ce[nb[p][d]][d], ON)) return 0;
    return 1;
}

/* Can white pearl p run along axis d (d = 0 vertical, 1 horizontal)? */
static int white_axis_possible(int p, int d) {
    int a = ce[p][d], b = ce[p][d + 2];
    if (is_off(a) || is_off(b)) return 0;
    /* both neighbours straight on this axis means no turn next to the pearl */
    return !(is_on(ce[nb[p][d]][d]) && is_on(ce[nb[p][d + 2]][d + 2]));
}

static int white_rule(int p) {
    int vpos = white_axis_possible(p, 0), hpos = white_axis_possible(p, 1);
    if (!vpos && !hpos) return 0;
    for (int axis = 0; axis < 2; ++axis) {
        int other = 1 - axis;
        int possible = axis == 0 ? vpos : hpos;
        int a = ce[p][axis], b = ce[p][axis + 2];
        if (!possible || is_on(ce[p][other]) || is_on(ce[p][other + 2])) {
            if (!set_edge(a, OFF) || !set_edge(b, OFF)) return 0;
            if (!set_edge(ce[p][other], ON) || !set_edge(ce[p][other + 2], ON)) return 0;
            continue;
        }
        if (is_on(a) && is_on(b)) {
            int na = ce[nb[p][axis]][axis], nbb = ce[nb[p][axis + 2]][axis + 2];
            if (is_on(na) && !set_edge(nbb, OFF)) return 0;
            if (is_on(nbb) && !set_edge(na, OFF)) return 0;
        }
    }
    return 1;
}

static int propagate(void) {
    while (qh != qt) {
        int x = queue[qh];
        qh = qh == MAXCELL ? 0 : qh + 1;
        inq[x] = 0;
        int ok = cell_rule(x);
        if (ok && pearl[x] == 'B') ok = black_rule(x);
        if (ok && pearl[x] == 'W') ok = white_rule(x);
        if (!ok) {
            clear_queue();
            return 0;
        }
    }
    return 1;
}

/* ---------- search ---------- */

static unsigned char best_st[MAXE];
static int best_len, have_best;
static long long nodes, node_cap;
static int aborted, cut, improving, attempt;
static double limit_time;

static unsigned long long rng_state = 88172645463325252ULL;

static unsigned rnd(void) {
    rng_state ^= rng_state << 13;
    rng_state ^= rng_state >> 7;
    rng_state ^= rng_state << 17;
    return (unsigned)(rng_state >> 32);
}

/* Every used cell and untouched pearl must stay mutually reachable through
 * edges that are not OFF, or no single loop can contain them all. */
static int seen_stamp[MAXCELL], stamp, bfs_q[MAXCELL], bdist[MAXCELL];

static int connected(void) {
    int start = -1;
    for (int i = 0; i < npearl && start < 0; ++i) start = pearl_list[i];
    int need = total_on + nends / 2 + (npearl - touched);
    stamp++;
    int h = 0, t = 0, found = 0;
    bfs_q[t++] = start;
    seen_stamp[start] = stamp;
    while (h < t) {
        int x = bfs_q[h++];
        if (don[x] || pearl[x]) found++;
        for (int d = 0; d < 4; ++d) {
            int y = nb[x][d];
            if (y >= 0 && st[ce[x][d]] != OFF && seen_stamp[y] != stamp) {
                seen_stamp[y] = stamp;
                bfs_q[t++] = y;
            }
        }
    }
    return found == need;
}

static void record(void) {
    if (have_best && total_on >= best_len) return;
    for (int e = 0; e < NE; ++e) best_st[e] = st[e] == ON;
    best_len = total_on;
    have_best = 1;
}

/* Pick the edge to branch on.  Returns -1 when nothing is left to decide.
 * With pearl_first, untouched pearls go first (fixing a pearl's orientation
 * propagates far).  Otherwise the most constrained path end, heading for the
 * nearest untouched pearl or the nearest end of another path. */
static int pearl_first;

static int choose_edge(void) {
    int x = -1, ties = 0;
    if (pearl_first) {
        for (int i = 0; i < npearl; ++i) {
            int p = pearl_list[i];
            if (don[p] != 0) continue;
            if (x < 0 || dunk[p] < dunk[x]) {
                x = p;
                ties = 1;
            } else if (dunk[p] == dunk[x] && attempt && rnd() % ++ties == 0) {
                x = p;
            }
        }
        if (x >= 0) {
            int first = attempt ? (int)(rnd() & 3) : 0;
            for (int k = 0; k < 4; ++k)
                if (st[ce[x][(first + k) & 3]] == UNK) return ce[x][(first + k) & 3];
        }
    }

    /* most constrained path end; ties broken at random after the first attempt */
    x = -1;
    ties = 0;
    for (int i = 0; i < NCELL; ++i) {
        if (don[i] != 1) continue;
        if (x < 0 || dunk[i] < dunk[x]) {
            x = i;
            ties = 1;
        } else if (dunk[i] == dunk[x] && attempt && rnd() % ++ties == 0) {
            x = i;
        }
    }
    if (x < 0) {
        /* no path yet: start at an untouched pearl */
        for (int i = 0; i < npearl; ++i)
            if (don[pearl_list[i]] == 0) { x = pearl_list[i]; break; }
        if (x < 0) return -1;
    }

    /* Multi-source BFS from everything x may head for (untouched pearls and
     * the ends of other paths) through free cells, so the chosen direction
     * goes around existing paths instead of into them. */
    int h = 0, t = 0;
    stamp++;
    for (int i = 0; i < npearl; ++i) {
        int p = pearl_list[i];
        if (don[p] == 0 && p != x) { seen_stamp[p] = stamp; bdist[p] = 0; bfs_q[t++] = p; }
    }
    if (don[x] == 1)
        for (int y = 0; y < NCELL; ++y)
            if (don[y] == 1 && y != x && y != mate[x]) { seen_stamp[y] = stamp; bdist[y] = 0; bfs_q[t++] = y; }
    if (t == 0 && don[x] == 1) {   /* only this path left: close it */
        seen_stamp[mate[x]] = stamp;
        bdist[mate[x]] = 0;
        bfs_q[t++] = mate[x];
    }
    while (h < t) {
        int u = bfs_q[h++];
        for (int d = 0; d < 4; ++d) {
            int w = nb[u][d];
            if (w >= 0 && don[w] == 0 && st[ce[u][d]] != OFF && seen_stamp[w] != stamp) {
                seen_stamp[w] = stamp;
                bdist[w] = bdist[u] + 1;
                bfs_q[t++] = w;
            }
        }
    }

    int best_e = -1, best_score = 1 << 30;
    for (int d = 0; d < 4; ++d) {
        int e = ce[x][d];
        if (st[e] != UNK) continue;
        int y = nb[x][d];
        int s = (seen_stamp[y] == stamp ? 4 * bdist[y] : 1 << 20) + (attempt ? (int)(rnd() % 7) : 0);
        if (s < best_score) { best_score = s; best_e = e; }
    }
    return best_e;
}

/* Probing (failed literals): if setting an edge one way leads straight to a
 * contradiction, it must go the other way.  Only edges at undecided pearls
 * and path ends are probed, which is where the deductions happen (e.g. three
 * whites in a row). */
static int probe_list[MAXE], probe_seen[MAXE], probe_stamp;

static int consistent(int e, int v) {
    int mark = tp;
    int ok = set_edge(e, v) && propagate();
#ifdef PROBE_CONN
    if (ok && !closed_) ok = connected();
#endif
    if (ok && closed_) record();
    undo(mark);
    clear_queue();
    return ok;
}

static int probe(void) {
    for (int round = 0; round < 4; ++round) {
        int n = 0, changed = 0;
        probe_stamp++;
        for (int x = 0; x < NCELL; ++x) {
            if (!(don[x] == 1 || (pearl[x] && don[x] == 0))) continue;
            for (int d = 0; d < 4; ++d) {
                int e = ce[x][d];
                if (st[e] == UNK && probe_seen[e] != probe_stamp) {
                    probe_seen[e] = probe_stamp;
                    probe_list[n++] = e;
                }
            }
        }
        for (int i = 0; i < n; ++i) {
            int e = probe_list[i];
            if (st[e] != UNK) continue;
            int v = !consistent(e, ON) ? OFF : !consistent(e, OFF) ? ON : UNK;
            if (v == UNK) continue;
            if (!set_edge(e, v) || !propagate()) return 0;
            changed = 1;
            if (closed_) return 1;
        }
        if (!changed) break;
    }
    return 1;
}

/* Returns 1 to stop the search (first loop found while not improving). */
static int dfs(void) {
    if ((++nodes & 255) == 0 && elapsed() > limit_time) aborted = 1;
    if (nodes > node_cap) cut = 1;
    if (aborted || cut) return 1;
    if (!propagate()) return 0;
#ifndef NO_PROBE
    if (!probe()) return 0;
#endif
    if (!closed_ && !connected()) return 0;
#ifdef STATS
    {
        static int root_done;
        extern int stat_known, stat_root_on, stat_max_touched, stat_max_on;
        if (!root_done) {
            root_done = 1;
            for (int e = 0; e < NE; ++e) stat_known += st[e] != UNK;
            stat_root_on = total_on;
        }
        if (touched > stat_max_touched) stat_max_touched = touched;
        if (total_on > stat_max_on) stat_max_on = total_on;
    }
#endif
    if (closed_) {
        record();
        return !improving;
    }
    /* loop length = cells on it >= cells already used + untouched pearls */
    if (have_best && total_on + nends / 2 + (npearl - touched) >= best_len) return 0;

    int e = choose_edge();
    if (e < 0) return 0;
    int mark = tp;
    if (set_edge(e, ON) && dfs()) return 1;
    undo(mark);
    clear_queue();
    if (aborted || cut) return 1;
    if (set_edge(e, OFF) && dfs()) return 1;
    undo(mark);
    clear_queue();
    return 0;
}

/* Restarts with a growing node budget: find a loop (until find_until), then,
 * once one is known, look for strictly shorter ones until improve_until. */
static void run_dfs(double find_until, double improve_until) {
    long long budget = 2000;
    for (attempt = 0;; ++attempt) {
        limit_time = have_best ? improve_until : find_until;
        if (elapsed() >= limit_time) break;
        improving = have_best;
        pearl_first = 0;
        aborted = cut = 0;
        node_cap = nodes + budget;
        int mark = tp;
        for (int x = 0; x < NCELL; ++x) push(x);
        int stopped = dfs();
        undo(mark);
        clear_queue();
        if (aborted) break;
        if (!stopped && !cut) break;   /* tree exhausted: best is optimal */
        if (!(stopped && !cut)) budget += budget / 2;
    }
}

/* ---------- annealing on the region the loop encloses ----------
 * A single loop is exactly the boundary of a hole-free, 4-connected set of
 * faces (the squares between cell centres) with no two faces touching only
 * at a corner.  Flipping one face while keeping that shape keeps a single
 * loop, so every state is a loop and the cost is just the pearl violations
 * (plus a small length term).  This finds loops where the DFS cannot join
 * its path fragments. */

static unsigned char fin[MAXN][MAXN];   /* face (r, c) spans cells r..r+1, c..c+1 */
static int FR, FC;
static const int RING_R[8] = {-1, -1, 0, 1, 1, 1, 0, -1};
static const int RING_C[8] = {0, 1, 1, 1, 0, -1, -1, -1};

static int face(int r, int c) {
    return r >= 0 && r < FR && c >= 0 && c < FC ? fin[r][c] : 0;
}

/* N=1 E=2 S=4 W=8, same bits as tile_of */
static int cmask(int x) {
    int r = x / C, c = x % C;
    int a = face(r - 1, c - 1), b = face(r - 1, c), cc = face(r, c - 1), d = face(r, c);
    return (a != b) | (b != d) << 1 | (cc != d) << 2 | (a != cc) << 3;
}

static int is_turn(int m) { return m == 3 || m == 6 || m == 12 || m == 9; }

static int pearl_cost(int p) {
    int m = cmask(p);
    if (pearl[p] == 'B') {
        if (!m) return 4;
        if (!is_turn(m)) return 3;
        int k = 0;
        for (int d = 0; d < 4; ++d)
            if (m >> d & 1) k += cmask(nb[p][d]) != ((d & 1) ? 10 : 5);
        return k;
    }
    if (!m) return 3;
    if (m != 5 && m != 10) return 2;
    int axis = m == 5 ? 0 : 1;
    return !is_turn(cmask(nb[p][axis])) && !is_turn(cmask(nb[p][axis + 2]));
}

/* Can face (r, c) flip without breaking the single-loop shape? */
static int flippable(int r, int c, int region_size) {
    int me = fin[r][c], v[8];
    if (me && region_size <= 1) return 0;
    for (int i = 0; i < 8; ++i) v[i] = face(r + RING_R[i], c + RING_C[i]) != me;  /* "other side" */
    /* after the flip, f joins the other side: it must touch it orthogonally,
     * the ring must hold exactly one run of it, and no diagonal-only contact */
    if (!(v[0] || v[2] || v[4] || v[6])) return 0;
    int runs = 0;
    for (int i = 0; i < 8; ++i) runs += v[i] && !v[(i + 7) & 7];
    if (runs != 1) return 0;
    for (int i = 1; i < 8; i += 2)
        if (v[i] && !v[i - 1] && !v[(i + 1) & 7]) return 0;
    return 1;
}

/* pearls whose cost reads a corner of face (r, c): 4x4 cells minus corners */
static int affected(int r, int c, int *out) {
    int n = 0;
    for (int i = r - 1; i <= r + 2; ++i)
        for (int j = c - 1; j <= c + 2; ++j) {
            if (i < 0 || i >= R || j < 0 || j >= C) continue;
            if ((i == r - 1 || i == r + 2) && (j == c - 1 || j == c + 2)) continue;
            if (pearl[i * C + j]) out[n++] = i * C + j;
        }
    return n;
}

static int corner_len(int r, int c) {
    int n = 0;
    for (int i = r; i <= r + 1; ++i)
        for (int j = c; j <= c + 1; ++j) n += cmask(i * C + j) != 0;
    return n;
}

static void record_faces(int len) {
    if (have_best && len >= best_len) return;
    for (int e = 0; e < NE; ++e) {
        int u = eu[e], v = ev[e];
        best_st[e] = (cmask(u) >> (v == u + 1 ? 1 : 2)) & 1;
    }
    best_len = len;
    have_best = 1;
}

#ifdef STATS
static int sa_min_cost = 1 << 30;
#endif
static unsigned char known[MAXE];   /* root deductions: UNK, ON or OFF */

/* the 4 edges on face (r, c)'s border: top, bottom, left, right */
static void face_edges(int r, int c, int *e) {
    e[0] = ce[r * C + c][1];
    e[1] = ce[(r + 1) * C + c][1];
    e[2] = ce[r * C + c][2];
    e[3] = ce[r * C + c + 1][2];
}

/* edge e is ON when the faces on its two sides differ */
static int face_edge_on(int e) {
    int u = eu[e], r = u / C, c = u % C;
    if (ev[e] == u + 1) return face(r - 1, c) != face(r, c);
    return face(r, c - 1) != face(r, c);
}

static int known_cost(int e) {
    return known[e] != UNK && (known[e] == ON) != face_edge_on(e);
}

static void anneal(double until) {
    FR = R - 1;
    FC = C - 1;
    /* start from the faces spanning the pearls' bounding box */
    int r0 = R, r1 = 0, c0 = C, c1 = 0;
    for (int i = 0; i < npearl; ++i) {
        int r = pearl_list[i] / C, c = pearl_list[i] % C;
        if (r < r0) r0 = r;
        if (r > r1) r1 = r;
        if (c < c0) c0 = c;
        if (c > c1) c1 = c;
    }
    if (r1 > FR - 1) r1 = FR - 1;
    if (c1 > FC - 1) c1 = FC - 1;
    if (r0 > r1) r0 = r1;
    if (c0 > c1) c0 = c1;
    int size = 0;
    for (int r = 0; r < FR; ++r)
        for (int c = 0; c < FC; ++c) {
            fin[r][c] = r >= r0 && r <= r1 && c >= c0 && c <= c1;
            size += fin[r][c];
        }
    int cost = 0, len = 0;
    for (int i = 0; i < npearl; ++i) cost += pearl_cost(pearl_list[i]);
    for (int e = 0; e < NE; ++e) cost += known_cost(e);
    for (int x = 0; x < NCELL; ++x) len += cmask(x) != 0;

#ifndef SA_T0
#define SA_T0 1.5
#define SA_TMIN 0.15
#define SA_DECAY 0.998
#endif
    const double lam = 0.02;
    double temp = SA_T0;
    int aff[16];
    for (long long it = 0;; ++it) {
        if ((it & 4095) == 0) {
            double now = elapsed();
            if (now >= until || (have_best && now >= IMPROVE_UNTIL)) break;
            temp *= SA_DECAY;
            if (temp < SA_TMIN) temp = SA_T0;   /* reheat */
        }
        int r, c;
        if (rnd() % 10 < 8) {
            /* work next to a violated pearl when one turns up quickly */
            int p = pearl_list[rnd() % npearl];
            for (int k = 0; k < 8 && cost && !pearl_cost(p); ++k) p = pearl_list[rnd() % npearl];
            r = p / C - 2 + (int)(rnd() % 4);
            c = p % C - 2 + (int)(rnd() % 4);
            if (r < 0 || r >= FR || c < 0 || c >= FC) continue;
        } else {
            r = rnd() % FR;
            c = rnd() % FC;
        }
        if (!flippable(r, c, size)) continue;
        int n = affected(r, c, aff), fe[4];
        face_edges(r, c, fe);
        int before = 0, after = 0;
        for (int i = 0; i < n; ++i) before += pearl_cost(aff[i]);
        for (int i = 0; i < 4; ++i) before += known_cost(fe[i]);
        int lb = corner_len(r, c);
        fin[r][c] ^= 1;
        for (int i = 0; i < n; ++i) after += pearl_cost(aff[i]);
        for (int i = 0; i < 4; ++i) after += known_cost(fe[i]);
        int la = corner_len(r, c);
        double delta = (after - before) + lam * (la - lb);
        if (delta <= 0 || (double)(rnd() % 1000000) / 1e6 < exp(-delta / temp)) {
            cost += after - before;
            len += la - lb;
            size += fin[r][c] ? 1 : -1;
            if (cost == 0) record_faces(len);
#ifdef STATS
            if (cost < sa_min_cost) sa_min_cost = cost;
#endif
        } else {
            fin[r][c] ^= 1;
        }
    }
}

/* ---------- setup and output ---------- */

static void build(char **grid) {
    NCELL = R * C;
    npearl = 0;
    NE = 0;
    for (int x = 0; x < NCELL; ++x) {
        char ch = grid[x / C][x % C];
        pearl[x] = (ch == 'W' || ch == 'B') ? ch : 0;
        if (pearl[x]) pearl_list[npearl++] = x;
    }
    for (int x = 0; x < NCELL; ++x)
        for (int d = 0; d < 4; ++d) {
            int r = x / C + DR[d], c = x % C + DC[d];
            nb[x][d] = (r >= 0 && r < R && c >= 0 && c < C) ? r * C + c : -1;
        }
    for (int x = 0; x < NCELL; ++x)
        for (int d = 1; d <= 2; ++d)   /* E and S edges own the id */
            if (nb[x][d] >= 0) {
                eu[NE] = x;
                ev[NE] = nb[x][d];
                ce[x][d] = NE;
                ce[nb[x][d]][d ^ 2] = NE;   /* E<->W is 1<->3, S<->N is 2<->0 */
                NE++;
            }
    EOFF = NE;
    for (int x = 0; x < NCELL; ++x)
        for (int d = 0; d < 4; ++d)
            if (nb[x][d] < 0) ce[x][d] = EOFF;
    for (int x = 0; x < NCELL; ++x) {
        near_cnt[x] = 0;
        for (int i = 0; i < npearl; ++i) {
            int p = pearl_list[i];
            if (abs(p / C - x / C) <= 2 && abs(p % C - x % C) <= 2)
                near_list[x][near_cnt[x]++] = p;
        }
    }

    for (int e = 0; e < NE; ++e) st[e] = UNK;
    st[EOFF] = OFF;
    for (int x = 0; x < NCELL; ++x) {
        don[x] = 0;
        dunk[x] = 0;
        for (int d = 0; d < 4; ++d) dunk[x] += nb[x][d] >= 0;
        mate[x] = x;
        plen[x] = 0;
        inq[x] = 0;
    }
    total_on = touched = nends = closed_ = 0;
    tp = 0;
    qh = qt = 0;
}

static char tile_of(int x) {
    int m = 0;
    for (int d = 0; d < 4; ++d)
        if (ce[x][d] != EOFF && best_st[ce[x][d]]) m |= 1 << d;
    switch (m) {
    case 1 | 4: return '|';
    case 2 | 8: return '-';
    case 1 | 2: return 'L';
    case 1 | 8: return 'J';
    case 4 | 2: return 'F';
    case 4 | 8: return '7';
    }
    return '.';
}

char **solve(int grid_count, char **grid, int *result_count) {
    t_start = wall_now();
    R = grid_count;
    C = 0;
    while (grid[0][C] == '.' || grid[0][C] == 'W' || grid[0][C] == 'B') C++;
    build(grid);

    have_best = 0;
    best_len = 0;
    nodes = 0;

    /* root deductions, kept for the annealer */
    {
        int mark = tp;
        for (int x = 0; x < NCELL; ++x) push(x);
        int ok = propagate() && probe();
        for (int e = 0; e < NE; ++e) known[e] = ok ? st[e] : UNK;
        undo(mark);
        clear_queue();
    }
    run_dfs(DFS_FIND, IMPROVE_UNTIL);
    if (!have_best) anneal(HARD_LIMIT);
    if (have_best && elapsed() < IMPROVE_UNTIL) run_dfs(IMPROVE_UNTIL, IMPROVE_UNTIL);

    char **ans = malloc(R * sizeof(char *));
    for (int r = 0; r < R; ++r) {
        ans[r] = malloc(C + 1);
        for (int c = 0; c < C; ++c) ans[r][c] = have_best ? tile_of(r * C + c) : '.';
        ans[r][C] = '\0';
    }
    *result_count = R;
    return ans;
}

#ifdef CHECKSOL
/* Debug: read a puzzle followed by a known solution, impose the solution's
 * edges one by one and report the first step the rules reject. */
int main(void) {
    int n;
    if (scanf("%d", &n) != 1) return 1;
    static char g[MAXN][128], s[MAXN][128];
    char *rows[MAXN];
    for (int i = 0; i < n; ++i) { if (scanf("%127s", g[i]) != 1) return 1; rows[i] = g[i]; }
    for (int i = 0; i < n; ++i) if (scanf("%127s", s[i]) != 1) return 1;
    t_start = wall_now();
    R = n;
    C = strlen(g[0]);
    build(rows);
    for (int x = 0; x < NCELL; ++x) push(x);
    if (!propagate()) { printf("root contradiction\n"); return 0; }
    for (int e = 0; e < NE; ++e) {
        int a = eu[e], b = ev[e], d = b == a + 1 ? 1 : 2;
        char t = s[a / C][a % C];
        int has = (d == 1) ? (t == '-' || t == 'L' || t == 'F') : (t == '|' || t == 'F' || t == '7');
        if (!set_edge(e, has ? ON : OFF) || !propagate() || (!closed_ && !connected())) {
            printf("contradiction at edge %d (%d,%d)-(%d,%d) want %s\n", e,
                   a / C, a % C, b / C, b % C, has ? "ON" : "OFF");
            return 0;
        }
    }
    printf("ok closed=%d len=%d\n", closed_, total_on);
    return 0;
}
#elif defined(LOCAL)
#ifdef STATS
int stat_known, stat_root_on, stat_max_touched, stat_max_on;
#endif
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
    fprintf(stderr, "time %.3f len %d nodes %lld\n", elapsed(), have_best ? best_len : -1, nodes);
#ifdef STATS
    fprintf(stderr, "edges %d root_known %d root_on %d pearls %d max_touched %d max_on %d\n",
            NE, stat_known, stat_root_on, npearl, stat_max_touched, stat_max_on);
    fprintf(stderr, "sa_min_cost %d\n", sa_min_cost);
#endif
    return 0;
}
#endif
