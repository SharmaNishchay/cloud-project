# AI use

**Student:** Nishchay Sharma (230101030)

## Tools used
- **Claude (Anthropic chat assistant):** helped me plan the project, wrote the first version of the repository (Makefile, worker, clean.py,
  training script, FastAPI service, Dockerfiles, Kubernetes manifests, CI workflow, test files, subnet and NACL draft) and helped me debug
  problems while running it on my laptop.
- **GitHub Copilot:** produced an earlier stub repository. It did not actually train a model or run a real service, so I discarded it
  and did not submit any of its code.

## How I checked what the tools gave me
- Ran `make lint test` (ruff and pytest) locally and in GitHub Actions.
- Ran `tools/nacl_sim.py` on the sample packets and recomputed the subnet sizes by hand.
- Ran every component myself: the k3d cluster, SeaweedFS, the two labelling workers, `clean.py` (checked that the counts add up),
  and a `make train SUBSET=50` smoke test.
- Read the real command output and logs and fixed the problems I hit. Examples: images missing in the cluster (`ErrImagePull`),
  pod DNS failure to reach Ollama, the Docker VM disk becoming 100% full, and a dropped `kubectl port-forward` during upload.
- Teacher replies are stored exactly as generated and were never edited by hand. The student is trained only on the cleaned teacher
  replies, never on `validation.jsonl`. All reported numbers come from my own runs.
- No secrets are committed; storage credentials are generated at deploy time and live only in Kubernetes Secrets.
