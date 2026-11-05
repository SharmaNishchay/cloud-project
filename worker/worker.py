"""Teacher-labelling worker.

Env: SHARD_INDEX (from 0), SHARD_COUNT, OLLAMA_URL, S3_ENDPOINT/S3_ACCESS_KEY/S3_SECRET_KEY.
Takes the pool lines whose 0-based line number % SHARD_COUNT == SHARD_INDEX, asks the teacher
(phi3.5, temperature 0, seed 42) and writes datasets/teacher/shard-<i>.jsonl.
The object is checkpointed every CHECKPOINT records and the worker resumes from it after a crash.
"""
import json
import os
import time

import requests

import s3

BUCKET = "datasets"
MODEL = os.environ.get("TEACHER_MODEL", "phi3.5")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://host.k3d.internal:11434")
PROMPT_PATH = os.environ.get("PROMPT_PATH", "prompts/teacher_prompt.txt")
CHECKPOINT = int(os.environ.get("CHECKPOINT", "20"))


def shard_lines(lines, index, count):
    """Records whose 0-based line number leaves remainder `index` modulo `count`."""
    return [json.loads(ln) for i, ln in enumerate(lines) if i % count == index and ln.strip()]


def build_prompt(template, command):
    return template.replace("{command}", command)  # replace, not format: the prompt contains JSON braces


def ask_teacher(prompt):
    body = {"model": MODEL, "prompt": prompt, "stream": False,
            "options": {"temperature": 0, "seed": 42, "num_predict": 120, "stop": ["\n\n"]}}
    for attempt in range(6):
        try:
            r = requests.post(f"{OLLAMA_URL}/api/generate", json=body, timeout=900)
            r.raise_for_status()
            return r.json()["response"]  # stored exactly as generated
        except Exception as e:  # noqa: BLE001
            print(f"teacher error (attempt {attempt}): {e}", flush=True)
            time.sleep(5 * (attempt + 1))
    raise RuntimeError("teacher unavailable")


def main():
    idx, cnt = int(os.environ["SHARD_INDEX"]), int(os.environ["SHARD_COUNT"])
    c = s3.client()
    template = open(PROMPT_PATH, encoding="utf-8").read()
    pool = s3.get_text(c, BUCKET, "commands_pool.jsonl").splitlines()
    mine = shard_lines(pool, idx, cnt)
    key = f"teacher/shard-{idx}.jsonl"
    done = []
    if s3.exists(c, BUCKET, key):
        done = [json.loads(x) for x in s3.get_text(c, BUCKET, key).splitlines() if x.strip()]
    seen = {d["id"] for d in done}
    print(f"shard {idx}/{cnt}: {len(mine)} commands, {len(seen)} already done", flush=True)
    t0 = time.time()
    for n, rec in enumerate(mine):
        if rec["id"] in seen:
            continue
        raw = ask_teacher(build_prompt(template, rec["text"]))
        done.append({"id": rec["id"], "text": rec["text"], "teacher_raw": raw})
        if len(done) % CHECKPOINT == 0:
            s3.put_text(c, BUCKET, key, "".join(json.dumps(d, ensure_ascii=False) + "\n" for d in done))
            print(f"  {len(done)}/{len(mine)}  {time.time()-t0:.0f}s", flush=True)
    s3.put_text(c, BUCKET, key, "".join(json.dumps(d, ensure_ascii=False) + "\n" for d in done))
    print(f"shard {idx} finished: {len(done)} records", flush=True)


if __name__ == "__main__":
    main()
