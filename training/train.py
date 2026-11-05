"""Sequence-level distillation: fine-tune pythia-70m on the teacher's JSON replies (CPU only).
Reads ONLY the config file (plus --subset N for a smoke test).
Example: "Command: <text>\nJSON: <teacher JSON>"; loss is computed on the JSON part only."""
import argparse
import csv
import gzip
import hashlib
import json
import os
import random
import sys
import tarfile

import numpy as np
import torch
import yaml
from torch.utils.data import DataLoader
from transformers import AutoModelForCausalLM, AutoTokenizer, get_linear_schedule_with_warmup

sys.path.insert(0, os.path.dirname(__file__))
from infer import build_prompt  # noqa: E402


def seed_all(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.use_deterministic_algorithms(True, warn_only=True)


def encode(tok, rec, max_len):
    p = tok(build_prompt(rec["text"]))["input_ids"]
    t = tok(" " + rec["teacher_raw"].strip())["input_ids"] + [tok.eos_token_id]
    ids = (p + t)[:max_len]
    labels = ([-100] * len(p) + t)[:max_len]
    return ids, labels


def collate(batch, pad):
    n = max(len(i) for i, _ in batch)
    ids = torch.tensor([i + [pad] * (n - len(i)) for i, _ in batch])
    lab = torch.tensor([lb + [-100] * (n - len(lb)) for _, lb in batch])
    att = torch.tensor([[1] * len(i) + [0] * (n - len(i)) for i, _ in batch])
    return ids, att, lab


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 20), b""):
            h.update(ch)
    return h.hexdigest()


def package(out_dir, version):
    """Per-file checksums + a reproducible tarball (the GitHub Release asset) + model.sha256 of that tarball."""
    files = sorted(f for f in os.listdir(out_dir) if os.path.isfile(os.path.join(out_dir, f))
                   and f not in ("model.sha256", "files.sha256") and not f.endswith(".tar.gz"))
    with open(os.path.join(out_dir, "files.sha256"), "w") as f:
        for n in files:
            f.write(f"{sha256_file(os.path.join(out_dir, n))}  {n}\n")
    tar_path = os.path.join(out_dir, f"model-{version}.tar.gz")
    with open(tar_path, "wb") as raw, gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as gz, \
            tarfile.open(fileobj=gz, mode="w") as tar:
        for n in files:
            ti = tar.gettarinfo(os.path.join(out_dir, n), arcname=n)
            ti.mtime, ti.uid, ti.gid, ti.uname, ti.gname = 0, 0, 0, "", ""
            with open(os.path.join(out_dir, n), "rb") as fh:
                tar.addfile(ti, fh)
    with open(os.path.join(out_dir, "model.sha256"), "w") as f:
        f.write(f"{sha256_file(tar_path)}  model-{version}.tar.gz\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="training/config.yaml")
    ap.add_argument("--subset", type=int, default=0)
    a = ap.parse_args()
    cfg = yaml.safe_load(open(a.config))
    seed_all(cfg["seed"])
    torch.set_num_threads(max(1, os.cpu_count() or 1))

    recs = [json.loads(x) for x in open(cfg["train_file"], encoding="utf-8") if x.strip()]
    recs = recs[: a.subset or cfg["num_records"]]
    tok = AutoTokenizer.from_pretrained(cfg["base_model"])
    tok.pad_token = tok.eos_token
    model = AutoModelForCausalLM.from_pretrained(cfg["base_model"])
    data = [encode(tok, r, cfg["max_seq_length"]) for r in recs]
    g = torch.Generator().manual_seed(cfg["seed"])
    dl = DataLoader(data, batch_size=cfg["batch_size"], shuffle=True, generator=g,
                    collate_fn=lambda b: collate(b, tok.pad_token_id))
    opt = torch.optim.AdamW(model.parameters(), lr=cfg["learning_rate"], weight_decay=cfg["weight_decay"])
    total = len(dl) * cfg["epochs"]
    sched = get_linear_schedule_with_warmup(opt, int(cfg["warmup_ratio"] * total), total)

    loss_csv = cfg["loss_csv"] if not a.subset else "training/loss_subset.csv"
    out_dir = cfg["output_dir"] if not a.subset else "out/models/subset"
    os.makedirs(os.path.dirname(loss_csv), exist_ok=True)
    os.makedirs(out_dir, exist_ok=True)
    model.train()
    rows = []
    for ep in range(1, cfg["epochs"] + 1):
        tot, n = 0.0, 0
        for ids, att, lab in dl:
            loss = model(input_ids=ids, attention_mask=att, labels=lab).loss
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step(); sched.step(); opt.zero_grad()
            tot += loss.item(); n += 1
        rows.append((ep, tot / n))
        print(f"epoch {ep}/{cfg['epochs']} train_loss {tot/n:.4f}", flush=True)
    with open(loss_csv, "w", newline="") as f:
        w = csv.writer(f); w.writerow(["epoch", "train_loss"]); w.writerows(rows)

    model.save_pretrained(out_dir)
    tok.save_pretrained(out_dir)
    import transformers
    json.dump({"version": cfg["version"], "base_model": cfg["base_model"], "seed": cfg["seed"],
               "epochs": cfg["epochs"], "num_records": len(recs), "torch": torch.__version__,
               "transformers": transformers.__version__}, open(os.path.join(out_dir, "version.json"), "w"), indent=2)
    package(out_dir, cfg["version"])
    print("saved to", out_dir)


if __name__ == "__main__":
    main()
