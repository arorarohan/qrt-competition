import ast
import math
import re
import sys
import time


TIME_LIMIT_SECONDS = 4.5


def parse_sizes(text):
    text = text.strip()
    if not text:
        return []

    if text.lstrip().startswith("["):
        try:
            value = ast.literal_eval(text)
            return [int(x) for x in value]
        except Exception:
            pass

    nums = [int(x) for x in re.findall(r"-?\d+", text)]
    if len(nums) >= 1 and len(nums) == nums[0] + 1:
        return nums[1:]
    return nums


def ceil_div(a, b):
    return (a + b - 1) // b


def bounding_area(coords, sizes):
    if not sizes:
        return 0
    height = 0
    width = 0
    for (x, y), s in zip(coords, sizes):
        height = max(height, x + s)
        width = max(width, y + s)
    return height * width


def lower_bound_area(sizes):
    if not sizes:
        return 0
    return sum(s * s for s in sizes)


def normalize(coords, sizes):
    if not sizes:
        return coords
    min_x = min(x for x, _ in coords)
    min_y = min(y for _, y in coords)
    return [(x - min_x, y - min_y) for x, y in coords]


def shelf_pack(sizes, width, order=None):
    if not sizes:
        return []
    if width < max(sizes):
        return None

    if order is None:
        order = sorted(range(len(sizes)), key=lambda i: (-sizes[i], i))

    coords = [None] * len(sizes)
    row_x = 0
    row_y = 0
    row_h = 0

    for i in order:
        s = sizes[i]
        if row_y and row_y + s > width:
            row_x += row_h
            row_y = 0
            row_h = 0
        coords[i] = (row_x, row_y)
        row_y += s
        row_h = max(row_h, s)

    return coords


def skyline_pack(sizes, width, order=None, height_limit=None, deadline=None):
    if not sizes:
        return []
    if width < max(sizes):
        return None

    if order is None:
        order = sorted(range(len(sizes)), key=lambda i: (-sizes[i], i))

    coords = [None] * len(sizes)
    skyline = [(0, width, 0)]  # (y0, y1, current occupied height)

    def interval_height(y0, y1):
        h = 0
        for a, b, v in skyline:
            if a < y1 and y0 < b:
                h = max(h, v)
        return h

    def place_interval(y0, y1, new_h):
        updated = []
        for a, b, h in skyline:
            if b <= y0 or y1 <= a:
                updated.append((a, b, h))
            else:
                if a < y0:
                    updated.append((a, y0, h))
                if y1 < b:
                    updated.append((y1, b, h))
        updated.append((y0, y1, new_h))
        updated.sort()

        merged = []
        for a, b, h in updated:
            if a == b:
                continue
            if merged and merged[-1][1] == a and merged[-1][2] == h:
                merged[-1] = (merged[-1][0], b, h)
            else:
                merged.append((a, b, h))
        return merged

    for placed_count, i in enumerate(order):
        if placed_count % 16 == 0 and deadline is not None and time.perf_counter() > deadline:
            return None
        s = sizes[i]
        candidate_ys = {0}
        for a, b, _ in skyline:
            if a + s <= width:
                candidate_ys.add(a)
            y = b - s
            if y >= 0:
                candidate_ys.add(y)

        best = None
        for y in candidate_ys:
            if y + s > width:
                continue
            x = interval_height(y, y + s)
            if height_limit is not None and x + s > height_limit:
                continue
            score = (x + s, x, y)
            if best is None or score < best:
                best = score

        if best is None:
            return None

        _, x, y = best
        coords[i] = (x, y)
        skyline = place_interval(y, y + s, x + s)

    return coords


def row_pack(sizes):
    coords = []
    y = 0
    for s in sizes:
        coords.append((0, y))
        y += s
    return coords


def col_pack(sizes):
    coords = []
    x = 0
    for s in sizes:
        coords.append((x, 0))
        x += s
    return coords


def rects_overlap(a, b):
    ax, ay, ah, aw = a
    bx, by, bh, bw = b
    return ax < bx + bh and bx < ax + ah and ay < by + bw and by < ay + aw


def rect_contains(a, b):
    ax, ay, ah, aw = a
    bx, by, bh, bw = b
    return ax <= bx and ay <= by and ax + ah >= bx + bh and ay + aw >= by + bw


def prune_free_rects(rects):
    cleaned = [r for r in rects if r[2] > 0 and r[3] > 0]
    result = []
    for i, r in enumerate(cleaned):
        contained = False
        for j, other in enumerate(cleaned):
            if i != j and rect_contains(other, r):
                contained = True
                break
        if not contained:
            result.append(r)
    return result


def split_free_rect(free_rect, used_rect):
    fx, fy, fh, fw = free_rect
    ux, uy, uh, uw = used_rect

    if not rects_overlap(free_rect, used_rect):
        return [free_rect]

    out = []
    if ux > fx:
        out.append((fx, fy, ux - fx, fw))
    if ux + uh < fx + fh:
        out.append((ux + uh, fy, fx + fh - ux - uh, fw))
    if uy > fy:
        out.append((fx, fy, fh, uy - fy))
    if uy + uw < fy + fw:
        out.append((fx, uy + uw, fh, fy + fw - uy - uw))
    return out


def maxrects_score(free_rect, s, heuristic, placed, height, width):
    x, y, h, w = free_rect
    short_side = min(h - s, w - s)
    long_side = max(h - s, w - s)
    area_waste = h * w - s * s

    if heuristic == "area":
        return (area_waste, short_side, long_side, x, y)
    if heuristic == "bottom_left":
        return (x, y, short_side, area_waste)
    if heuristic == "contact":
        contact = 0
        if x == 0:
            contact += s
        if y == 0:
            contact += s
        if x + s == height:
            contact += s
        if y + s == width:
            contact += s
        for px, py, ps in placed:
            if px + ps == x or x + s == px:
                contact += max(0, min(y + s, py + ps) - max(y, py))
            if py + ps == y or y + s == py:
                contact += max(0, min(x + s, px + ps) - max(x, px))
        return (-contact, area_waste, short_side, x, y)
    return (short_side, long_side, area_waste, x, y)


def maxrects_pack(sizes, width, height, heuristic="short_side", order=None, deadline=None):
    if not sizes:
        return []
    if width < max(sizes) or height < max(sizes):
        return None

    if order is None:
        order = sorted(range(len(sizes)), key=lambda i: (-sizes[i], i))

    free_rects = [(0, 0, height, width)]
    coords = [None] * len(sizes)
    placed = []

    for placed_count, i in enumerate(order):
        if placed_count % 8 == 0 and deadline is not None and time.perf_counter() > deadline:
            return None
        s = sizes[i]
        best_index = -1
        best_score = None

        for j, rect in enumerate(free_rects):
            x, y, h, w = rect
            if s <= h and s <= w:
                score = maxrects_score(rect, s, heuristic, placed, height, width)
                if best_score is None or score < best_score:
                    best_score = score
                    best_index = j

        if best_index < 0:
            return None

        x, y, _, _ = free_rects[best_index]
        used = (x, y, s, s)
        coords[i] = (x, y)
        placed.append((x, y, s))

        new_free = []
        for rect in free_rects:
            new_free.extend(split_free_rect(rect, used))
        if deadline is not None and time.perf_counter() > deadline:
            return None
        free_rects = prune_free_rects(new_free)

    return coords


def transformed_rotated_pack(sizes, width, height, heuristic, order, deadline):
    rotated = maxrects_pack(sizes, height, width, heuristic, order, deadline)
    if rotated is None:
        return None
    return [(y, x) for x, y in rotated]


def transformed_rotated_skyline(sizes, width, height, order, deadline):
    rotated = skyline_pack(sizes, height, order, height_limit=width, deadline=deadline)
    if rotated is None:
        return None
    return [(y, x) for x, y in rotated]


def width_candidates(sizes, best_area=None, exhaustive_limit=5000, cap=1400):
    if not sizes:
        return []

    m = max(sizes)
    total = sum(s * s for s in sizes)
    root = max(m, math.isqrt(total))
    if root * root < total:
        root += 1

    if best_area is None:
        hi = max(m, ceil_div(total, m))
    else:
        hi = max(m, (best_area - 1) // m)
    lo = m
    if hi < lo:
        return [m]

    candidates = set()
    if hi - lo <= exhaustive_limit:
        candidates.update(range(lo, hi + 1))
    else:
        candidates.update([lo, hi, root])

        window = 350 if len(sizes) <= 200 else 120
        for w in range(max(lo, root - window), min(hi, root + window) + 1):
            candidates.add(w)

        for h in range(max(m, root - window), root + window + 1):
            w = ceil_div(total, h)
            for d in (-3, -2, -1, 0, 1, 2, 3):
                ww = w + d
                if lo <= ww <= hi:
                    candidates.add(ww)

        top = sorted(sizes, reverse=True)[:40]
        running = 0
        for s in top:
            running += s
            if lo <= running <= hi:
                candidates.add(running)
        for i, a in enumerate(top[:25]):
            for b in top[i:25]:
                w = a + b
                if lo <= w <= hi:
                    candidates.add(w)
        for s in top:
            for w in (m + s, root + s, root - s):
                if lo <= w <= hi:
                    candidates.add(w)

        # Coarse coverage keeps very rectangular good solutions reachable.
        samples = cap // 4
        for k in range(samples + 1):
            w = lo + (hi - lo) * k // max(1, samples)
            candidates.add(w)

    candidates = [w for w in candidates if lo <= w <= hi]
    candidates.sort(key=lambda w: (w * max(m, ceil_div(total, w)), abs(w - root), w))
    if len(candidates) > cap:
        keep = set(candidates[: cap * 3 // 4])
        stride = max(1, len(candidates) // (cap // 4))
        keep.update(candidates[::stride])
        candidates = sorted(keep, key=lambda w: (w * max(m, ceil_div(total, w)), abs(w - root), w))
        candidates = candidates[:cap]
    return candidates


def choose_better(current, candidate, sizes):
    if candidate is None:
        return current
    candidate = normalize(candidate, sizes)
    if current is None:
        return candidate
    if bounding_area(candidate, sizes) < bounding_area(current, sizes):
        return candidate
    return current


def initial_solution(sizes, deadline):
    if not sizes:
        return []

    best = row_pack(sizes)
    best = choose_better(best, col_pack(sizes), sizes)

    total = sum(s * s for s in sizes)
    root = max(max(sizes), math.isqrt(total))
    if root * root < total:
        root += 1

    n = len(sizes)
    if n <= 40:
        shelf_cap, skyline_cap = 700, 450
    elif n <= 150:
        shelf_cap, skyline_cap = 350, 160
    elif n <= 500:
        shelf_cap, skyline_cap = 180, 70
    else:
        shelf_cap, skyline_cap = 90, 35

    widths = set(width_candidates(sizes, None, exhaustive_limit=shelf_cap, cap=shelf_cap))
    widths.update([max(sizes), root, ceil_div(total, max(sizes))])
    widths = sorted(widths, key=lambda w: (w * max(max(sizes), ceil_div(total, w)), abs(w - root), w))

    order_desc = sorted(range(len(sizes)), key=lambda i: (-sizes[i], i))
    order_desc_rev = sorted(range(len(sizes)), key=lambda i: (-sizes[i], -i))
    order_input = list(range(len(sizes)))
    for width in widths:
        if time.perf_counter() > deadline:
            return best
        for order in (order_desc, order_input):
            best = choose_better(best, shelf_pack(sizes, width, order), sizes)

    skyline_orders = (order_desc, order_desc_rev, order_input) if n <= 150 else (order_desc,)
    for width in widths[:skyline_cap]:
        if time.perf_counter() > deadline:
            return best
        for order in skyline_orders:
            best = choose_better(best, skyline_pack(sizes, width, order, deadline=deadline), sizes)
    return best


def try_fixed_rectangle(sizes, width, height, deadline, order):
    if time.perf_counter() > deadline:
        return None

    packed = skyline_pack(sizes, width, order, height_limit=height, deadline=deadline)
    if packed is not None:
        return packed
    if width != height:
        packed = transformed_rotated_skyline(sizes, width, height, order, deadline)
        if packed is not None:
            return packed

    if len(sizes) > 220:
        return None

    heuristics = ["short_side", "area", "bottom_left"]
    if len(sizes) <= 120:
        heuristics.append("contact")

    for heuristic in heuristics:
        if time.perf_counter() > deadline:
            return None
        packed = maxrects_pack(sizes, width, height, heuristic, order, deadline)
        if packed is not None:
            return packed

        if width != height:
            packed = transformed_rotated_pack(sizes, width, height, heuristic, order, deadline)
            if packed is not None:
                return packed
    return None


def improve_with_rectangles(sizes, best, deadline):
    if not sizes:
        return best

    m = max(sizes)
    total = sum(s * s for s in sizes)
    order = sorted(range(len(sizes)), key=lambda i: (-sizes[i], i))

    while time.perf_counter() < deadline:
        best_area = bounding_area(best, sizes)
        improved = False
        if len(sizes) <= 40:
            cap = 1200
        elif len(sizes) <= 150:
            cap = 450
        elif len(sizes) <= 500:
            cap = 140
        else:
            cap = 60
        widths = width_candidates(sizes, best_area, exhaustive_limit=cap, cap=cap)

        for width in widths:
            if time.perf_counter() > deadline:
                return best

            min_height = max(m, ceil_div(total, width))
            max_height = (best_area - 1) // width
            if max_height < min_height:
                continue

            lo = min_height
            hi = max_height
            best_for_width = None

            while lo <= hi and time.perf_counter() < deadline:
                mid = (lo + hi) // 2
                packed = try_fixed_rectangle(sizes, width, mid, deadline, order)
                if packed is None:
                    lo = mid + 1
                else:
                    best_for_width = packed
                    hi = mid - 1

            if best_for_width is not None:
                old_area = bounding_area(best, sizes)
                best = choose_better(best, best_for_width, sizes)
                if bounding_area(best, sizes) < old_area:
                    improved = True

                    if bounding_area(best, sizes) <= lower_bound_area(sizes):
                        return best

        if not improved:
            return best
    return best


def intervals_overlap(a0, a1, b0, b1):
    return a0 < b1 and b0 < a1


def exact_corner_search(sizes, width, height, deadline):
    n = len(sizes)
    if n == 0:
        return []
    if n > 11:
        return None
    if width < max(sizes) or height < max(sizes):
        return None

    order = sorted(range(n), key=lambda i: (-sizes[i], i))
    remaining_area_suffix = [0] * (n + 1)
    for k in range(n - 1, -1, -1):
        s = sizes[order[k]]
        remaining_area_suffix[k] = remaining_area_suffix[k + 1] + s * s

    coords = [None] * n
    placed = []
    seen = set()

    def can_place(x, y, s):
        if x + s > height or y + s > width:
            return False
        for px, py, ps, _ in placed:
            if x < px + ps and px < x + s and y < py + ps and py < y + s:
                return False
        return True

    def search(k, used_area):
        if time.perf_counter() > deadline:
            return False
        if k == n:
            return True
        if width * height - used_area < remaining_area_suffix[k]:
            return False

        state = (
            k,
            tuple(sorted((px, py, ps) for px, py, ps, _ in placed)),
        )
        if state in seen:
            return False
        seen.add(state)

        idx = order[k]
        s = sizes[idx]

        xs = {0}
        ys = {0}
        for px, py, ps, _ in placed:
            xs.add(px + ps)
            ys.add(py + ps)

        positions = []
        for x in xs:
            if x + s > height:
                continue
            for y in ys:
                if y + s > width or not can_place(x, y, s):
                    continue

                top_supported = x == 0 or any(
                    px + ps == x and intervals_overlap(y, y + s, py, py + ps)
                    for px, py, ps, _ in placed
                )
                left_supported = y == 0 or any(
                    py + ps == y and intervals_overlap(x, x + s, px, px + ps)
                    for px, py, ps, _ in placed
                )
                support_bonus = int(top_supported) + int(left_supported)
                positions.append((-support_bonus, max(x + s, y + s), x + y, x, y))

        positions.sort()
        for _, _, _, x, y in positions:
            coords[idx] = (x, y)
            placed.append((x, y, s, idx))
            if search(k + 1, used_area + s * s):
                return True
            placed.pop()
            coords[idx] = None
        return False

    if search(0, 0):
        return coords
    return None


def improve_small_cases(sizes, best, deadline):
    if len(sizes) > 11 or not sizes:
        return best

    best_area = bounding_area(best, sizes)
    lb = lower_bound_area(sizes)
    if best_area == lb:
        return best

    m = max(sizes)
    total = sum(s * s for s in sizes)
    dims = set()
    widths = width_candidates(sizes, best_area, exhaustive_limit=12000, cap=3500)

    for w in widths:
        h0 = max(m, ceil_div(total, w))
        h1 = (best_area - 1) // w
        if h1 < h0:
            continue
        for h in range(h0, min(h1, h0 + 8) + 1):
            dims.add((w, h))
            dims.add((h, w))

    ordered_dims = sorted(dims, key=lambda wh: (wh[0] * wh[1], abs(wh[0] - wh[1]), wh[0]))
    for width, height in ordered_dims:
        if time.perf_counter() > deadline:
            return best
        if width * height >= bounding_area(best, sizes):
            break
        packed = exact_corner_search(sizes, width, height, deadline)
        if packed is not None:
            best = choose_better(best, packed, sizes)
            if bounding_area(best, sizes) <= lb:
                return best
    return best


def solve(sizes):
    sizes = [int(s) for s in sizes]
    if not sizes:
        return []

    start = time.perf_counter()
    deadline = start + TIME_LIMIT_SECONDS

    best = initial_solution(sizes, deadline)
    best = improve_with_rectangles(sizes, best, deadline)
    best = improve_small_cases(sizes, best, deadline)
    return normalize(best, sizes)


def pack_squares(squares):
    return [[x, y] for x, y in solve(squares)]


def format_answer(coords):
    return "[" + ",".join(f"({x},{y})" for x, y in coords) + "]"


def main():
    sizes = parse_sizes(sys.stdin.read())
    coords = solve(sizes)
    print(format_answer(coords))


if __name__ == "__main__":
    main()
