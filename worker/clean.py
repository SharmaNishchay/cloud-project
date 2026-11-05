"""Clean teacher outputs -> datasets/v1/train.jsonl + train.sha256.

Order of checks per record: (a) invalid JSON, (b) keys not exactly the four, (c) bad intent,
(d) slot not null/not text found in the command. Only records that pass are de-duplicated by
command text (smallest id kept). So input = a + b + c + d + duplicates + kept.
Usage: python worker/clean.py            (S3, uses S3_* env)
       python worker/clean.py --local-dir shards/ --out out/   (offline / tests)
"""
import argparse
import glob
import hashlib
import json
import os

INTENTS = {"alarm_set", "alarm_query", "calendar_set", "calendar_query", "calendar_remove",
           "weather_query", "datetime_query", "recommendation_events"}
KEYS = {"intent", "date", "time", "place"}


def classify(rec):
    """Return None if the record is good, else 'a'|'b'|'c'|'d'."""
    try:
        obj = json.loads(rec["teacher_raw"])
    except (ValueError, TypeError):
        return "a"
    if not isinstance(obj, dict) or set(obj.keys()) != KEYS:
        return "b"
    if not isinstance(obj["intent"], str) or obj["intent"] not in INTENTS:
        return "c"
    for k in ("date", "time", "place"):
        v = obj[k]
        if v is not None and not (isinstance(v, str) and v in rec["text"]):
            return "d"
    return None


def clean(records):
    counts = {"input": len(records), "a": 0, "b": 0, "c": 0, "d": 0, "duplicates": 0, "kept": 0}
    valid = []
    for rec in sorted(records, key=lambda r: r["id"]):
        bad = classify(rec)
        if bad:
            counts[bad] += 1
        else:
            valid.append(rec)
    out, seen = [], set()
    for rec in valid:  # id order -> smallest id wins
        if rec["text"] in seen:
            counts["duplicates"] += 1
            continue
        seen.add(rec["text"])
        out.append(rec)
    counts["kept"] = len(out)
    assert counts["input"] == sum(counts[k] for k in ("a", "b", "c", "d", "duplicates", "kept"))
    return out, counts


def serialise(records):
    return "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--local-dir")
    ap.add_argument("--out", default="out")
    a = ap.parse_args()
    records = []
    if a.local_dir:
        for p in sorted(glob.glob(os.path.join(a.local_dir, "shard-*.jsonl"))):
            records += [json.loads(x) for x in open(p, encoding="utf-8") if x.strip()]
    else:
        import s3
        c = s3.client()
        keys = sorted(o["Key"] for o in c.list_objects_v2(Bucket="datasets", Prefix="teacher/")
                      .get("Contents", []) if o["Key"].endswith(".jsonl"))
        for k in keys:
            records += [json.loads(x) for x in s3.get_text(c, "datasets", k).splitlines() if x.strip()]
    ids = [r["id"] for r in records]
    print("shard check: records", len(ids), "unique ids", len(set(ids)))
    out, counts = clean(records)
    body = serialise(out)
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    line = f"{digest}  train.jsonl\n"
    if a.local_dir:
        os.makedirs(a.out, exist_ok=True)
        open(os.path.join(a.out, "train.jsonl"), "w", encoding="utf-8").write(body)
        open(os.path.join(a.out, "train.sha256"), "w").write(line)
    else:
        s3.put_text(c, "datasets", "v1/train.jsonl", body)
        s3.put_text(c, "datasets", "v1/train.sha256", line)
    print(json.dumps(counts, indent=2))
    print("sha256", digest)


if __name__ == "__main__":
    main()
