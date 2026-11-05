"""Tiny S3 helper. Credentials come from env vars (Kubernetes Secret), never from the repo."""
import os

import boto3
from botocore.config import Config


def client():
    return boto3.client(
        "s3",
        endpoint_url=os.environ["S3_ENDPOINT"],
        aws_access_key_id=os.environ["S3_ACCESS_KEY"],
        aws_secret_access_key=os.environ["S3_SECRET_KEY"],
        region_name="us-east-1",
        config=Config(s3={"addressing_style": "path"}, retries={"max_attempts": 5}),
    )


def get_text(c, bucket, key):
    return c.get_object(Bucket=bucket, Key=key)["Body"].read().decode("utf-8")


def put_text(c, bucket, key, text):
    c.put_object(Bucket=bucket, Key=key, Body=text.encode("utf-8"))


def exists(c, bucket, key):
    try:
        c.head_object(Bucket=bucket, Key=key)
        return True
    except Exception:
        return False
