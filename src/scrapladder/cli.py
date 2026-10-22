"""Command line.

    scrapladder fetch URL [-o page.html] [--memory scrapladder.json] [--must-contain TEXT]
    scrapladder explain URL          # try every rung, one table
    scrapladder methods              # which rungs are available here
    scrapladder stats [--memory F]   # what the memory learned
"""

from __future__ import annotations

import argparse
import collections
import sys

from . import Ladder, Memory
from .methods import ALL


def _ladder(a) -> Ladder:
    return Ladder(memory=a.memory, min_interval=a.interval, respect_robots=not a.ignore_robots,
                  must_contain=getattr(a, "must_contain", None))


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="scrapladder")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("fetch", "explain"):
        s = sub.add_parser(name)
        s.add_argument("url")
        s.add_argument("--memory", default=None, help="JSON file with what was learned per domain")
        s.add_argument("--interval", type=float, default=4.0, help="seconds between requests to a domain")
        s.add_argument("--ignore-robots", action="store_true")
        if name == "fetch":
            s.add_argument("-o", "--output")
            s.add_argument("--must-contain")
    sub.add_parser("methods")
    s = sub.add_parser("stats")
    s.add_argument("--memory", default="scrapladder.json")
    a = p.parse_args(argv)

    if a.cmd == "methods":
        for cls in ALL:
            m = cls()
            try:
                m.check()
                state = "available"
            except Exception as e:
                state = f"missing: {e}"
            print(f"{m.name:<12} {'paid' if m.paid else 'free':<5} {state}")
        return 0

    if a.cmd == "stats":
        mem = Memory(a.memory)
        first = collections.Counter(s.winners[0] for s in mem.domains.values() if s.winners)
        print(f"{len(mem.domains)} domains")
        for name, n in first.most_common():
            print(f"  {name:<12} first on {n:>5} ({n / max(1, sum(first.values())):.0%})")
        return 0

    with _ladder(a) as ladder:
        if a.cmd == "explain":
            print(f"{'method':<12} {'outcome':<15} {'status':>6} {'size':>9} {'sec':>6}  reason")
            for at in ladder.explain(a.url):
                print(f"{at.method:<12} {at.outcome:<15} {str(at.status or '-'):>6} {at.size:>9} {at.seconds:>6.1f}  {at.reason}")
            return 0
        r = ladder.fetch(a.url)
        print(r.summary(), file=sys.stderr)
        if r.ok:
            if a.output:
                open(a.output, "w", encoding="utf-8").write(r.html)
            else:
                sys.stdout.write(r.html)
            return 0
        if r.retry_after:
            print(f"retry after {r.retry_after:.0f}s", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
