"""Search comparison: naive vs KMP vs exact Rabin-Karp on the SAME inputs.

Run from the repository root:
    python tests/student/benchmark_search.py

Scope (identical for all three): only the call algorithms.<name>(request) is
timed with time.perf_counter(); JSON parsing, I/O and input generation are
excluded. One untimed warm-up call per algorithm/size/case, then 5 timed runs;
median reported in milliseconds. Before timing, the three outputs are checked
to be identical and equal to an independent oracle (str.startswith at every
position). Python is interpreted: there is no compilation or JIT warm-up.

Cases (common domain n, m <= 3000):
  random     - text and pattern uniform over 'abcd' (random.Random(2026));
               the pattern is copied from the text middle so matches exist.
  repetitive - text 'a'*n, pattern 'a'*(m-1)+'b' (never matches; worst case
               for naive and many RK hash candidates).
"""

import platform
import random
import statistics
import sys
import pathlib
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "Python" / "source"))
sys.path.insert(0, str(ROOT / "tests" / "student"))
import algorithms                     # noqa: E402
from oracle import search_oracle      # noqa: E402

SIZES = [(750, 50), (1500, 150), (3000, 300)]
RUNS = 5
ALGS = [("naive", algorithms.naive), ("kmp", algorithms.kmp), ("rk", algorithms.rk)]


def make(case, n, m, rnd):
    if case == "random":
        text = "".join(rnd.choice("abcd") for _ in range(n))
        start = (n - m) // 2
        return text, text[start:start + m]
    return "a" * n, "a" * (m - 1) + "b"


def main():
    rnd = random.Random(2026)
    print(f"Python {platform.python_version()} ({platform.python_implementation()}) on "
          f"{platform.platform()}; timer=time.perf_counter; warm-up=1; runs={RUNS}\n")
    print("|Case|n|m|Seed/generator|Algorithm|Run 1|Run 2|Run 3|Run 4|Run 5|Median (ms)|Correct outputs checked|")
    print("|---|---:|---:|---|---|---:|---:|---:|---:|---:|---:|---|")
    for case in ("random", "repetitive"):
        for n, m in SIZES:
            text, pattern = make(case, n, m, rnd)
            req = {"text": text, "pattern": pattern}
            want = search_oracle(text, pattern)
            outs = [fn(req)["positions"] for _, fn in ALGS]          # warm-up + check
            assert outs[0] == outs[1] == outs[2] == want
            gen = "Random(2026), alphabet abcd" if case == "random" else "'a'*n / 'a'*(m-1)+'b'"
            for name, fn in ALGS:
                times = []
                for _ in range(RUNS):
                    t0 = time.perf_counter()
                    fn(req)
                    times.append((time.perf_counter() - t0) * 1000)
                med = statistics.median(times)
                print(f"|{case}|{n}|{m}|{gen}|{name}|" + "|".join(f"{t:.2f}" for t in times)
                      + f"|{med:.2f}|yes, {len(want)} matches, all 3 equal + oracle|")


if __name__ == "__main__":
    main()
