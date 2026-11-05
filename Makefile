PY        ?= python
CONFIG    ?= training/config.yaml
GH_REPO   ?= $(shell git config --get remote.origin.url 2>/dev/null | sed -E 's#.*github.com[:/]##; s#\.git$$##')
VERSION   ?= v1

.PHONY: up down setup train test lint build deploy label clean-data publish eval loadtest

# ---- whole system from a fresh clone:  make up ----
up: build
	k3d cluster create --config cluster/k3d.yaml || true
	k3d image import cmd-parser:1.0 cmd-worker:1.0 -c cloudmini
	kubectl apply -f k8s/00-namespaces.yaml
	scripts/secrets.sh
	kubectl apply -f k8s/10-seaweedfs.yaml
	kubectl -n data rollout status deploy/seaweedfs --timeout=300s
	GH_REPO=$(GH_REPO) scripts/with_s3.sh $(PY) scripts/bootstrap_s3.py
	kubectl apply -f k8s/30-app.yaml
	kubectl -n app rollout status deploy/parser --timeout=600s
	@echo "ready: curl -X POST localhost:8080/parse -H 'Content-Type: application/json' -d '{\"text\":\"what is the weather in london\"}'"

down:
	k3d cluster delete cloudmini

build:
	docker build -f service/Dockerfile -t cmd-parser:1.0 .
	docker build -f worker/Dockerfile -t cmd-worker:1.0 .

# ---- Task 1 ----
label:            # needs: OLLAMA_HOST=0.0.0.0 ollama serve  (+ ollama pull phi3.5)
	kubectl apply -f k8s/20-label-job.yaml
clean-data:       # clean teacher shards -> datasets/v1/train.jsonl(+.sha256), then copy to data/train.jsonl
	scripts/with_s3.sh $(PY) worker/clean.py
	scripts/with_s3.sh $(PY) -c "import sys; sys.path.insert(0,'worker'); import s3; c=s3.client(); open('data/train.jsonl','w').write(s3.get_text(c,'datasets','v1/train.jsonl')); open('data/train.sha256','w').write(s3.get_text(c,'datasets','v1/train.sha256'))"

# ---- Task 2 ----
setup:
	$(PY) -m venv .venv && .venv/bin/pip install -r training/requirements.txt pytest ruff fastapi httpx jsonschema locust
train:            # make train [SUBSET=50] [CONFIG=training/config_v2.yaml]
	$(PY) training/train.py --config $(CONFIG) $(if $(SUBSET),--subset $(SUBSET),)
publish:          # make publish VERSION=v1  (needs port-forward access + gh CLI)
	scripts/with_s3.sh $(PY) scripts/publish_model.py $(VERSION)
	mkdir -p models/$(VERSION) && cp out/models/$(VERSION)/model.sha256 out/models/$(VERSION)/files.sha256 out/models/$(VERSION)/version.json models/$(VERSION)/
	gh release create model-$(VERSION) out/models/$(VERSION)/model-$(VERSION).tar.gz --title "model $(VERSION)" --notes "see models/$(VERSION)/model.sha256" || \
	gh release upload model-$(VERSION) out/models/$(VERSION)/model-$(VERSION).tar.gz --clobber
eval:             # make eval  -> results/ for teacher, base, student
	$(PY) scripts/predict.py --mode teacher --out results/teacher_predictions.jsonl
	$(PY) scripts/predict.py --mode base --out results/base_predictions.jsonl
	$(PY) scripts/predict.py --mode student --model-dir out/models/v1 --out results/student_predictions.jsonl
	$(PY) tools/score.py results/teacher_predictions.jsonl data/validation.jsonl --out results/teacher_validation.json
	$(PY) tools/score.py results/base_predictions.jsonl data/validation.jsonl --out results/base_validation.json
	$(PY) tools/score.py results/student_predictions.jsonl data/validation.jsonl --out results/student_validation.json

# ---- Task 6 / 7 ----
lint:
	ruff check .
test:
	$(PY) -m pytest -q
loadtest:
	scripts/loadtest.sh 2m results/loadtest
