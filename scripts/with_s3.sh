#!/usr/bin/env bash
# Run a command with a port-forward to SeaweedFS and S3_* env set from the cluster Secret.
set -euo pipefail
kubectl -n data port-forward svc/seaweedfs 18333:8333 >/dev/null 2>&1 &
PF=$!; trap 'kill $PF 2>/dev/null' EXIT
sleep 3
export S3_ENDPOINT=http://localhost:18333
export S3_ACCESS_KEY=$(kubectl -n data get secret s3-creds -o jsonpath='{.data.S3_ACCESS_KEY}' | base64 -d)
export S3_SECRET_KEY=$(kubectl -n data get secret s3-creds -o jsonpath='{.data.S3_SECRET_KEY}' | base64 -d)
"$@"
