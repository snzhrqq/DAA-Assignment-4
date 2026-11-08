# Assignment 4 — analysis

## Environment and commands

* Language: **Python** (`submission.json`: `{"language": "Python"}`); CPython 3.13.18. Implementation: `Python/source/algorithms.py`; the supplied `main.py` is unchanged.
* Machine used for the recorded runs: Linux x86_64 (cloud container), Intel Xeon @ 2.30 GHz, 2 vCPUs, 7 GB RAM.
* Python is interpreted, so there is no build step. Commands (from the repository root):

```sh
python tools/run.py --setup                                  # startup check
python tools/run.py --check                                  # 44 public cases + repeated mixed batch
python tools/run.py --input tests/student/cases.jsonl        # my fixtures -> tests/student/cases_actual.jsonl
python tests/student/run_tests.py                            # my tests (log: tests/student/test_output.txt)
python tests/student/benchmark_search.py                     # search comparison (output: tests/student/benchmark_output.txt)
```

Recorded results: `--setup` PASS; `--check` all 44 public cases PASS and the repeated mixed batch PASS; `run_tests.py` ALL TESTS PASSED.

**State reset.** Every command builds all of its tables, tries, queues and counters as local variables inside the call, and nothing is stored at module level, so consecutive requests cannot share state. Each Aho–Corasick text starts with a fresh count dictionary. No function is recursive (tree DP uses BFS order, merge reconstruction uses an explicit stack), so deep inputs cannot overflow the call stack.

## Algorithm explanations

### lcs — prefix DP

* **State.** `dp[i][j]` = length of an LCS of the prefixes `a[:i]` and `b[:j]` (`i` characters of `a`, `j` of `b`).
* **Base cases.** `dp[0][j] = dp[i][0] = 0` (an empty prefix has no common subsequence). If either string is empty, the function returns `0, ""` immediately.
* **Transition.** If `a[i-1] == b[j-1]`: `dp[i][j] = dp[i-1][j-1] + 1`. Otherwise `dp[i][j] = max(dp[i-1][j], dp[i][j-1])`.
* **Order.** Rows `i = 1..n`, columns `j = 1..m`; the three cells used (up, left, diagonal) are always computed earlier.
* **Correctness.** If the last characters match, some optimal LCS ends with that match (exchange argument), so we use it. If they differ, an LCS cannot use both last characters, so it is an LCS of `a[:i-1], b[:j]` or of `a[:i], b[:j-1]`; the mismatch transition takes the better one.
* **Reconstruction.** Walk back from `(n, m)`: on a character match take it and move diagonally; otherwise move to the neighbour holding the larger value (ties go up). Every step follows a transition that produced the stored value, so the collected characters (reversed) form a common subsequence of length `dp[n][m]`. Ties choose one of several optimal answers; any optimum is accepted.
* **Complexity.** `O((|a|+1)(|b|+1))` time and memory for the table (list of Python lists), `O(min)` for the output.
* **Boundary test.** `a="tea_time", b="team"` → `team` (a subsequence, not a substring): detects an implementation that computes the longest common *substring*.

### merge — interval DP

* **State.** `cost[l][r]` = minimum cost to merge original blocks `l..r` into one block; `split[l][r]` = the `k` of the **last** merge `[l,k] + [k+1,r]`.
* **Base cases.** `cost[i][i] = 0`; for `n <= 1` return `0, []`.
* **Transition.** `cost[l][r] = min over k in [l, r-1] of cost[l][k] + cost[k+1][r] + sum(l..r)`. The last merge always costs the total size of the interval, whatever happened before; prefix sums give `sum(l..r)` in O(1).
* **Order.** Intervals by increasing length, so both halves are ready.
* **Correctness.** In any plan the final merge joins two adjacent intervals `[l,k]` and `[k+1,r]` that were built independently; their optimal costs are optimal subproblems, so minimising over `k` gives the optimum. Merging the smallest two arbitrary blocks (greedy) is wrong because blocks must be adjacent (`[1,100,1]` → 203, not a non-adjacent 2).
* **Reconstruction.** Iterative postorder over `split`: the left and right child intervals are emitted before their parent merge `[l,k,r]`, so the plan is chronological and every step merges two blocks that already exist and are adjacent. Exactly `n-1` merges. Ties keep the first minimal `k`; other optimal plans are equally valid.
* **Complexity.** `O(n^3)` time, `O(n^2)` memory (two `n×n` tables); `O(1)` for `n <= 1`. Costs are exact Python integers (e.g. `5·10^9` in my test).
* **Boundary test.** `[0,0,0,0]` → cost 0 with several optimal plans: detects code that requires a unique witness or rejects zero sizes.

### tree — maximum-weight independent set (take/skip)

* **State.** For root 0: `take[v]` = best weight of `v`'s subtree if `v` is selected; `skip[v]` = best if `v` is not selected.
* **Transition.** `take[v] = w[v] + Σ skip[c]`; `skip[v] = Σ max(take[c], skip[c])` over children `c`.
* **Base case / empty set.** A leaf has `take = w`, `skip = 0`. Because skipping is always allowed, all-negative inputs give `0` with an empty selection. `n = 0` → `0, []`.
* **Order.** An iterative BFS from root 0 gives parent pointers and an order where parents come before children; processing that order **in reverse** is a postorder (children before parents). No recursion, so a 100 000-vertex chain works.
* **Correctness.** The root's optimum is `max(take[0], skip[0])`. An independent set either contains `v` (then no child) or not (then each child subtree is free), which is exactly the two transitions. Any root gives the same optimum, since the maximum-weight independent set is a property of the tree, not of the rooting.
* **Reconstruction.** Top-down in BFS order: a vertex whose parent was chosen is skipped; otherwise it is chosen iff `take[v] > skip[v]` (ties → skip). This reproduces the decisions that achieved each stored value, never selects two neighbours, and lists each vertex once.
* **Complexity.** `O(n+1)` time and memory including reconstruction; totals are exact Python integers.
* **Boundary test.** Deep chain of 100 000 vertices: detects recursive DFS (stack overflow).

### naive

* Empty pattern → all `n+1` boundaries `0..n`. Otherwise try every start `i = 0..n-m` (the last valid start is `n-m`; for `m > n` the range is empty) and compare characters one by one. Overlapping matches are found because every start is tried.
* **Complexity.** `O(n·m + n + 1)` time; `O(1)` auxiliary plus `O(z+1)` output.
* **Boundary test.** `"aaaaa"/"aaa"` → `[0,1,2]`: detects skipping `m` characters after a match.

### kmp

* **Prefix function.** `pi[i]` = length of the longest proper prefix of `pattern[:i+1]` that is also its suffix. Built incrementally: on mismatch fall back `k = pi[k-1]`.
* **Search.** `k` = number of pattern characters currently matched. On mismatch `k = pi[k-1]` until a match or `k = 0`; on match `k += 1`. When `k == m`, report start `i-m+1` and fall back `k = pi[m-1]` — this keeps overlapping matches.
* **Correctness.** Invariant: after reading `text[i]`, `pattern[:k]` is the longest pattern prefix that is a suffix of `text[:i+1]`. The fallback only skips alignments that `pi` proves cannot match.
* **Empty / long pattern.** `m = 0` returns `0..n` before any indexing; `m > n` returns `[]`.
* **Complexity.** `O(n + m + z + 1)` time (each fallback undoes an earlier increment), `O(m+1)` auxiliary, `O(z+1)` output.
* **Boundary test.** `"abababa"/"aba"` → `[0,2,4]`: detects resetting `k = 0` after a full match.

### rk — exact Rabin–Karp (base 31, modulus 101)

* **Hash.** `h(s) = (s0·31^(m-1) + s1·31^(m-2) + … + s(m-1)) mod 101` with ASCII codes; the highest power belongs to the leftmost character.
* **Rolling update.** `h' = ((h − ord(out)·31^(m-1))·31 + ord(in)) mod 101`. The subtraction can be negative; Python's `%` returns a value in `0..100`, so the remainder is always normalised (other languages need `(x % p + p) % p`).
* **Verification.** An equal hash is only a *candidate*: characters are compared before reporting. With modulus 101 collisions are common (`h("ab") = h("dj") = 75`), so the check is essential.
* **Boundaries.** `m = 0` → `0..n`; `m > n` → `[]`, both before forming a window. Overlaps are kept.
* **Complexity.** `O(n + m + c·m)` time where `c` is the number of equal-hash windows; with `c ≈ n` (e.g. text and pattern all `'a'`) this is `O(n·m)`. Bound for all inputs: `O(n·m + n + m + 1)`. It is **not** deterministic linear time. `O(m+1)` auxiliary (rolling window).
* **Boundary test.** `"abdj"/"ab"` → `[0]` and `"abdjab"/"dj"` → `[2]`: detects reporting hash matches without verification.

### suffix — prefix doubling + Kasai

**Doubling.** `rank[i]` starts as the character code. In each round sort suffixes by the pair `(rank[i], rank[i+k])`, where "past the end" is encoded as the smallest value, so a suffix that is a prefix of another sorts first and **no sentinel is stored**. The pair is packed into one integer `rank[i]·W + (rank[i+k]+1 or 0)`, `W = max(rank)+2`, and the index list is sorted with Python's `list.sort` (TimSort, comparison-based). New ranks are assigned by scanning the sorted order; stop when all `n` ranks are distinct, otherwise double `k`. Invariant: after a round with step `k`, ranks order suffixes by their first `2k` characters. Suffix strings are never materialised.

*Complexity:* at most `⌈log2 n⌉+1` rounds, each `O(n log n)` for the sort → `O(n log²(n+1))` time, `O(n+1)` auxiliary memory.

**Kasai.** Process suffixes in text order `i = 0..n-1`; compare suffix `i` with the previous suffix in sorted order `sa[rank[i]-1]`. Keep `h` and after each step decrease it by one, because if suffixes `i` and `j` share `h` characters, suffixes `i+1` and `j+1` share at least `h-1` and `j+1` is ordered before `i+1`. `h` increases at most `2n` times in total → `O(n)`. `lcp[0] = 0`; `lcp[p]` compares `sa[p-1]` with `sa[p]`.

**Longest repeat.** Any substring occurring at two starts is a common prefix of two suffixes; the longest common prefix of any pair is achieved by a pair adjacent in sorted order, so `max(lcp)` is the longest repeat length and `text[sa[p] : sa[p]+lcp[p]]` is a witness (overlaps allowed). If `max = 0`, `repeated = ""`. Empty text → `[], [], ""`.

* **Boundary test.** `"aaaa"` → `sa=[3,2,1,0]`, `lcp=[0,1,2,3]`, `"aaa"`: detects adding a sentinel/empty suffix or wrong order for a suffix that is a prefix of another.

### aho — Aho–Corasick with aggregated counts

* **Trie.** One trie per request (dictionaries as child maps). Each dictionary position remembers its terminal state; duplicate patterns share one terminal, so they automatically receive equal counts.
* **Failure links.** BFS from the root: `fail[v]` = longest proper suffix of `v`'s string that is also a trie path. BFS order guarantees `fail` of shallower states is ready.
* **Suffix-pattern counts.** `out[s]` = nearest terminal state on the failure chain of `s` (itself included). Scanning a text, each visited state adds 1 to `out[s]`. Then counts are propagated from deeper to shallower terminals along the chain of terminals (reverse BFS order): `cnt[next_terminal(u)] += cnt[u]`. A pattern ending at position `i` of the text is a suffix of the current state's string, so it lies on that state's failure chain and is counted exactly once per occurrence — this handles overlaps and nested patterns (`he` inside `she`).
* **Independent texts.** A new count dictionary and state 0 for every text; the automaton is reused. Empty text → a row of zeros; empty dictionary → `[]` row per text; no texts → `[]`.
* **Complexity.** Construction `O(L + p)` with hash-map children (fail-link walks are amortised by pattern depth; the fixed-95-letter table version would be `O(L + 95·S + p)`); memory `O(S + p)`. Per text: transitions via failure links are amortised `O(|text|)`; propagation is only over terminal states (≤ `p`), so `O(|text| + p)` per text. This avoids walking every match and stays fast on dense inputs (my test with patterns `a, aa, …` and texts of `'a'` runs in 0.05 s).
* **Boundary test.** `["he","she","he"]` with `["sheshe","sheshe",""]` → `[[2,2,2],[2,2,2],[0,0,0]]`: detects missing suffix-pattern counts, unequal duplicates and stale counts between texts.

## Own tests

All files are in `tests/student/`. `cases.json` holds every fixture with a written justification (`why`) and an expected answer; `oracle.py` is an independent checker (memoised suffix recursion for LCS, brute-force merge orders, brute-force subsets for tree, `str.startswith` at every position for search and Aho–Corasick, sorting real suffix strings for the suffix array). Expected answers are themselves validated by the oracle.

|Command|Input or fixture path|Expected result|Actual result / log|What it checks|
|---|---|---|---|---|
|lcs|`cases.json`: `""/""`, `"abc"/""`|`0, ""`|same (`cases_actual.jsonl`)|empty inputs|
|lcs|`"tea_time"/"team"`|`4, "team"`|`4, "team"`|subsequence, not substring|
|lcs|`"ab"/"ba"`|`1`, `"a"` or `"b"`|`1, "b"`|alternative optimal witness|
|lcs|`"Ab, c!"/"ab, c?"`|`4, "b, c"`|`4, "b, c"`|case-sensitivity, punctuation|
|merge|`[]`, `[7]`|`0, []`|same|0/1 blocks|
|merge|`[1,100,1]`|`203`|`203`, valid plan|adjacency (no greedy)|
|merge|`[0,0,0,0]`|`0`, any 3 merges|`0`, valid plan|zeros, multiple optima|
|merge|`[1e9,1e9,1e9]`|`5000000000`|same|large totals|
|tree|n=0; n=1 `[5]`|`0,[]`; `5,[0]`|same|0/1 vertices|
|tree|`[-1,-5,-2]` path|`0, []`|same|all negative → empty set|
|tree|star `[10,3,3,3,3]`|`12, [1,2,3,4]`|same|centre vs leaves|
|tree|`[-5,1e9,1e9,1e9]` star|`3000000000`|same|large sum|
|tree|deep chain n=100000 (`run_tests.py` D)|valid optimum|PASS, 0.13 s|no recursion failure|
|naive/kmp/rk|`"abc"/""`, `""/""`, `""/"a"`, `"ab"/"abc"`|`[0..3]`, `[0]`, `[]`, `[]`|same|empty pattern n+1, empty text, longer pattern|
|naive/kmp|`"aaaaa"/"aaa"`, `"abababa"/"aba"`|`[0,1,2]`, `[0,2,4]`|same|overlaps|
|kmp|`"a.b A.b"/"A.b"`|`[4]`|`[4]`|case and punctuation|
|rk|`"abdj"/"ab"`, `"abdjab"/"dj"`|`[0]`, `[2]`|same|ab/dj collision verified|
|rk|`"~~ !~ !"/" !"`|`[2,5]`|`[2,5]`|negative remainder normalisation|
|naive=kmp=rk|300 random inputs (part C)|identical, = oracle|PASS|same contract on common domain|
|suffix|`""`, `"z"`|empty / `[0],[0],""`|same|empty, one char|
|suffix|`"aaaa"`, `"dcba"`|see Algorithm section|same|all equal / all distinct, no sentinel|
|suffix|`"banana"`, `"abxabcdycd"`|`ana`; `ab` or `cd`|same|overlapping and tied repeats|
|aho|`[]` patterns; `[]` texts|`[[],[]]`; `[]`|same|empty dictionary / texts|
|aho|`["he","she","he"]`|`[[2,2,2],[2,2,2],[0,0,0]]`|same|duplicates, suffix patterns, reset, empty text|
|aho|`["aaa","a","aa"]` / `"aaaa"`|`[[2,4,3]]`|same|overlaps, nested|
|all|Part B: 150 random cases per DP/suffix/aho command|oracle agreement|PASS|independent oracle|
|all|Part A batch run twice in one process|identical outputs|PASS|state reset|
|all|Part D full limits (lcs 1000×1000, merge n=200, tree n=1e5, kmp 2e5/1e5, rk 1e4/2e3 all candidates, suffix 5e4, aho 1e4 patterns/100 texts, dense aho)|correct + < 20 s|PASS, max 0.64 s|scale|

## Search comparison

Script: `tests/student/benchmark_search.py`, output: `tests/student/benchmark_output.txt`. Same inputs for all three algorithms. **Correctness first:** before timing, the three outputs are checked to be identical and equal to the oracle. **Timing scope:** only the function call (`algorithms.naive/kmp/rk(request)`), `time.perf_counter()`, milliseconds; parsing, I/O and generation excluded. One untimed warm-up call, then 5 runs; median reported. Python is interpreted: no compilation, no JIT. Random case: `random.Random(2026)`, alphabet `abcd`, pattern copied from the middle of the text (one match). Repetitive case: text `'a'*n`, pattern `'a'*(m-1)+'b'` (no match).

|Case|n|m|Seed/generator|Algorithm|Run 1|Run 2|Run 3|Run 4|Run 5|Median (ms)|Correct outputs checked|
|---|---:|---:|---|---|---:|---:|---:|---:|---:|---:|---|
|random|750|50|Random(2026), abcd|naive|0.05|0.05|0.05|0.05|0.05|0.05|yes (1 match)|
|random|750|50|Random(2026), abcd|kmp|0.06|0.05|0.05|0.05|0.07|0.05|yes|
|random|750|50|Random(2026), abcd|rk|0.08|1.01|0.08|0.08|0.07|0.08|yes|
|random|1500|150|Random(2026), abcd|naive|0.10|0.12|0.13|0.10|0.10|0.10|yes (1 match)|
|random|1500|150|Random(2026), abcd|kmp|0.11|0.11|0.10|0.10|0.10|0.10|yes|
|random|1500|150|Random(2026), abcd|rk|0.18|0.20|0.16|0.16|0.16|0.16|yes|
|random|3000|300|Random(2026), abcd|naive|0.20|0.21|0.21|0.20|0.23|0.21|yes (1 match)|
|random|3000|300|Random(2026), abcd|kmp|0.20|0.20|0.21|0.21|0.20|0.20|yes|
|random|3000|300|Random(2026), abcd|rk|0.32|0.37|0.31|0.30|0.30|0.31|yes|
|repetitive|750|50|'a'*n / 'a'*(m-1)+'b'|naive|1.24|1.19|1.28|1.29|1.27|1.27|yes (0 matches)|
|repetitive|750|50|'a'*n / 'a'*(m-1)+'b'|kmp|0.08|0.07|0.07|0.09|0.07|0.07|yes|
|repetitive|750|50|'a'*n / 'a'*(m-1)+'b'|rk|0.08|0.08|0.07|0.07|0.07|0.07|yes|
|repetitive|1500|150|'a'*n / 'a'*(m-1)+'b'|naive|7.35|7.18|7.13|7.17|7.60|7.18|yes (0 matches)|
|repetitive|1500|150|'a'*n / 'a'*(m-1)+'b'|kmp|0.17|0.15|0.18|0.18|0.16|0.17|yes|
|repetitive|1500|150|'a'*n / 'a'*(m-1)+'b'|rk|0.16|0.16|0.16|0.21|0.18|0.16|yes|
|repetitive|3000|300|'a'*n / 'a'*(m-1)+'b'|naive|30.00|29.46|29.89|28.78|29.09|29.46|yes (0 matches)|
|repetitive|3000|300|'a'*n / 'a'*(m-1)+'b'|kmp|0.31|0.33|0.29|0.29|0.32|0.31|yes|
|repetitive|3000|300|'a'*n / 'a'*(m-1)+'b'|rk|0.36|0.32|0.31|0.29|0.29|0.31|yes|

**Observations.** On random text over `abcd`, a naive comparison usually fails after one or two characters, so all three grow roughly linearly and naive/KMP are about equal; RK is slightly slower because every window pays for the rolling-hash arithmetic. On the repetitive case naive does about `m` comparisons per start: its median grows from 1.27 ms to 29.46 ms (×23 while `n·m` grows ×24), whereas KMP stays near-linear (0.07 → 0.31 ms). RK is also fast here, but only because `h('a'*300) = 0` and `h('a'*299+'b') = 1` differ, so no window becomes a candidate (`c = 0`). With text and pattern both all `'a'` every window is an equal-hash candidate and RK degrades to `O(n·m)` (my scale test `rk 10000/2000` all `'a'`: 0.64 s, the slowest of all my scale tests). The small modulus 101 is chosen to make collisions testable (`ab`/`dj` → 75); with only 101 possible values, random windows collide with probability about 1/101, so production RK uses large (or several) moduli — this observation does not generalise to such implementations. These measurements come from one machine and are evidence only, not a proof of asymptotic complexity.

## Sources and AI assistance

* Sources: the assignment specification, contracts, rubric and testing guide in `docs/`, and standard course material for LCS, interval DP, tree DP, KMP, Rabin–Karp, prefix doubling, Kasai and Aho–Corasick.
* AI assistance: Claude (Anthropic) drafted the Python implementation, the test scripts, the oracle, the benchmark and this analysis, and explained the algorithms to me. My verification: I ran `python tools/run.py --setup`, `--check`, `tests/student/run_tests.py` and `tests/student/benchmark_search.py`, read the code and checked the justified expected answers of my fixtures.
* No other external code was used.
