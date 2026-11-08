"""My own tests for Assignment 4. Run from the repository root:

    python tests/student/run_tests.py

A. Hand-made boundary cases (cases.json), each with a justification. The whole
   batch is sent to Python/source/main.py TWICE in one process (state reset).
   Both the expected answer and the actual answer go through the oracle.
B. Random differential tests (seed 4) against independent brute-force oracles.
C. naive / kmp / rk must give identical positions on the same inputs.
D. Full-limit inputs per command, run as one process each and timed (limit 20 s).
Actual outputs of part A are saved in tests/student/actual_outputs.jsonl.
"""

import json
import pathlib
import random
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
HERE = ROOT / "tests" / "student"
sys.path.insert(0, str(HERE))
from oracle import validate, search_oracle   # noqa: E402

MAIN = [sys.executable, str(ROOT / "Python" / "source" / "main.py")]
fails = 0

# fields whose value is unique for every correct program
UNIQUE = {"lcs": ["length"], "merge": ["cost"], "tree": ["weight"], "naive": ["positions"],
          "kmp": ["positions"], "rk": ["positions"], "suffix": ["sa", "lcp"], "aho": ["counts"]}


def report(ok, label, why=""):
    global fails
    fails += 0 if ok else 1
    print(("PASS " if ok else "FAIL ") + label + ("" if ok else f"  ({why})"))


def run(requests):
    data = "".join(json.dumps(r, separators=(",", ":")) + "\n" for r in requests)
    t0 = time.perf_counter()
    res = subprocess.run(MAIN, input=data, capture_output=True, text=True, timeout=120)
    secs = time.perf_counter() - t0
    if res.returncode != 0:
        raise SystemExit(res.stderr)
    return [json.loads(x) for x in res.stdout.splitlines()], secs


def part_a():
    print("== A. boundary cases (batch sent twice in one process) ==")
    cases = json.loads((HERE / "cases.json").read_text(encoding="utf-8"))
    answers, _ = run([c["input"] for c in cases] * 2)
    with open(HERE / "actual_outputs.jsonl", "w", encoding="utf-8") as f:
        for c, a in zip(cases, answers):
            f.write(json.dumps({"name": c["name"], "actual": a}, separators=(",", ":")) + "\n")
    for k, (c, a) in enumerate(zip(cases * 2, answers)):
        ok_e, why_e = validate(c["input"], c["expected"])
        ok_a, why_a = validate(c["input"], a)
        same = all(a.get(f) == c["expected"].get(f) for f in UNIQUE[c["input"]["task"]])
        report(ok_e and ok_a and same, ("run1 " if k < len(cases) else "run2 ") + c["name"],
               f"expected:{why_e} actual:{why_a} unique-match:{same}")
    report(answers[:len(cases)] == answers[len(cases):], "state reset: both runs identical")


def rand_str(rnd, n, alpha):
    return "".join(rnd.choice(alpha) for _ in range(n))


def part_b():
    print("== B. random differential tests vs brute-force oracles (seed 4) ==")
    rnd = random.Random(4)
    reqs = []
    for _ in range(150):
        reqs.append({"task": "lcs", "a": rand_str(rnd, rnd.randint(0, 9), "abc"),
                     "b": rand_str(rnd, rnd.randint(0, 9), "abc")})
        reqs.append({"task": "merge", "sizes": [rnd.randint(0, 9) for _ in range(rnd.randint(0, 7))]})
        n = rnd.randint(0, 11)
        edges = [[rnd.randrange(v), v] for v in range(1, n)]
        reqs.append({"task": "tree", "n": n, "weights": [rnd.randint(-5, 9) for _ in range(n)],
                     "edges": edges})
        reqs.append({"task": "suffix", "text": rand_str(rnd, rnd.randint(0, 25), "ab")})
        pats = [rand_str(rnd, rnd.randint(1, 3), "ab") for _ in range(rnd.randint(0, 5))]
        reqs.append({"task": "aho", "patterns": pats,
                     "texts": [rand_str(rnd, rnd.randint(0, 20), "ab") for _ in range(rnd.randint(0, 3))]})
    answers, _ = run(reqs)
    bad = {}
    total = {}
    for r, a in zip(reqs, answers):
        ok, why = validate(r, a)
        total[r["task"]] = total.get(r["task"], 0) + 1
        if not ok:
            bad.setdefault(r["task"], why)
    for task in total:
        report(task not in bad, f"{task}: {total[task]} random cases agree with oracle", bad.get(task, ""))


def part_c():
    print("== C. naive / kmp / rk identical on the same inputs (seed 7) ==")
    rnd = random.Random(7)
    reqs = []
    for _ in range(300):
        alpha = rnd.choice(["ab", "abc", " !~a", "abdj"])
        text = rand_str(rnd, rnd.randint(0, 40), alpha)
        pat = rand_str(rnd, rnd.randint(0, 5), alpha)
        for t in ("naive", "kmp", "rk"):
            reqs.append({"task": t, "text": text, "pattern": pat})
    answers, _ = run(reqs)
    ok = True
    for i in range(0, len(reqs), 3):
        want = search_oracle(reqs[i]["text"], reqs[i]["pattern"])
        if not (answers[i]["positions"] == answers[i + 1]["positions"]
                == answers[i + 2]["positions"] == want):
            ok = False
    report(ok, "300 inputs: naive == kmp == rk == oracle")


def part_d():
    print("== D. full published limits, one process per command (seed 2026) ==")
    rnd = random.Random(2026)
    big = []
    big.append(("lcs 1000x1000", [{"task": "lcs", "a": rand_str(rnd, 1000, "ACGT"),
                                   "b": rand_str(rnd, 1000, "ACGT")}]))
    big.append(("merge n=200, sizes up to 1e9", [{"task": "merge",
               "sizes": [rnd.randint(0, 10**9) for _ in range(200)]}]))
    chain = [[i, i + 1] for i in range(99999)]
    big.append(("tree deep chain n=1e5", [{"task": "tree", "n": 100000,
               "weights": [rnd.randint(-10**9, 10**9) for _ in range(100000)], "edges": chain}]))
    big.append(("tree random n=1e5", [{"task": "tree", "n": 100000,
               "weights": [rnd.randint(-10**9, 10**9) for _ in range(100000)],
               "edges": [[rnd.randrange(v), v] for v in range(1, 100000)]}]))
    big.append(("naive 3000/1500 all 'a'", [{"task": "naive", "text": "a" * 3000, "pattern": "a" * 1500}]))
    big.append(("kmp 200000/100000 all 'a'", [{"task": "kmp", "text": "a" * 200000, "pattern": "a" * 100000}]))
    big.append(("kmp 200000 random, empty pattern", [{"task": "kmp", "text": rand_str(rnd, 200000, "ab"), "pattern": ""}]))
    big.append(("rk 10000/2000 all 'a' (every window a candidate)",
               [{"task": "rk", "text": "a" * 10000, "pattern": "a" * 2000}]))
    big.append(("suffix 50000 random", [{"task": "suffix", "text": rand_str(rnd, 50000, "ab")}]))
    big.append(("suffix 50000 all 'a'", [{"task": "suffix", "text": "a" * 50000}]))
    pats = [rand_str(rnd, 10, "ab") for _ in range(10000)]
    big.append(("aho 10000 patterns, 100 texts, total 200000", [{"task": "aho", "patterns": pats,
               "texts": [rand_str(rnd, 2000, "ab") for _ in range(100)]}]))
    big.append(("aho dense: 'a'*k patterns, 'a' texts", [{"task": "aho",
               "patterns": ["a" * k for k in range(1, 447)],
               "texts": ["a" * 2000 for _ in range(100)]}]))
    for label, reqs in big:
        (ans,), secs = run(reqs)
        r = reqs[0]
        if r["task"] in ("naive", "kmp", "rk"):
            ok = ans["positions"] == search_oracle(r["text"], r["pattern"])
            why = "positions"
        elif r["task"] == "aho":
            ok = ans["counts"][0] == [len(search_oracle(r["texts"][0], p)) for p in r["patterns"]] \
                and len(ans["counts"]) == 100
            why = "counts"
        elif r["task"] == "suffix" and r["text"] == "a" * 50000:
            ok = ans["sa"] == list(range(49999, -1, -1)) and ans["repeated"] == "a" * 49999
            why = "all-equal sa"
        else:
            ok, why = validate(r, ans)
        report(ok and secs < 20, f"{label}: {secs:.2f} s", why)


if __name__ == "__main__":
    part_a()
    part_b()
    part_c()
    part_d()
    print("\nALL TESTS PASSED" if fails == 0 else f"\n{fails} FAILURE(S)")
    sys.exit(1 if fails else 0)
