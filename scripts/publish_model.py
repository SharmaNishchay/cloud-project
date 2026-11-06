"""Upload out/models/<version>/ to s3://models/<version>/ (run through scripts/with_s3.sh). Retries each file."""
import os
import sys
import time

from boto3.s3.transfer import TransferConfig

sys.path.insert(0, "worker")
import s3  # noqa: E402

v = sys.argv[1]
d = f"out/models/{v}"
c = s3.client()
cfg = TransferConfig(max_concurrency=1, multipart_chunksize=16 * 1024 * 1024)
for n in sorted(os.listdir(d)):
    p = os.path.join(d, n)
    if not os.path.isfile(p) or n.endswith(".tar.gz"):  # the tarball goes to the GitHub Release, not the bucket
        continue
    for attempt in range(10):
        try:
            c.upload_file(p, "models", f"{v}/{n}", Config=cfg)
            print("uploaded", f"{v}/{n}", flush=True)
            break
        except Exception as e:  # noqa: BLE001
            print(f"retry {n} ({attempt}): {type(e).__name__}", flush=True)
            time.sleep(4)
    else:
        raise SystemExit(f"failed to upload {n}")
