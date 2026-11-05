# Work packages (do in order; each is small enough for one chat; paste only SPEC.md + that package)

WP0 Repo hygiene: replace stubs with this scaffold. Add .venv/.pytest_cache to .gitignore. `make lint test` green.
   ACCEPT: pytest 9 passed.
WP1 Cluster + storage: `make up` (cluster, SeaweedFS ns data, buckets, upload pool). ACCEPT: kubectl -n data get pods Running; buckets listed.
WP2 Teacher: `ollama pull phi3.5`; test prompt on 20 commands (python scripts/predict.py --mode teacher on validation first 20);
   improve prompts/teacher_prompt.txt until >=90% valid. Then `make label` (2 workers). ACCEPT: shard-0/1 objects, ids 3000 unique.
WP3 Clean: `make clean-data`. ACCEPT: counts table balances; rerun gives same sha256 as train.sha256.
WP4 Train: `make train SUBSET=50`, then `make train`, then v2 (`CONFIG=training/config_v2.yaml`). `make publish VERSION=v1/v2`.
   ACCEPT: loss.csv per epoch; release asset sha256 == models/v1/model.sha256.
WP5 Eval: `make eval`. ACCEPT: 3 prediction files + 3 reports in results/. If student validity <95%: raise epochs / lr in config, retrain (v1 again).
WP6 Service image: docker build; Task 3 steps in RUNBOOK.md (50 reqs at 1 CPU/1GiB, peak mem, FAULT_INJECT). ACCEPT: image <=2GB, evidence in results/.
WP7 K8s experiments: RUNBOOK.md Task 4 items 1-7, evidence in results/.
WP8 CI: push, run workflow normal (green) and with model=base (red at quality-gate). Save the URLs.
WP9 Load test + cost: scripts/loadtest.sh, kubectl top, scripts/cost.py. ACCEPT: p95<=5000 ms, errors<=1%.
WP10 Docs: report/report.pdf (<=8 pages, one section/task, measured vs assumed), README links, AI_USE.md (true), tag `final`, build <roll>.zip.
