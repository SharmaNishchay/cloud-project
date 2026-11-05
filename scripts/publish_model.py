"""Upload out/models/<version>/ to s3://models/<version>/ (run through scripts/with_s3.sh)."""
import os
import sys

sys.path.insert(0, "worker")
import s3  # noqa: E402

v = sys.argv[1]
d = f"out/models/{v}"
c = s3.client()
for n in sorted(os.listdir(d)):
    p = os.path.join(d, n)
    if os.path.isfile(p):
        c.upload_file(p, "models", f"{v}/{n}")
        print("uploaded", f"{v}/{n}")
