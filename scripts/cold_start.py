"""Delete all pods in app, wait for Ready, report creation->Ready time; 3 runs + median."""
import json
import statistics
import subprocess
import time
from datetime import datetime


def k(*a):
    return subprocess.run(["kubectl", "-n", "app", *a], capture_output=True, text=True).stdout


def ts(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ")


times = []
for run in range(3):
    k("delete", "pods", "-l", "app=parser", "--wait=true")
    time.sleep(5)
    k("wait", "--for=condition=Ready", "pod", "-l", "app=parser", "--timeout=600s")
    for p in json.loads(k("get", "pods", "-l", "app=parser", "-o", "json"))["items"]:
        created = ts(p["metadata"]["creationTimestamp"])
        ready = [c for c in p["status"]["conditions"] if c["type"] == "Ready"][0]["lastTransitionTime"]
        d = (ts(ready) - created).total_seconds()
        print(f"run {run+1} {p['metadata']['name']}: {d:.0f}s")
        times.append(d)
    print(k("logs", "-l", "app=parser", "--tail=3"))  # log evidence of model download
print("per-pod times:", times, "median:", statistics.median(times))
