#!/usr/bin/env python3
import itertools, random, string

LOOK = {
    "o": "0", "0": "o", "l": "1i", "1": "li", "i": "1l", "s": "5", "5": "s",
    "z": "2", "2": "z", "e": "3", "3": "e", "a": "4", "4": "a", "g": "9q",
    "9": "gq", "q": "9g", "t": "7", "7": "t", "b": "86", "8": "b", "6": "b",
    "u": "v", "v": "u", "m": "n", "n": "m",
}

def variants(name):
    res, seen = [], set()
    for i, ch in enumerate(name):
        for r in LOOK.get(ch, ""):
            v = name[:i] + r + name[i + 1:]
            if v != name and v not in seen:
                seen.add(v)
                res.append(v)
    return res

def near(name, pool):
    res = []
    for i, ch in enumerate(name):
        for c in pool:
            if c != ch:
                res.append(name[:i] + c + name[i + 1:])
    random.shuffle(res)
    return res

def runs(L, pool):
    out = []
    for seq in (string.ascii_lowercase, string.digits):
        for step in (1, 2):
            for s in range(len(seq)):
                idx = [s + step * i for i in range(L)]
                if idx[-1] < len(seq):
                    w = "".join(seq[i] for i in idx)
                    out += [w, w[::-1]]
    return [w for w in out if all(c in pool for c in w)]

def special_set(L, pool):
    out = set()
    for c in pool:
        out.add(c * L)
    for a in pool:
        for b in pool:
            if a != b:
                out.add("".join(a if i % 2 == 0 else b for i in range(L)))
            for k in range(1, L):
                out.add(a * k + b * (L - k))
    h = (L + 1) // 2
    for half in itertools.product(pool, repeat=h):
        s = "".join(half)
        out.add(s + s[::-1][L % 2:])
    out.update(runs(L, pool))
    return out

def gen_random(L, pool):
    seen, total = set(), len(pool) ** L
    while len(seen) < total:
        n = "".join(random.choices(pool, k=L))
        if n not in seen:
            seen.add(n)
            yield n

def gen_ordered(L, pool):
    first = sorted(set(runs(L, pool)))
    seen = set(first)
    for w in first:
        yield w
    for t in itertools.product(pool, repeat=L):
        w = "".join(t)
        if w not in seen:
            yield w

def gen_similar(L, pool, base, tak):
    m = len(base)
    if m == L:
        lk = variants(base)
        nr = [v for v in near(base, pool) if v not in lk]
        if tak:
            for v in lk + nr:
                yield (base, v)
        else:
            yield base
            for v in lk + nr:
                yield v
        return
    seen, miss = set(), 0
    cap = (L - m + 1) * len(pool) ** (L - m)
    while len(seen) < cap and miss < 5000:
        p = random.randint(0, L - m)
        n = ("".join(random.choices(pool, k=p)) + base + "".join(random.choices(pool, k=L - m - p)))
        if n in seen:
            miss += 1
            continue
        miss = 0
        seen.add(n)
        if tak:
            v = variants(n) or near(n, pool)
            yield (n, random.choice(v))
        else:
            yield n

def make_gen(L, mode, pool, base, tak):
    if mode == "random":
        return gen_random(L, pool)
    if mode == "special":
        items = list(special_set(L, pool))
        random.shuffle(items)
        return iter(items)
    if mode == "ordered":
        return gen_ordered(L, pool)
    return gen_similar(L, pool, base, tak)