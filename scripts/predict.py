"""Produce predictions.jsonl for score.py.
  --mode teacher  (needs Ollama; same prompt/settings as Task 1)
  --mode base     (untrained EleutherAI/pythia-70m)
  --mode student  --model-dir DIR   (trained model)
"""
import argparse
import json
import os
import sys

sys.path.insert(0, "training")
sys.path.insert(0, "worker")

ap = argparse.ArgumentParser()
ap.add_argument("--mode", required=True, choices=["teacher", "base", "student"])
ap.add_argument("--model-dir")
ap.add_argument("--data", default="data/validation.jsonl")
ap.add_argument("--out", required=True)
ap.add_argument("--max-new-tokens", type=int, default=64)
a = ap.parse_args()

recs = [json.loads(x) for x in open(a.data, encoding="utf-8") if x.strip()]
preds = []
if a.mode == "teacher":
    os.environ.setdefault("S3_ENDPOINT", "x"); os.environ.setdefault("S3_ACCESS_KEY", "x"); os.environ.setdefault("S3_SECRET_KEY", "x")
    os.environ.setdefault("OLLAMA_URL", "http://localhost:11434")
    import worker as w
    tpl = open("prompts/teacher_prompt.txt", encoding="utf-8").read()
    for r in recs:
        preds.append(w.ask_teacher(w.build_prompt(tpl, r["text"])))
else:
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from infer import generate
    src = "EleutherAI/pythia-70m" if a.mode == "base" else a.model_dir
    tok = AutoTokenizer.from_pretrained(src)
    model = AutoModelForCausalLM.from_pretrained(src).eval()
    for i, r in enumerate(recs):
        preds.append(generate(model, tok, r["text"], a.max_new_tokens))
        if i % 20 == 0:
            print(i, flush=True)
os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
with open(a.out, "w", encoding="utf-8") as f:
    for r, p in zip(recs, preds):
        f.write(json.dumps({"id": r["id"], "prediction": p}, ensure_ascii=False) + "\n")
print("wrote", a.out)
