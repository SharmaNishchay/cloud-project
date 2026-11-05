# Runbook: experiments and the evidence to save in results/

Save every command's output, e.g. `... 2>&1 | tee results/<name>.txt`.

## Task 1 evidence
    k3d cluster list; kubectl -n data get pods; kubectl -n pipeline get pods -o wide
    scripts/with_s3.sh python -c "import sys;sys.path.insert(0,'worker');import s3;c=s3.client();print([o['Key'] for b in ('datasets','models') for o in c.list_objects_v2(Bucket=b).get('Contents',[])])"
    make clean-data | tee results/clean_counts.txt        # counts table for the report
Check shards: every C-id exactly once (clean.py prints "records 3000 unique ids 3000"). Rerun clean.py -> same sha256.

## Task 3: container + 50 requests at 1 CPU / 1 GiB
    docker build -f service/Dockerfile -t cmd-parser:1.0 .  &&  docker images cmd-parser:1.0     # <= 2 GB
    # run against S3 reachable from the host (port-forward svc/seaweedfs 18333:8333); creds via env, not files
    docker run -d --name t3 --cpus=1 --memory=1g --add-host=host.docker.internal:host-gateway -p 8000:8000 \
      -e MODEL_URI=s3://models/v1/ -e MODEL_VERSION=v1 -e S3_ENDPOINT=http://host.docker.internal:18333 -e MAX_NEW_TOKENS=64 \
      -e S3_ACCESS_KEY -e S3_SECRET_KEY cmd-parser:1.0
    curl -s -o /dev/null -w '%{http_code}\n' localhost:8000/readyz            # 503 then 200
    (for i in $(seq 50); do curl -s -X POST localhost:8000/parse -H 'content-type: application/json' -d '{"text":"what is the weather in london"}'; echo; done) &
    for i in $(seq 60); do docker stats --no-stream --format '{{.MemUsage}}' t3; sleep 1; done | tee results/t3_mem.txt   # report the peak
    docker inspect t3 --format '{{.State.OOMKilled}}'                          # false
    # FAULT_INJECT test: run a second container with -e FAULT_INJECT=1 -> /parse returns 500 {"error":"invalid_model_output"}

## Task 4 (cluster up via `make up`, load test URL http://localhost:8080)
1. Ingress works: `curl -i -X POST localhost:8080/parse -H 'content-type: application/json' -d '{"text":"remove the upcoming calendar event"}'`
2. Not-ready endpoints while loading: `kubectl -n app rollout restart deploy/parser; kubectl -n app get endpoints parser -w` (empty until /readyz = 200).
3. HPA: `kubectl -n app scale deploy/parser --replicas=1` then a long load test (`scripts/loadtest.sh 6m results/hpa`), in another terminal
   `kubectl -n app get hpa -w` and `kubectl top pods -n app`. Show 1 -> 2 under load and back to 1 after cooling (~5 min).
   Limitation: single node (one laptop), so no real multi-machine capacity; HPA reacts slowly (metrics-server ~15-60 s, 5 min scale-down).
4. Rolling update (during `scripts/loadtest.sh 5m results/rolling`):
       kubectl -n app set env deploy/parser MODEL_VERSION=v2 MODEL_URI=s3://models/v2/
       kubectl -n app rollout status deploy/parser
       kubectl -n app rollout undo deploy/parser && kubectl -n app rollout status deploy/parser
   Failed requests must be <= 0.5%; loadtest_headers.json shows versions; after undo `curl -si ... | grep X-Model-Version` = v1.
   NOTE `rollout undo` restores the whole previous pod template (env included) -> v1.
5. Recovery (during `scripts/loadtest.sh 3m results/recovery`): `kubectl -n app delete pod $(kubectl -n app get pods -o name | head -1)`;
   `kubectl -n app get pods -w` shows the replacement; failed <= 2%.
6. Cold start: `python scripts/cold_start.py | tee results/cold_start.txt` (logs print "downloaded N files from s3://models/...").
7. Load balancing: `kubectl -n app scale deploy/parser --replicas=2` (HPA may fight you: `kubectl -n app delete hpa parser` for this test, then
   re-apply k8s/30-app.yaml); wait for 2 Ready; `scripts/loadtest.sh 2m results/loadtest`; read per_replica in results/loadtest_headers.json
   (each replica >= 30% of successes).

## Task 7
    kubectl top pods -n app      # run repeatedly DURING the load test, save the output
    python scripts/cost.py results/loadtest_stats.csv --replicas 2 --cpu-limit 1 --mem-limit-gib 1 --target 99 | tee results/cost.txt
Fill the review table with numbers from results/. Error rate = failures / requests from loadtest_stats.csv.

## Task 6: failing gate
GitHub -> Actions -> ci -> Run workflow -> model = base. The run fails at `quality-gate`; paste its URL in the report.
Create the release assets first (`make publish VERSION=v1`), then tag: `git tag final && git push --tags`.
