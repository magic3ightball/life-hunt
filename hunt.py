"""Soup search for Life-like rules: separate objects, compute apgcodes,
and compare against the Catagolue census to flag rare / unseen objects.

  python3 hunt.py --rule b3s23 --soups 20000
"""
import argparse
import collections
import hashlib
import json
import pickle
import os
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "census_cache")
ENC = "0123456789abcdefghijklmnopqrstuvwxyz"

# ---------- Life on cell sets ----------

def parse_rule(rule):
    b, s = set(), set()
    cur = None
    for ch in rule.lower():
        if ch == "b":
            cur = b
        elif ch == "s":
            cur = s
        elif ch.isdigit() and cur is not None:
            cur.add(int(ch))
    return b, s


def step(cells, rule):
    b, s = rule
    cnt = collections.Counter()
    for x, y in cells:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx or dy:
                    cnt[(x + dx, y + dy)] += 1
    out = {c for c, n in cnt.items() if (n in s if c in cells else n in b)}
    if 0 in b:
        raise ValueError("B0 rules not supported")
    return frozenset(out)


def normalize(cells):
    if not cells:
        return frozenset(), (0, 0)
    mx = min(x for x, _ in cells)
    my = min(y for _, y in cells)
    return frozenset((x - mx, y - my) for x, y in cells), (mx, my)

# ---------- apgcode (extended Wechsler) ----------

def wechsler(cells):
    w = max(x for x, _ in cells) + 1
    h = max(y for _, y in cells) + 1
    strips = []
    for sy in range(0, h, 5):
        cols = []
        for x in range(w):
            v = 0
            for k in range(5):
                if (x, sy + k) in cells:
                    v |= 1 << k
            cols.append(v)
        while cols and cols[-1] == 0:
            cols.pop()
        s = "".join(ENC[v] for v in cols)
        strips.append(compress_zeros(s))
    return "z".join(strips)


def compress_zeros(s):
    out, i = [], 0
    while i < len(s):
        if s[i] != "0":
            out.append(s[i])
            i += 1
            continue
        j = i
        while j < len(s) and s[j] == "0":
            j += 1
        n = j - i
        while n > 0:
            if n == 1:
                out.append("0"); n = 0
            elif n == 2:
                out.append("w"); n = 0
            elif n == 3:
                out.append("x"); n = 0
            else:
                k = min(n, 39)
                out.append("y" + ENC[k - 4]); n -= k
        i = j
    return "".join(out)


TRANSFORMS = [
    lambda x, y: (x, y), lambda x, y: (-x, y), lambda x, y: (x, -y), lambda x, y: (-x, -y),
    lambda x, y: (y, x), lambda x, y: (-y, x), lambda x, y: (y, -x), lambda x, y: (-y, -x),
]


def canon(phases):
    best = None
    for ph in phases:
        for t in TRANSFORMS:
            c, _ = normalize({t(x, y) for x, y in ph})
            w = wechsler(c)
            key = (len(w), w)
            if best is None or key < best:
                best = key
    return best[1]

# ---------- object classification ----------

def classify(cells, rule, maxp):
    """Evolve an isolated object; return (apgcode, phases) or (None, reason)."""
    start, _ = normalize(cells)
    cur = frozenset(cells)
    phases = [cur]
    pop0 = len(cur)
    for g in range(1, maxp + 1):
        cur = step(cur, rule)
        if not cur:
            return None, "dies"
        nc, off = normalize(cur)
        if nc == start:
            nph = [normalize(p)[0] for p in phases]
            o0 = normalize(cells)[1]
            moved = off != o0
            if moved:
                return "xq%d_%s" % (g, canon(nph)), nph
            if g == 1:
                return "xs%d_%s" % (pop0, canon(nph)), nph
            return "xp%d_%s" % (g, canon(nph)), nph
        phases.append(cur)
    return None, "noperiod"


def components(cells, radius=2):
    cells = set(cells)
    seen, comps = set(), []
    for c in cells:
        if c in seen:
            continue
        stack, comp = [c], []
        seen.add(c)
        while stack:
            x, y = stack.pop()
            comp.append((x, y))
            for dx in range(-radius, radius + 1):
                for dy in range(-radius, radius + 1):
                    q = (x + dx, y + dy)
                    if q in cells and q not in seen:
                        seen.add(q)
                        stack.append(q)
        comps.append(comp)
    return comps


def orbit(cells, rule, gens):
    out = [frozenset(cells)]
    for _ in range(gens):
        out.append(step(out[-1], rule))
    return out


def split_pseudo(sub, rule, gens):
    """Finest partition of an object into parts that each repeat on their own
    (period dividing `gens`) and together evolve exactly like the whole.
    Built from 8-connected pieces; None if the object is strict."""
    pieces = [frozenset(p) for p in components(sub, 1)]
    if len(pieces) < 2 or len(pieces) > 12:
        return None
    whole = orbit(sub, rule, gens)
    valid = {}

    def ok(mask):
        if mask not in valid:
            cells = frozenset().union(*(pieces[i] for i in range(len(pieces)) if mask >> i & 1))
            valid[mask] = (cells, orbit(cells, rule, gens))
        cells, orb = valid[mask]
        return orb[-1] == cells

    best = None

    def search(rest, chosen):
        nonlocal best
        if not rest:
            if best is None or len(chosen) > len(best):
                orbs = [valid[m][1] for m in chosen]
                if all(frozenset().union(*(o[t] for o in orbs)) == whole[t] for t in range(gens + 1)):
                    best = list(chosen)
            return
        low = rest & -rest
        sub_mask = rest
        while sub_mask:  # every subset of rest that contains the lowest piece
            if sub_mask & low and ok(sub_mask):
                search(rest & ~sub_mask, chosen + [sub_mask])
            sub_mask = (sub_mask - 1) & rest

    search((1 << len(pieces)) - 1, [])
    if best is None or len(best) < 2:
        return None
    return [valid[m][0] for m in best]


def identify(sub, rule, period):
    """Classify one object, splitting pseudo-objects into their constituents."""
    code, info = classify(sub, rule, period)
    if not code:
        return [("zz_" + info, sorted(sub))]
    p = int(code[2:].split("_")[0])
    parts = split_pseudo(sub, rule, max(p, 2))
    if parts:
        out = []
        for part in parts:
            out += identify(part, rule, period)
        return out
    return [(code, sorted(sub))]


def separate(state, period, rule):
    """Split a periodic soup ash into objects. Returns list of (code, cells)."""
    phases = [frozenset(state)]
    for _ in range(period - 1):
        phases.append(step(phases[-1], rule))
    union = set().union(*phases)
    results = []
    for comp in components(union):
        comp = set(comp)
        sub = frozenset(c for c in phases[0] if c in comp)
        if not sub:
            continue
        key, (ox, oy) = normalize(sub)
        if key not in MEMO:
            MEMO[key] = identify(key, rule, period)
        results += [(code, [(x + ox, y + oy) for x, y in cells]) for code, cells in MEMO[key]]
    return results


MEMO = {}


def work(args):
    rule_s, prefix, start, count = args
    rule = parse_rule(rule_s)
    seeds = "".join(f"{i} {hashlib.sha256(f'{prefix}{i}'.encode()).hexdigest()}\n"
                    for i in range(start, start + count))
    # seeds go through a file: feeding stdin while soup fills stdout can deadlock
    with tempfile.TemporaryFile("w+") as f:
        f.write(seeds)
        f.seek(0)
        out = subprocess.run([os.path.join(HERE, "soup"), rule_s], stdin=f,
                             capture_output=True, text=True, check=True).stdout
    tally = collections.Counter()
    samples = {}
    unstable = []
    for line in out.splitlines():
        f = line.split()
        kind, idx = f[0], int(f[1])
        if kind == "U":
            unstable.append(idx)
            continue
        if kind == "S":
            period, n = int(f[2]), int(f[4])
            nums = list(map(int, f[5:5 + 2 * n]))
            state = list(zip(nums[0::2], nums[1::2]))
            objs = separate(state, period, rule) if state else []
        else:
            n = int(f[3])
            nums = list(map(int, f[4:4 + 2 * n]))
            cells = frozenset(zip(nums[0::2], nums[1::2]))
            objs = []
            for piece in components(cells):
                objs += identify(frozenset(piece), rule, 64)
        for code, cells in objs:
            tally[code] += 1
            if code not in samples:
                samples[code] = (idx, cells)
    return tally, samples, unstable

# ---------- Catagolue census ----------

def census(rule, prefix):
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, f"{rule}_{prefix}.csv")
    if not os.path.exists(path):
        url = f"https://catagolue.hatsya.com/textcensus/{rule}/C1/{prefix}"
        r = subprocess.run(["curl", "-sf", "--max-time", "60", url], capture_output=True, text=True)
        if r.returncode != 0 or not r.stdout.startswith('"apgcode"'):
            print("census fetch failed", url, file=sys.stderr)
            return None
        data = r.stdout
        open(path, "w").write(data)
    d = {}
    for line in open(path).read().splitlines()[1:]:
        parts = line.replace('"', "").split(",")
        if len(parts) == 2:
            d[parts[0]] = int(parts[1])
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rule", default="b3s23")
    ap.add_argument("--soups", type=int, default=10000)
    ap.add_argument("--prefix", default="hunt" + time.strftime("%Y%m%d%H%M%S"))
    ap.add_argument("--chunk", type=int, default=50)
    ap.add_argument("--rare", type=int, default=1000, help="flag codes with census count below this")
    a = ap.parse_args()

    jobs = [(a.rule, a.prefix, s, min(a.chunk, a.soups - s)) for s in range(0, a.soups, a.chunk)]
    ckpt = os.path.join(HERE, "results", f"{a.rule}_{a.prefix}.ckpt")
    os.makedirs(os.path.dirname(ckpt), exist_ok=True)
    tally, samples, unstable, done, spent = collections.Counter(), {}, [], 0, 0
    if os.path.exists(ckpt):  # resume an interrupted run with the same prefix
        tally, samples, unstable, done, spent = pickle.load(open(ckpt, "rb"))
        print(f"resuming after {done} chunks", file=sys.stderr)
    t0 = time.time() - spent
    with ProcessPoolExecutor() as ex:
        for i, (t, smp, u) in enumerate(ex.map(work, jobs[done:]), start=done + 1):
            tally.update(t)
            for k, v in smp.items():
                samples.setdefault(k, v)
            unstable += u
            if i % 10 == 0:
                print(f"{sum(j[3] for j in jobs[:i])} soups, {time.time() - t0:.0f}s", file=sys.stderr, flush=True)
            if i % 50 == 0 or i == len(jobs):
                pickle.dump((tally, samples, unstable, i, time.time() - t0), open(ckpt + ".tmp", "wb"))
                os.replace(ckpt + ".tmp", ckpt)

    finds = []
    for code, n in tally.most_common():
        if code.startswith("zz"):
            cens = None
        else:
            prefix = code.split("_")[0]
            table = census(a.rule, prefix)
            cens = None if table is None else table.get(code, 0)
        idx, cells = samples[code]
        finds.append({"code": code, "count": n, "census": cens, "soup": f"{a.prefix}{idx}",
                      "cells": cells})

    report = {"rule": a.rule, "prefix": a.prefix, "soups": a.soups, "seconds": round(time.time() - t0),
              "unstable": [f"{a.prefix}{i}" for i in unstable], "objects": finds}
    out = os.path.join(HERE, "results", f"{a.rule}_{a.prefix}.json")
    json.dump(report, open(out, "w"))

    print(f"rule {a.rule}: {a.soups} soups in {report['seconds']}s, {len(tally)} distinct objects")
    print("most common:", ", ".join(f"{c}×{n}" for c, n in tally.most_common(6)))
    print(f"\nRARE (census < {a.rare}) or UNSEEN:")
    for f in finds:
        if f["census"] is not None and f["census"] < a.rare:
            tag = "NEW?" if f["census"] == 0 else f"census {f['census']}"
            print(f"  {tag:>14}  {f['code']}  https://catagolue.hatsya.com/hashsoup/C1/{f['soup']}/{a.rule}")
    odd = [f for f in finds if f["code"].startswith("zz")]
    if odd:
        print("unclassified:", ", ".join(f"{f['code']}×{f['count']}" for f in odd))
    if unstable:
        print("never stabilized (possible guns/puffers):", ", ".join(report["unstable"][:10]))
    print("saved", out)


if __name__ == "__main__":
    main()
