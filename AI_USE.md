# AI use

> EDIT THIS so it matches what YOU actually did. The assignment grades honesty and verification.

Tools: Claude (Anthropic chat assistant) - used for: scaffolding the repo (Makefile, Kubernetes manifests, worker, clean.py,
training script, FastAPI service, CI workflow), subnet/NACL calculation drafts, and explaining knowledge distillation.

How I checked the output (replace with what you really did):
- Ran `pytest` (unit tests for cleaning, sharding, the service and the NACL) and `ruff`.
- Verified subnet maths by hand and with `tools/nacl_sim.py`.
- Ran each component on my machine and compared against the handout requirements; fixed: <list real bugs you hit>.
- Teacher outputs were never edited by hand. Training data = teacher replies only (no validation data, no manual labels).
