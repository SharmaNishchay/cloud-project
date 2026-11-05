"""Create buckets, upload commands_pool.jsonl, restore model files from GitHub Release tarballs (if they exist)."""
import io
import os
import sys
import tarfile
import urllib.request

sys.path.insert(0, "worker")
import s3  # noqa: E402

c = s3.client()
for b in ("datasets", "models"):
    try:
        c.create_bucket(Bucket=b)
    except Exception as e:  # noqa: BLE001
        print("bucket", b, "->", e)
c.upload_file("data/commands_pool.jsonl", "datasets", "commands_pool.jsonl")
print("uploaded commands_pool.jsonl")

repo = os.environ.get("GH_REPO", "")
for v in ("v1", "v2"):
    if not repo:
        break
    url = f"https://github.com/{repo}/releases/download/model-{v}/model-{v}.tar.gz"
    try:
        data = urllib.request.urlopen(url, timeout=120).read()
    except Exception as e:  # noqa: BLE001
        print(f"release asset for {v} not available ({e}); skipping")
        continue
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as t:
        for m in t.getmembers():
            if m.isfile():
                c.put_object(Bucket="models", Key=f"{v}/{m.name}", Body=t.extractfile(m).read())
    print("restored model", v)
