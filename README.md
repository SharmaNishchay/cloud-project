# Cloud Computing (CS3081) Mini Project: distilled command parser on local Kubernetes

**Name:** Nishchay Sharma
**Roll number:** 230101030
**GitHub repository:** https://github.com/SharmaNishchay/cloud-project

---

# Cloud Computing mini project - distilled command parser on local Kubernetes

GitHub repo: <PUT YOUR REPO LINK HERE>   |   Name: <name>   Roll no.: <roll>

Prereqs: Docker, k3d, kubectl, Python 3.11, [Ollama](https://ollama.com) with `phi3.5`, `gh` CLI (for releases), `locust`.

## Build + deploy from a fresh clone
    git clone <repo> && cd <repo>
    make up            # cluster, SeaweedFS, buckets, restores model v1/v2 from the GitHub Release, deploys the service
    curl -X POST localhost:8080/parse -H 'Content-Type: application/json' -d '{"text":"what is the weather in london"}'

## Pipeline (Tasks 1-2)
    ollama pull phi3.5 && OLLAMA_HOST=0.0.0.0 ollama serve      # separate terminal
    make label            # 2 parallel workers in namespace `pipeline`; watch: kubectl -n pipeline logs -f -l job-name=teacher-label
    make clean-data       # datasets/v1/train.jsonl + train.sha256 (also copied to data/)
    make setup && . .venv/bin/activate
    make train SUBSET=50  # smoke test;  make train  -> v1;  make train CONFIG=training/config_v2.yaml -> v2
    make publish VERSION=v1 && make publish VERSION=v2
    make eval             # teacher / base / student scores into results/

## Test, load test, tear down
    make lint test
    make loadtest         # standard Locust command through the Ingress
    python scripts/cold_start.py ; python scripts/cost.py results/loadtest_stats.csv --replicas 2
    make down
See RUNBOOK.md for the Task 3/4 experiments (rolling update, recovery, HPA, load balancing).
