"""Command-parser inference service (port 8000).
Env: MODEL_URI (s3://bucket/prefix/), MODEL_VERSION, S3_ENDPOINT, MAX_NEW_TOKENS, FAULT_INJECT.
S3_ACCESS_KEY / S3_SECRET_KEY come from a Kubernetes Secret. Pod name = hostname."""
import json
import os
import socket
import tempfile
import threading

import jsonschema
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel

SCHEMA = json.load(open(os.path.join(os.path.dirname(__file__), "schema.json")))["json_schema"]
app = FastAPI(title="command-parser")
STATE = {"ready": False, "model": None, "tok": None, "error": None}
_lock = threading.Lock()


class ParseIn(BaseModel):
    text: str


def download_model(uri, endpoint, dest):
    import boto3
    from botocore.config import Config
    bucket, _, prefix = uri[len("s3://"):].partition("/")
    c = boto3.client("s3", endpoint_url=endpoint, region_name="us-east-1",
                     aws_access_key_id=os.environ["S3_ACCESS_KEY"],
                     aws_secret_access_key=os.environ["S3_SECRET_KEY"],
                     config=Config(s3={"addressing_style": "path"}))
    n = 0
    for page in c.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=prefix):
        for o in page.get("Contents", []):
            name = os.path.basename(o["Key"])
            if not name or name.endswith(".tar.gz"):
                continue
            c.download_file(bucket, o["Key"], os.path.join(dest, name)); n += 1
    print(f"downloaded {n} files from {uri} (version {os.environ.get('MODEL_VERSION')})", flush=True)


def load_model():
    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        torch.set_num_threads(1)
        d = tempfile.mkdtemp()
        download_model(os.environ["MODEL_URI"], os.environ["S3_ENDPOINT"], d)
        STATE["tok"] = AutoTokenizer.from_pretrained(d)
        STATE["model"] = AutoModelForCausalLM.from_pretrained(d).eval()
        STATE["ready"] = True
        print("model loaded, ready", flush=True)
    except Exception as e:  # noqa: BLE001
        STATE["error"] = str(e)
        print("model load failed:", e, flush=True)


@app.on_event("startup")
def _startup():
    threading.Thread(target=load_model, daemon=True).start()  # /healthz stays up while loading


def generate(text):
    import torch
    tok, model = STATE["tok"], STATE["model"]
    enc = tok(f"Command: {text}\nJSON:", return_tensors="pt")
    with _lock, torch.no_grad():
        out = model.generate(**enc, max_new_tokens=int(os.environ.get("MAX_NEW_TOKENS", "64")),
                             do_sample=False, pad_token_id=tok.eos_token_id, eos_token_id=tok.eos_token_id)
    return tok.decode(out[0][enc["input_ids"].shape[1]:], skip_special_tokens=True).strip().split("\n")[0].strip()


def validate(raw):
    """Return the parsed object if raw is valid per schema.json, else None."""
    try:
        obj = json.loads(raw)
        jsonschema.validate(obj, SCHEMA)
        return obj
    except Exception:  # noqa: BLE001
        return None


def headers():
    return {"X-Model-Version": os.environ.get("MODEL_VERSION", "unknown"),
            "X-Served-By": os.environ.get("POD_NAME") or socket.gethostname()}


@app.get("/healthz")
def healthz():
    return {"status": "alive"}


@app.get("/readyz")
def readyz():
    if STATE["ready"]:
        return {"status": "ready"}
    return JSONResponse({"status": "loading"}, status_code=503)


@app.post("/parse")
def parse(body: ParseIn):
    if not STATE["ready"]:
        return JSONResponse({"error": "model_not_ready"}, status_code=503, headers=headers())
    raw = generate(body.text)
    if os.environ.get("FAULT_INJECT") == "1":
        raw = "not json"
    obj = validate(raw)
    if obj is None:
        return JSONResponse({"error": "invalid_model_output"}, status_code=500, headers=headers())
    return JSONResponse(obj, headers=headers())
