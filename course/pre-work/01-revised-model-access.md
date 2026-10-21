# Revised model access

Use Docker and the existing course repository. Windows learners can run the revised shell launchers in WSL2; the original Windows launchers remain available for the original course.

## Hosted route

Copy `.env.cerebras-typesafe.example` to `.env.revised`. Add keys privately as `CEREBRAS_API_KEY` and `TYPESAFE_API_KEY`; alternatively keep keys in the ignored `.env` and leave them out of `.env.revised`. Never commit populated environment files.

The launchers load `.env` first, then `.env.revised`. The example leaves key variables unset so existing keys in `.env` are retained.

Generation uses the existing OpenAI-compatible adapter, Cerebras's endpoint and `gpt-oss-120b`. Decisions use TypeSafe's separate typed-choice API with the version pinned to `jev-1.13.0`. A model ID is recorded with each decision; the stable version avoids following the latest alias during a class.

Check provider access before the live session. Do not assume a permanent free tier or enough quota for a room of learners. Cerebras currently describes trial credits and free-trial rate limits; TypeSafe account access, credit and organisation limits need checking in the account. A provider outage or exhausted quota produces a visible error, never an unlabelled replacement decision.

Current primary references (checked 21 October 2026): [Cerebras rate limits](https://inference-docs.cerebras.ai/support/rate-limits), [Cerebras pricing](https://www.cerebras.ai/pricing), [TypeSafe models](https://docs.typesafe.ai/models), [TypeSafe Choice](https://docs.typesafe.ai/primitives/choice).

## Local route

Copy `.env.local-revised.example` to `.env.revised`. Install Ollama on the host and pull `gpt-oss:20b`, or choose another available model explicitly. On capable hardware use `gpt-oss:120b` for generation to retain the course comparison. The example uses the smaller model to keep an ordinary local option.

The decision baseline uses Ollama's constrained JSON output and temperature zero. It reports a named choice and **no probability estimate**. `DECISION_ALLOW_UNSCORED=true` is an explicit classroom policy. Schema constraints and temperature zero do not establish semantic accuracy, calibration or universal determinism.

Host Ollama is reached from containers at `host.docker.internal:11434`. For container Ollama, set both model endpoints to `http://ollama:11434`, set `AOA_LOCAL=1` when starting and ensure the named models are pulled into that container. Local and hosted routes use the same AU contracts and inspectable execution path.

## Start

```bash
./scripts/revised-up.sh 1
```

Open `http://localhost:8080`. Check `http://localhost:7250/healthz` from the host: it names the decision provider/model and says whether configuration is present. It does **not** claim a successful provider call. Run the first CV example to verify actual access.

Keep the model choice stable during the four sessions. Record model, prompts/skills hashes, candidate cards, task quality, failure/abstention rate, latency, usage and cost before considering a replacement. Do not compare a hosted price with local zero: local compute and operator time still have a cost.
