"""Independent oracles and validators for my own tests.

The oracles are deliberately written differently from the solution
(brute force, memoised recursion over suffixes, built-in startswith on
every position, direct sorting of suffix strings), so a shared bug is
unlikely. validate(request, answer) returns (ok, reason).
"""

from functools import lru_cache
from itertools import combinations


def is_subsequence(s, t):
    it = iter(t)
    return all(c in it for c in s)


# ---------- LCS ----------
def lcs_len(a, b):
    """Memoised recursion over SUFFIXES (the solution uses prefixes)."""
    import sys
    sys.setrecursionlimit(10000)

    @lru_cache(maxsize=None)
    def f(i, j):
        if i == len(a) or j == len(b):
            return 0
        if a[i] == b[j]:
            return 1 + f(i + 1, j + 1)
        return max(f(i + 1, j), f(i, j + 1))
    return f(0, 0)


def check_lcs(req, ans):
    a, b = req["a"], req["b"]
    if not isinstance(ans.get("length"), int) or not isinstance(ans.get("sequence"), str):
        return False, "schema"
    best = lcs_len(a, b) if len(a) * len(b) <= 40000 else ans["length"]
    if ans["length"] != best:
        return False, f"length {ans['length']} != {best}"
    s = ans["sequence"]
    if len(s) != best or not is_subsequence(s, a) or not is_subsequence(s, b):
        return False, "sequence is not a common subsequence of optimal length"
    return True, "ok"


# ---------- merge ----------
def merge_brute(sizes):
    """Try every order of adjacent merges (exponential, small n only)."""
    @lru_cache(maxsize=None)
    def best(blocks):
        if len(blocks) <= 1:
            return 0
        res = None
        for i in range(len(blocks) - 1):
            merged = blocks[i] + blocks[i + 1]
            c = merged + best(blocks[:i] + (merged,) + blocks[i + 2:])
            res = c if res is None else min(res, c)
        return res
    return best(tuple(sizes))


def simulate_plan(sizes, plan):
    """Return the cost of a plan, or None if any step is invalid."""
    blocks = [(i, i) for i in range(len(sizes))]
    total = 0
    for step in plan:
        if not (isinstance(step, list) and len(step) == 3):
            return None
        l, k, r = step
        if (l, k) not in blocks or (k + 1, r) not in blocks:
            return None
        i = blocks.index((l, k))
        if i + 1 >= len(blocks) or blocks[i + 1] != (k + 1, r):
            return None                       # must be adjacent current blocks
        total += sum(sizes[l:r + 1])
        blocks[i:i + 2] = [(l, r)]
    if len(sizes) > 0 and len(blocks) != 1:
        return None
    return total


def check_merge(req, ans):
    sizes = req["sizes"]
    if not isinstance(ans.get("cost"), int) or not isinstance(ans.get("plan"), list):
        return False, "schema"
    n = len(sizes)
    best = merge_brute(sizes) if n <= 8 else ans["cost"]
    if ans["cost"] != best:
        return False, f"cost {ans['cost']} != {best}"
    if n <= 1:
        return (ans["plan"] == []), "plan must be empty"
    if len(ans["plan"]) != n - 1:
        return False, "plan needs n-1 merges"
    if simulate_plan(sizes, ans["plan"]) != ans["cost"]:
        return False, "plan invalid or its cost differs"
    return True, "ok"


# ---------- tree ----------
def check_tree(req, ans):
    n, w, edges = req["n"], req["weights"], req["edges"]
    if not isinstance(ans.get("weight"), int) or not isinstance(ans.get("selected"), list):
        return False, "schema"
    sel = ans["selected"]
    if len(set(sel)) != len(sel) or any(not (0 <= v < n) for v in sel):
        return False, "repeated or out-of-range vertex"
    chosen = set(sel)
    if any(u in chosen and v in chosen for u, v in edges):
        return False, "two adjacent vertices selected"
    if sum(w[v] for v in sel) != ans["weight"]:
        return False, "weight is not the sum of selected"
    if n <= 15:                                   # brute force over all subsets
        best = 0
        for r in range(1, n + 1):
            for sub in combinations(range(n), r):
                s = set(sub)
                if not any(u in s and v in s for u, v in edges):
                    best = max(best, sum(w[v] for v in sub))
        if ans["weight"] != best:
            return False, f"weight {ans['weight']} != {best}"
    return True, "ok"


# ---------- search ----------
def search_oracle(text, pattern):
    return [i for i in range(len(text) - len(pattern) + 1) if text.startswith(pattern, i)]


def check_search(req, ans):
    pos = ans.get("positions")
    if not isinstance(pos, list):
        return False, "schema"
    want = search_oracle(req["text"], req["pattern"])
    return (pos == want), f"positions differ ({len(pos)} vs {len(want)})"


# ---------- suffix ----------
def check_suffix(req, ans):
    t = req["text"]
    n = len(t)
    sa, lcp, rep = ans.get("sa"), ans.get("lcp"), ans.get("repeated")
    if not isinstance(sa, list) or not isinstance(lcp, list) or not isinstance(rep, str):
        return False, "schema"
    if n <= 3000:
        want_sa = sorted(range(n), key=lambda i: t[i:])
    else:                                          # large: check order pairwise
        want_sa = sa
        if sorted(sa) != list(range(n)):
            return False, "sa is not a permutation"
        for x in range(1, n):
            i, j = sa[x - 1], sa[x]
            h = lcp[x]
            if t[i:i + h] != t[j:j + h] or (j + h < n and i + h < n and t[i + h] >= t[j + h]) \
               or (j + h >= n):
                return False, f"order/lcp wrong at {x}"
    if sa != want_sa:
        return False, "sa differs"

    def direct(i, j):
        h = 0
        while i + h < n and j + h < n and t[i + h] == t[j + h]:
            h += 1
        return h

    want_lcp = ([0] + [direct(sa[x - 1], sa[x]) for x in range(1, n)]) if n else []
    if n <= 3000 and lcp != want_lcp:
        return False, "lcp differs"
    best = max(want_lcp) if n else 0
    if len(rep) != best:
        return False, "repeated is not longest"
    if best and len(search_oracle(t, rep)) < 2:
        return False, "repeated does not occur twice"
    return True, "ok"


# ---------- aho ----------
def check_aho(req, ans):
    counts = ans.get("counts")
    if not isinstance(counts, list):
        return False, "schema"
    want = [[len(search_oracle(t, p)) for p in req["patterns"]] for t in req["texts"]]
    return (counts == want), "counts differ"


CHECK = {"lcs": check_lcs, "merge": check_merge, "tree": check_tree,
         "naive": check_search, "kmp": check_search, "rk": check_search,
         "suffix": check_suffix, "aho": check_aho}


def validate(req, ans):
    return CHECK[req["task"]](req, ans)
