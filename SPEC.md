# SPEC (compressed assignment, CS3081 mini project). Deadline 7 Nov 11:00 (hard). Individual. Free/open-source only.

Goal: command parser. Input: one short English command. Output: ONE JSON object, exactly keys intent,date,time,place.
intent in {alarm_set, alarm_query, calendar_set, calendar_query, calendar_remove, weather_query, datetime_query, recommendation_events}.
Slots: copy exact phrase from command (no conversion), shortest phrase (no at/on/in/for), else null, never invent.
Method: sequence-level KD. Teacher phi3.5 (Ollama, temperature 0, seed 42, our own prompt) labels commands_pool.jsonl (3000).
Student EleutherAI/pythia-70m fine-tuned on the FIRST 1500 cleaned records, CPU only, PyTorch+Transformers.
Never train on validation.jsonl. Teacher replies stored EXACTLY (no manual edits). Never fabricate results/numbers.
No credentials in repo. No model weights in git or in container image.

Kit: data/{commands_pool,validation}.jsonl schema.json rate_card.json; tools/{score.py,locustfile.py,nacl_sim.py}; network/packets_sample.jsonl.

## Tasks (marks)
T1 (12) k3d cluster from cluster/k3d.yaml; SeaweedFS in ns `data`; buckets `datasets`,`models`; commands_pool.jsonl in datasets;
  prompts/teacher_prompt.txt; worker/ reads SHARD_INDEX,SHARD_COUNT (line no. from 0, line % COUNT == INDEX), calls teacher,
  writes {"id","text","teacher_raw"} lines to datasets/teacher/shard-<i>.jsonl; >=2 workers concurrently in ns `pipeline`;
  every id in exactly one shard; worker/clean.py -> datasets/v1/train.jsonl (+train.sha256), id order, remove (a) invalid JSON
  (b) keys != 4 (c) bad intent (d) slot not null/not substring of command (e) duplicate commands (keep smallest id).
  Report counts: input=(a)+(b)+(c)+(d)+dups+kept. Half page on sharding. Re-running clean.py must reproduce the checksum.
T2 (20) training/config.yaml (seed, lr, batch, epochs, max_seq_len, library versions); `make train` reads only it;
  `make train SUBSET=50` works; training/loss.csv one row per epoch; seed fixed in code. Example format "Command: <c>\nJSON: <teacher json>".
  Save model+tokenizer to bucket models/v1/ and GitHub Release asset; models/v1/model.sha256 must match the release asset's SHA-256;
  second version in models/v2/. Run score.py on validation for teacher, untrained pythia, student -> results/ (raw outputs+reports;
  results/teacher_validation.json). Side-by-side table + discussion. 1-page explanation: sequence-level vs logit-based KD, why logit-based
  impossible here, one limitation. Hidden test: validity >=95%, full_frame >= half of teacher's.
T3 (14) service/ port 8000: POST /parse {"text"} -> 200 + 4-key JSON only, headers X-Model-Version, X-Served-By(pod name);
  GET /healthz 200 if alive; GET /readyz 503 until model loaded. Env: MODEL_URI, MODEL_VERSION, S3_ENDPOINT, MAX_NEW_TOKENS (+FAULT_INJECT=1
  replaces output with `not json`). Download model from object storage at start-up; creds from K8s Secret. Validate vs schema.json else
  500 {"error":"invalid_model_output"}. Pinned deps, CPU torch, no weights, image <=2GB, builds with one command. 50 sequential requests
  at 1 CPU/1GiB, report peak memory with command output.
T4 (22) ns `app`: Deployment(2 replicas, requests+limits), Service, Ingress /parse (Traefik); liveness /healthz, readiness /readyz (no endpoints
  while loading); HPA min1 max2 cpu70%, evidence 1->2->1; rolling update v1->v2 during load (<=0.5% fail) then `kubectl rollout undo`
  (header shows v1); delete a Pod during load (<=2% fail, replicas restored); cold start: delete all pods, logs show model download,
  3 runs median creation->Ready; load balancing with 2 ready replicas: each >=30% of successes. State single-node limitation.
T5 (10) subnets of 10.20.0.0/16 (done: app /22, public /24, data /25, mgmt /27) + network/nacl.json + half page explanation. (DONE in scaffold)
T6 (10) `make up` from fresh clone <=3 commands; `make down`; GitHub Actions: lint -> >=3 unit tests -> model eval (downloads Release asset,
  runs score.py on validation) -> quality gate `score.py --min-validity 95`; one run with untrained pythia that FAILS at gate (link in report);
  gitleaks clean; AI_USE.md (true).
T7 (12) standard locust cmd: p50,p95,rps,error rate,kubectl top pods, cold start (error<=1%, p95<=5000ms); cost per 1000 req =
  (hourly cost of all running replicas)/(requests per hour)*1000 using rate_card (CPU limit + mem limit per replica); SLO + error budget
  in requests; review table (6 rows, each w/ measured number, limitation, improvement).

## Submission: ONE file <roll_number>.zip containing: report/report.pdf (<=8 pages, one section per task), handwritten reflection
<roll_number>.pdf (3 pages, scanned, with GitHub link/name/roll), full repo (code, tests, Dockerfile, k8s, network, CI, results/),
README.md with GitHub link + build/deploy/test/teardown commands. Tag final commit `final`. Model files only as GitHub Release assets.
