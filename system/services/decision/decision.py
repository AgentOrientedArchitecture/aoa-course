"""Decision service: typed, calibrated allocation answers for the planner.

Serves TypeSafe's ``POST /v1/systemone`` contract (state + typed questions in, per-option probabilities and
confidence out) from a Kev checkpoint. It never generates text: each question is one forward pass whose
readout is a probability distribution over the options the caller supplied, so it cannot invent a capability.

``DECISION_MODEL_RUN`` is a mounted run directory (the course's own fine-tuned allocator) or a Hugging Face id
(falls back to the released ``jaredpalmer/kev-0.8b``, which knows nothing about this registry and is only a
smoke-test stand-in). ``DECISION_DEVICE`` defaults to CPU so the container runs on a laptop.
"""
from __future__ import annotations

import os
import sys

RUN = os.environ.get("DECISION_MODEL_RUN", "jaredpalmer/kev-0.8b").strip()
PORT = os.environ.get("DECISION_PORT", "7500").strip()
DEVICE = os.environ.get("DECISION_DEVICE", "cpu").strip()
os.environ.setdefault("KEV_DTYPE", "fp32" if DEVICE == "cpu" else "bf16")
os.environ.setdefault("KEV_PREFIX_MIN_TOKENS", "32")   # the planner repeats the same goal for every task of a plan

if __name__ == "__main__":
    mounted = "/models/run"
    if RUN == "/models/run" or (os.path.isdir(mounted) and os.path.exists(os.path.join(mounted, "head.pt"))):
        RUN = mounted
    print(f"decision: loading {RUN} on {DEVICE}", flush=True)
    import uvicorn
    from kev.checkpoint import Checkpoint, LoadOptions
    from kev.serve import Server, app

    checkpoint = Checkpoint(RUN)
    tok, model = checkpoint.load(DEVICE, LoadOptions.from_env())
    app.state.server = Server(checkpoint, tok, model, DEVICE)
    print(f"decision: serving {checkpoint.requested} ({checkpoint.path}) on {DEVICE} :{PORT}", flush=True)
    # kev.serve.main() binds 127.0.0.1; inside a container the planner needs the service on all interfaces.
    uvicorn.run(app, host="0.0.0.0", port=int(PORT))
