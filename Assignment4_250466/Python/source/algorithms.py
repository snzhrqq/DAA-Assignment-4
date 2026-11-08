"""Assignment 4 — dynamic programming and string processing (Python).

Every command receives one request dictionary and returns one result
dictionary. All working data is created inside the call, so no state
survives between requests. No recursion is used, so deep trees and long
strings cannot hit Python's recursion limit.
"""

from collections import deque


# ---------------------------------------------------------------------------
# Part 1: LCS — prefix dynamic programming
# ---------------------------------------------------------------------------

def lcs(request):
    a = request["a"]
    b = request["b"]
    n, m = len(a), len(b)
    if n == 0 or m == 0:
        return {"length": 0, "sequence": ""}

    # dp[i][j] = LCS length of prefixes a[:i] and b[:j]; row 0 / column 0 = 0.
    dp = [[0] * (m + 1)]
    for i in range(1, n + 1):
        prev = dp[i - 1]
        cur = [0] * (m + 1)
        ai = a[i - 1]
        for j in range(1, m + 1):
            if ai == b[j - 1]:
                cur[j] = prev[j - 1] + 1          # match: extend diagonal
            else:
                up, left = prev[j], cur[j - 1]    # mismatch: drop a char of a or b
                cur[j] = up if up >= left else left
        dp.append(cur)

    # Reconstruction: walk back from (n, m) following a transition that
    # produced the stored value.
    out = []
    i, j = n, m
    while i > 0 and j > 0:
        if a[i - 1] == b[j - 1]:
            out.append(a[i - 1])
            i -= 1
            j -= 1
        elif dp[i - 1][j] >= dp[i][j - 1]:
            i -= 1
        else:
            j -= 1
    out.reverse()
    return {"length": dp[n][m], "sequence": "".join(out)}


# ---------------------------------------------------------------------------
# Part 2: ordered adjacent-block merging — interval DP
# ---------------------------------------------------------------------------

def merge(request):
    sizes = request["sizes"]
    n = len(sizes)
    if n <= 1:
        return {"cost": 0, "plan": []}

    prefix = [0] * (n + 1)
    for i, s in enumerate(sizes):
        prefix[i + 1] = prefix[i] + s

    # cost[l][r] = minimum cost to turn blocks l..r into one block.
    # split[l][r] = k of the LAST merge [l,k] + [k+1,r] in an optimal plan.
    cost = [[0] * n for _ in range(n)]
    split = [[-1] * n for _ in range(n)]
    for length in range(2, n + 1):              # shorter intervals first
        for l in range(0, n - length + 1):
            r = l + length - 1
            row_l = cost[l]
            best = None
            best_k = l
            for k in range(l, r):
                c = row_l[k] + cost[k + 1][r]
                if best is None or c < best:
                    best = c
                    best_k = k
            cost[l][r] = best + prefix[r + 1] - prefix[l]
            split[l][r] = best_k

    # Reconstruction in postorder: children merges before the parent merge.
    plan = []
    stack = [(0, n - 1, False)]
    while stack:
        l, r, expanded = stack.pop()
        if l == r:
            continue
        k = split[l][r]
        if expanded:
            plan.append([l, k, r])
        else:
            stack.append((l, r, True))          # parent is emitted after children
            stack.append((k + 1, r, False))
            stack.append((l, k, False))
    return {"cost": cost[0][n - 1], "plan": plan}


# ---------------------------------------------------------------------------
# Part 3: maximum-weight independent set on a tree — take/skip DP
# ---------------------------------------------------------------------------

def tree(request):
    n = request["n"]
    weights = request["weights"]
    if n == 0:
        return {"weight": 0, "selected": []}

    adj = [[] for _ in range(n)]
    for u, v in request["edges"]:
        adj[u].append(v)
        adj[v].append(u)

    # Iterative BFS from root 0 gives parent pointers and an order in which
    # every parent appears before its children.
    parent = [-1] * n
    order = [0]
    seen = [False] * n
    seen[0] = True
    for v in order:                     # the list grows while we iterate
        for w in adj[v]:
            if not seen[w]:
                seen[w] = True
                parent[w] = v
                order.append(w)

    # take[v] = best weight in v's subtree when v IS selected
    # skip[v] = best weight in v's subtree when v is NOT selected
    take = [0] * n
    skip = [0] * n
    for v in reversed(order):           # postorder: children before parent
        take[v] += weights[v]
        p = parent[v]
        if p != -1:
            take[p] += skip[v]                      # parent taken -> child skipped
            skip[p] += take[v] if take[v] > skip[v] else skip[v]

    # Reconstruction top-down: a child may be taken only if its parent was not.
    chosen = [False] * n
    selected = []
    for v in order:                     # parents before children
        p = parent[v]
        if p != -1 and chosen[p]:
            continue                    # forced skip
        if take[v] > skip[v]:           # ties -> skip (also keeps weight 0 for all-negative)
            chosen[v] = True
            selected.append(v)
    best = take[0] if take[0] > skip[0] else skip[0]
    return {"weight": best, "selected": selected}


# ---------------------------------------------------------------------------
# Part 4: exact string search — naive, KMP, Rabin–Karp
# ---------------------------------------------------------------------------

def naive(request):
    text = request["text"]
    pattern = request["pattern"]
    n, m = len(text), len(pattern)
    if m == 0:
        return {"positions": list(range(n + 1))}   # every boundary 0..n
    positions = []
    for i in range(0, n - m + 1):                  # last valid start n-m
        j = 0
        while j < m and text[i + j] == pattern[j]:
            j += 1
        if j == m:
            positions.append(i)
    return {"positions": positions}


def _prefix_function(pattern):
    """pi[i] = length of the longest proper prefix of pattern[:i+1]
    that is also its suffix."""
    m = len(pattern)
    pi = [0] * m
    k = 0
    for i in range(1, m):
        c = pattern[i]
        while k > 0 and pattern[k] != c:
            k = pi[k - 1]                           # fall back
        if pattern[k] == c:
            k += 1
        pi[i] = k
    return pi


def kmp(request):
    text = request["text"]
    pattern = request["pattern"]
    n, m = len(text), len(pattern)
    if m == 0:
        return {"positions": list(range(n + 1))}
    if m > n:
        return {"positions": []}
    pi = _prefix_function(pattern)
    positions = []
    k = 0                                           # characters currently matched
    for i in range(n):
        c = text[i]
        while k > 0 and pattern[k] != c:
            k = pi[k - 1]                           # mismatch fallback
        if pattern[k] == c:
            k += 1
        if k == m:
            positions.append(i - m + 1)
            k = pi[k - 1]                           # fallback after a full match keeps overlaps
    return {"positions": positions}


RK_BASE = 31
RK_MOD = 101


def rk(request):
    text = request["text"]
    pattern = request["pattern"]
    n, m = len(text), len(pattern)
    if m == 0:
        return {"positions": list(range(n + 1))}
    if m > n:
        return {"positions": []}

    # Highest power belongs to the leftmost character.
    high = pow(RK_BASE, m - 1, RK_MOD)              # base^(m-1) mod p
    hp = 0
    hw = 0
    for i in range(m):
        hp = (hp * RK_BASE + ord(pattern[i])) % RK_MOD
        hw = (hw * RK_BASE + ord(text[i])) % RK_MOD

    positions = []
    for i in range(0, n - m + 1):
        if hw == hp:                                # candidate only
            j = 0
            while j < m and text[i + j] == pattern[j]:
                j += 1                              # verify actual characters
            if j == m:
                positions.append(i)
        if i + m < n:
            # remove leftmost char, shift, add the new rightmost char;
            # Python's % already returns a non-negative remainder.
            hw = ((hw - ord(text[i]) * high) * RK_BASE + ord(text[i + m])) % RK_MOD
    return {"positions": positions}


# ---------------------------------------------------------------------------
# Part 5: suffix array (prefix doubling) + Kasai LCP
# ---------------------------------------------------------------------------

def suffix(request):
    text = request["text"]
    n = len(text)
    if n == 0:
        return {"sa": [], "lcp": [], "repeated": ""}

    # Prefix doubling: rank[i] = class of the first k characters of suffix i.
    rank = [ord(c) for c in text]
    sa = list(range(n))
    k = 1
    while True:
        # Sort by the pair (rank[i], rank[i+k]); -1 means "past the end",
        # which is smaller than every character, so no sentinel is stored.
        width = max(rank) + 2               # second component is in 0..max(rank)+1
        key = [rank[i] * width + (rank[i + k] + 1 if i + k < n else 0) for i in range(n)]
        sa.sort(key=key.__getitem__)
        new_rank = [0] * n
        r = 0
        for idx in range(1, n):
            if key[sa[idx]] != key[sa[idx - 1]]:
                r += 1
            new_rank[sa[idx]] = r
        rank = new_rank
        if r == n - 1:                              # all ranks distinct -> done
            break
        k *= 2

    # Kasai: process suffixes in text order and reuse h - 1.
    lcp = [0] * n
    h = 0
    for i in range(n):
        p = rank[i]
        if p == 0:
            h = 0
            continue
        j = sa[p - 1]                               # previous suffix in sorted order
        while i + h < n and j + h < n and text[i + h] == text[j + h]:
            h += 1
        lcp[p] = h
        if h > 0:
            h -= 1

    best = 0
    best_at = 0
    for p in range(1, n):
        if lcp[p] > best:
            best = lcp[p]
            best_at = sa[p]
    return {"sa": sa, "lcp": lcp, "repeated": text[best_at:best_at + best]}


# ---------------------------------------------------------------------------
# Part 6: Aho–Corasick dictionary counting
# ---------------------------------------------------------------------------

def aho(request):
    patterns = request["patterns"]
    texts = request["texts"]
    p = len(patterns)

    # Trie: children[s] maps a character to the next state; state 0 = root.
    children = [{}]
    terminal_of = []                    # state that ends each dictionary position
    for pat in patterns:
        s = 0
        for c in pat:
            nxt = children[s].get(c)
            if nxt is None:
                nxt = len(children)
                children.append({})
                children[s][c] = nxt
            s = nxt
        terminal_of.append(s)           # duplicates share one terminal state

    S = len(children)
    is_terminal = [False] * S
    for s in terminal_of:
        is_terminal[s] = True

    # BFS: failure links (longest proper suffix that is also a trie path)
    # and the BFS order used for propagation.
    fail = [0] * S
    order = []
    queue = deque()
    for c, v in children[0].items():
        queue.append(v)
    while queue:
        u = queue.popleft()
        order.append(u)
        for c, v in children[u].items():
            f = fail[u]
            while f and c not in children[f]:
                f = fail[f]
            fv = children[f].get(c, 0)
            fail[v] = fv if fv != v else 0
            queue.append(v)

    # out[s] = nearest terminal state on the failure chain of s (s itself
    # included), or 0 if none. Only terminal states take part in counting,
    # so per-text propagation is over at most p states, not all S.
    out = [0] * S
    for u in order:                     # BFS order: fail[u] is processed earlier
        out[u] = u if is_terminal[u] else out[fail[u]]
    term_order = [u for u in order if is_terminal[u]]
    term_parent = {u: out[fail[u]] for u in term_order}   # next terminal on the chain

    counts = []
    for text in texts:
        visits = {}                     # fresh counts for every independent text
        s = 0
        for c in text:
            while s and c not in children[s]:
                s = fail[s]
            s = children[s].get(c, 0)
            t = out[s]
            if t:
                visits[t] = visits.get(t, 0) + 1
        # Propagate visits from deep terminals to shorter suffix terminals.
        for u in reversed(term_order):
            cnt = visits.get(u)
            if cnt:
                par = term_parent[u]
                if par:
                    visits[par] = visits.get(par, 0) + cnt
        counts.append([visits.get(terminal_of[i], 0) for i in range(p)])
    return {"counts": counts}
