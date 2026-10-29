"""
SmartDialer Load Test Script
============================

Uses the actual run_scenario() simulation function with time.perf_counter()
to measure real throughput. No fabricated results.

All numbers reported are measured from your machine at the time of execution.

Usage
-----
  cd backend
  python load_test.py                        # Scenario B, 50 agents, 30 ticks
  python load_test.py --scenario A           # Scenario A (20% answer rate)
  python load_test.py --scenario B --agents 20 --ticks 50
  python load_test.py --all-scenarios        # Run A / B / C / D sequentially
  python load_test.py --help

Notes
-----
- This is an in-process simulation test (no real network / DB I/O in tight loop).
- "calls/second" = total calls initiated / elapsed wall time.
- SQLite-backed DB I/O (state machine tests, circuit breaker tests) is tested
  separately via pytest, not here.
- Do not report these numbers as representative of a real 1000-agent deployment.
"""

import argparse
import sys
import time
import json

# Ensure backend package is importable
import os
sys.path.insert(0, os.path.dirname(__file__))


def run_single(scenario: str, agents: int, borrowers: int, ticks: int,
               mode: str, provider_fail_rate: float = 0.0) -> dict:
    from app.services.simulation import run_scenario

    start = time.perf_counter()
    result = run_scenario(
        scenario=scenario,
        num_agents=agents,
        num_borrowers=borrowers,
        duration_ticks=ticks,
        mode=mode,
        provider_fail_rate=provider_fail_rate,
    )
    elapsed = time.perf_counter() - start

    summary = result["summary"]
    initiated = summary["total_initiated"]
    answered  = summary["total_answered"]
    completed = summary["total_completed"]

    calls_per_sec = initiated / elapsed if elapsed > 0 else 0.0
    ticks_per_sec = ticks / elapsed if elapsed > 0 else 0.0

    return {
        "scenario":           scenario,
        "mode":               mode,
        "num_agents":         agents,
        "num_borrowers":      borrowers,
        "duration_ticks":     ticks,
        "elapsed_sec":        round(elapsed, 4),
        "total_initiated":    initiated,
        "total_answered":     answered,
        "total_completed":    completed,
        "total_failed":       summary["total_failed"],
        "answer_rate_pct":    summary["answer_rate_pct"],
        "peak_util_pct":      summary["peak_utilization_pct"],
        "avg_util_pct":       summary["avg_utilization_pct"],
        "safety_reductions":  summary["safety_reductions"],
        "safety_rejections":  summary["safety_rejections"],
        "calls_per_sec":      round(calls_per_sec, 1),
        "ticks_per_sec":      round(ticks_per_sec, 1),
    }


def print_result(r: dict):
    sep = "-" * 60
    print(sep)
    print(f"  Scenario {r['scenario']} | Mode: {r['mode']} | "
          f"Agents: {r['num_agents']} | Ticks: {r['duration_ticks']}")
    print(sep)
    print(f"  Elapsed          : {r['elapsed_sec']} s")
    print(f"  Calls initiated  : {r['total_initiated']}")
    print(f"  Calls answered   : {r['total_answered']}  "
          f"({r['answer_rate_pct']}%)")
    print(f"  Calls completed  : {r['total_completed']}")
    print(f"  Calls failed     : {r['total_failed']}")
    print(f"  Peak utilization : {r['peak_util_pct']}%")
    print(f"  Avg utilization  : {r['avg_util_pct']}%")
    print(f"  Safety reductions: {r['safety_reductions']}")
    print(f"  Safety rejections: {r['safety_rejections']}")
    print(f"  Throughput       : {r['calls_per_sec']} calls/s | "
          f"{r['ticks_per_sec']} ticks/s")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="SmartDialer in-process load test (simulation-based)"
    )
    parser.add_argument(
        "--scenario", choices=["A", "B", "C", "D"], default="B",
        help="Scenario: A=20%%, B=50%%, C=70%%, D=dynamic (default: B)"
    )
    parser.add_argument(
        "--mode", choices=["PROGRESSIVE", "PREDICTIVE"], default="PREDICTIVE",
        help="Dialing mode (default: PREDICTIVE)"
    )
    parser.add_argument(
        "--agents", type=int, default=50,
        help="Number of simulated agents (default: 50)"
    )
    parser.add_argument(
        "--borrowers", type=int, default=1000,
        help="Number of simulated borrowers (default: 1000)"
    )
    parser.add_argument(
        "--ticks", type=int, default=30,
        help="Number of simulation ticks (default: 30)"
    )
    parser.add_argument(
        "--all-scenarios", action="store_true",
        help="Run all 4 scenarios sequentially and compare"
    )
    parser.add_argument(
        "--fail-rate", type=float, default=0.0,
        help="Provider failure rate 0.0–1.0 (default: 0.0)"
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output results as JSON"
    )

    args = parser.parse_args()

    print("\n=== SmartDialer Load Test ===")
    print(f"  Python version: {sys.version.split()[0]}")
    print(f"  Mode: {args.mode}")
    print(f"  Provider fail rate: {args.fail_rate}")
    print()

    results = []

    if args.all_scenarios:
        for sc in ["A", "B", "C", "D"]:
            r = run_single(
                sc, args.agents, args.borrowers, args.ticks,
                args.mode, args.fail_rate
            )
            results.append(r)
            if not args.json:
                print_result(r)

        if not args.json:
            # Comparative summary
            print("=" * 60)
            print("COMPARATIVE SUMMARY")
            print(f"  {'Scenario':<10} {'Mode':<12} {'Initiated':<12} "
                  f"{'AnswerRate':<12} {'AvgUtil':<10} {'calls/s'}")
            print("-" * 60)
            for r in results:
                print(f"  {r['scenario']:<10} {r['mode']:<12} "
                      f"{r['total_initiated']:<12} "
                      f"{r['answer_rate_pct']:<12} "
                      f"{r['avg_util_pct']:<10} "
                      f"{r['calls_per_sec']}")
            print()
    else:
        r = run_single(
            args.scenario, args.agents, args.borrowers, args.ticks,
            args.mode, args.fail_rate
        )
        results.append(r)
        if not args.json:
            print_result(r)

    if args.json:
        print(json.dumps(results, indent=2))

    print("  NOTE: These are in-process simulation results.")
    print("  They measure pacing + safety logic throughput, not real network I/O.")
    print("  Scale claims require a real provider integration test.\n")


if __name__ == "__main__":
    main()
