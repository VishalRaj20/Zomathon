"""
benchmark_latency.py
--------------------
Measures inference latency of the recommendation engine across different scenarios.
Verifies the < 200-300ms requirement from the CSAO problem statement.

Usage:
    python src/evaluation/benchmark_latency.py
"""

import sys
import time
import statistics
from pathlib import Path
from datetime import datetime
import json

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.inference.recommender import recommend


def benchmark_scenario(name, user_id, restaurant_id, cart_items, timestamp, top_k=8, n_runs=20):
    """Run a scenario multiple times and collect latency stats."""
    latencies = []

    # Warmup run (load model, data into cache)
    recommend(user_id, restaurant_id, cart_items, timestamp, top_k=top_k)

    for _ in range(n_runs):
        start = time.perf_counter()
        recs = recommend(user_id, restaurant_id, cart_items, timestamp, top_k=top_k)
        elapsed_ms = (time.perf_counter() - start) * 1000
        latencies.append(elapsed_ms)

    return {
        "scenario": name,
        "n_runs": n_runs,
        "p50_ms": round(statistics.median(latencies), 1),
        "p95_ms": round(sorted(latencies)[int(0.95 * len(latencies))], 1),
        "p99_ms": round(sorted(latencies)[int(0.99 * len(latencies))], 1),
        "mean_ms": round(statistics.mean(latencies), 1),
        "min_ms": round(min(latencies), 1),
        "max_ms": round(max(latencies), 1),
        "meets_sla": sorted(latencies)[int(0.95 * len(latencies))] < 300,
        "num_recommendations": len(recs),
    }


def main():
    ts_dinner = datetime(2025, 11, 15, 20, 0)
    ts_lunch = datetime(2025, 11, 15, 12, 30)
    ts_breakfast = datetime(2025, 11, 15, 8, 0)

    scenarios = [
        ("Empty Cart (global recs)", 27, 0, [], ts_dinner),
        ("Single Item Cart", 27, 0, [162], ts_dinner),
        ("Small Cart (3 items)", 27, 0, [162, 161, 160], ts_dinner),
        ("Full Cart (5+ items)", 27, 0, [162, 161, 160, 152, 153], ts_dinner),
        ("Lunch Time", 27, 0, [162], ts_lunch),
        ("Breakfast Time", 27, 0, [162], ts_breakfast),
        ("Restaurant-specific", 27, 32, [], ts_dinner),
        ("Cold Start User", 9999, 0, [], ts_dinner),
    ]

    print("=" * 80)
    print("  CSAO Recommendation Engine — Latency Benchmark")
    print("  SLA Target: < 300ms (p95)")
    print("=" * 80)

    results = []
    for name, uid, rid, cart, ts in scenarios:
        print(f"\n  Running: {name}...")
        result = benchmark_scenario(name, uid, rid, cart, ts)
        results.append(result)

        status = "✓ PASS" if result["meets_sla"] else "✗ FAIL"
        print(f"    {status}  p50={result['p50_ms']}ms  p95={result['p95_ms']}ms  p99={result['p99_ms']}ms  mean={result['mean_ms']}ms")

    # Summary
    print("\n" + "=" * 80)
    print("  SUMMARY")
    print("=" * 80)
    all_pass = all(r["meets_sla"] for r in results)
    avg_p95 = statistics.mean(r["p95_ms"] for r in results)
    print(f"  Overall SLA compliance: {'ALL PASS ✓' if all_pass else 'SOME FAIL ✗'}")
    print(f"  Average p95 latency:    {avg_p95:.1f}ms")
    print(f"  Scenarios tested:       {len(results)}")

    # Save report
    report = {
        "timestamp": datetime.now().isoformat(),
        "sla_target_ms": 300,
        "all_pass": all_pass,
        "avg_p95_ms": round(avg_p95, 1),
        "scenarios": results,
    }
    report_path = Path(__file__).resolve().parents[2] / "models" / "latency_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\n  Report saved → {report_path}")


if __name__ == "__main__":
    main()
