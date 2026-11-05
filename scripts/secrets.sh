#!/usr/bin/env bash
# Create (once) random S3 credentials and distribute them as Secrets. Nothing is written to the repo.
set -euo pipefail
AK=$(kubectl -n data get secret s3-creds -o jsonpath='{.data.S3_ACCESS_KEY}' 2>/dev/null | base64 -d || true)
if [ -z "$AK" ]; then
  AK=$(openssl rand -hex 8); SK=$(openssl rand -hex 16)
else
  SK=$(kubectl -n data get secret s3-creds -o jsonpath='{.data.S3_SECRET_KEY}' | base64 -d)
fi
for ns in data pipeline app; do
  kubectl -n "$ns" create secret generic s3-creds --from-literal=S3_ACCESS_KEY="$AK" --from-literal=S3_SECRET_KEY="$SK" \
    --dry-run=client -o yaml | kubectl apply -f -
done
CFG="{\"identities\":[{\"name\":\"admin\",\"credentials\":[{\"accessKey\":\"$AK\",\"secretKey\":\"$SK\"}],\"actions\":[\"Admin\",\"Read\",\"Write\",\"List\",\"Tagging\"]}]}"
kubectl -n data create secret generic seaweed-s3-config --from-literal=s3.json="$CFG" --dry-run=client -o yaml | kubectl apply -f -
