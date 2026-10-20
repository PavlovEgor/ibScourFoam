#!/usr/bin/env python3
"""Analyze STEP_TIME entries from an ibScourFoam log to find where time is spent.

Usage:
    profileLog.py <logFile> [--by-time] [--top N]
"""

import argparse
import re
import sys
from collections import defaultdict

STEP_TIME_RE = re.compile(r"^STEP_TIME\s+(\S+)\s+(\S+)\s+([-\d.eE+]+)\s*$")


def parseLines(lines):
    """Yield (timeName, step, duration) tuples found in an iterable of lines."""
    for line in lines:
        m = STEP_TIME_RE.match(line)
        if m:
            timeName, step, duration = m.groups()
            yield timeName, step, float(duration)


def summarize(records):
    totals = defaultdict(float)
    counts = defaultdict(int)
    grandTotal = 0.0
    for _, step, duration in records:
        totals[step] += duration
        counts[step] += 1
        grandTotal += duration
    return totals, counts, grandTotal


def printSummary(totals, counts, grandTotal, top):
    rows = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)
    if top:
        rows = rows[:top]

    nameWidth = max((len(name) for name, _ in rows), default=4)
    nameWidth = max(nameWidth, len("Step"))

    header = f"{'Step':<{nameWidth}}  {'Total (s)':>12}  {'Calls':>8}  {'Avg (s)':>10}  {'% total':>8}"
    print(header)
    print("-" * len(header))
    for name, total in rows:
        n = counts[name]
        avg = total / n if n else 0.0
        pct = 100.0 * total / grandTotal if grandTotal else 0.0
        print(f"{name:<{nameWidth}}  {total:12.3f}  {n:8d}  {avg:10.4f}  {pct:7.2f}%")
    print("-" * len(header))
    print(f"{'TOTAL':<{nameWidth}}  {grandTotal:12.3f}")


def printByTime(records, top):
    perTime = defaultdict(dict)
    order = []
    for timeName, step, duration in records:
        if timeName not in perTime:
            order.append(timeName)
        perTime[timeName][step] = perTime[timeName].get(step, 0.0) + duration

    allSteps = sorted({s for steps in perTime.values() for s in steps})
    header = f"{'Time':>12}" + "".join(f"  {s:>14}" for s in allSteps) + f"  {'Total':>10}"
    print(header)
    print("-" * len(header))

    rows = order[-top:] if top else order
    for t in rows:
        steps = perTime[t]
        total = sum(steps.values())
        line = f"{t:>12}" + "".join(f"  {steps.get(s, 0.0):14.4f}" for s in allSteps)
        line += f"  {total:10.4f}"
        print(line)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("logFile", help="Path to the solver log file (or '-' for stdin)")
    parser.add_argument(
        "--by-time", action="store_true",
        help="Print a per-timestep breakdown instead of the aggregated summary"
    )
    parser.add_argument(
        "--top", type=int, default=0,
        help="Limit output: top-N steps for summary, last-N timesteps for --by-time"
    )
    args = parser.parse_args()

    if args.logFile == "-":
        records = list(parseLines(sys.stdin))
    else:
        with open(args.logFile, "r", errors="replace") as f:
            records = list(parseLines(f))

    if not records:
        print("No STEP_TIME entries found in the log.", file=sys.stderr)
        sys.exit(1)

    if args.by_time:
        printByTime(records, args.top)
    else:
        totals, counts, grandTotal = summarize(records)
        printSummary(totals, counts, grandTotal, args.top)


if __name__ == "__main__":
    main()
