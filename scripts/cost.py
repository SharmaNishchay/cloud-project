"""Cost per 1000 requests from rate_card.json and a Locust stats csv, every step printed.
usage: python scripts/cost.py results/loadtest_stats.csv --replicas 2 --cpu-limit 1 --mem-limit-gib 1 [--target 99]"""
import argparse
import csv
import json

ap = argparse.ArgumentParser()
ap.add_argument("stats")
ap.add_argument("--replicas", type=float, required=True)
ap.add_argument("--cpu-limit", type=float, default=1)
ap.add_argument("--mem-limit-gib", type=float, default=1)
ap.add_argument("--target", type=float, default=99.0, help="SLO: percent of requests that succeed")
a = ap.parse_args()
rc = json.load(open("data/rate_card.json"))
row = [r for r in csv.DictReader(open(a.stats)) if r["Name"] == "Aggregated"][0]
reqs, fails, rps = int(row["Request Count"]), int(row["Failure Count"]), float(row["Requests/s"])
per_replica = a.cpu_limit * rc["vcpu_hour"] + a.mem_limit_gib * rc["gib_memory_hour"]
hourly = per_replica * a.replicas
per_hour = rps * 3600
print(f"cost per replica-hour = {a.cpu_limit}*{rc['vcpu_hour']} + {a.mem_limit_gib}*{rc['gib_memory_hour']} = {per_replica:.4f} {rc['currency']}")
print(f"hourly cost of {a.replicas:g} replicas = {hourly:.4f}")
print(f"requests/hour = {rps:.3f} rps * 3600 = {per_hour:.1f}")
print(f"cost per 1000 requests = {hourly:.4f} / {per_hour:.1f} * 1000 = {hourly/per_hour*1000:.4f} {rc['currency']}")
budget = (1 - a.target / 100) * reqs
print(f"SLO {a.target}% success over this run: requests={reqs}, error budget={budget:.1f} requests, "
      f"failures={fails}, budget used={fails/budget*100 if budget else float('inf'):.1f}%")
