import sys
sys.path.insert(0, "worker")
sys.path.insert(0, "scripts")
import os
for k in ("S3_ENDPOINT", "S3_ACCESS_KEY", "S3_SECRET_KEY"):
    os.environ.setdefault(k, "x")
from worker import shard_lines, build_prompt  # noqa: E402


def test_shards_partition_the_pool():
    lines = [f'{{"id": "C{i:04d}", "text": "t{i}"}}' for i in range(10)]
    a, b = shard_lines(lines, 0, 2), shard_lines(lines, 1, 2)
    ids = [r["id"] for r in a + b]
    assert sorted(ids) == sorted({r["id"] for r in a + b}) and len(ids) == 10
    assert a[0]["id"] == "C0000" and b[0]["id"] == "C0001"


def test_prompt_keeps_json_braces():
    p = build_prompt('example {"a": 1}\nCommand: {command}', "hello")
    assert p.endswith("Command: hello") and '{"a": 1}' in p
