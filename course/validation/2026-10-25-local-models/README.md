# Local decision-model trial

## Clef on Bees — 25 October 2026

The running service was **llama.cpp with Cloudflare Clef-Flash Q5_K_M**, on the
Bees Strix Halo machine. It already exposed the native `/v1/systemone` protocol.
No Ollama upgrade or service replacement was needed. The installed Ollama client
was 0.12.3 and its default port was not running; that was not the service tested.

The probe used the actual course `allocate()`, `promote()` and `decide()` code.
An in-process transport connected the caller to the decision adapter; the adapter
made real requests to Bees through a temporary SSH tunnel. No application AU was
executed and no wiki content was published. The three wiki inputs were manually
constructed parsed notes, so this did not validate source extraction.

| Synthetic case | Observed outcome, both repeats | Winning probability |
|---|---|---:|
| Data-engineering assessment | `evaluator-cv-data` | 0.828 |
| Frontend assessment | `evaluator-cv-frontend` | 0.949 |
| Image generation, outside the available AUs | `no_suitable_capability`; allocation held | 0.958 |
| Relevant architecture note | `promote` | 0.901 |
| Unrelated fiction | `reject` | 0.954 |
| Unsupported agent-cost claim | `review` | 0.792 |

All **12 responses** satisfied the course's distribution checks and matched these
hand-authored expectations. AU candidate order was reversed on the second pass.
The acceptance gate remained at **0.65**, with unscored choices disabled.

Observed decision latency through the tunnel was **0.382–0.976 seconds**, median
**0.800 seconds**. The model was already loaded; these are warm functional checks,
not cold-start measurements, calibration or an end-to-end throughput benchmark.
No hosted model was called by the probe. Local hardware and power costs were not
estimated, so the report does not describe local inference as cost-free.

[Full evidence](bees-clef.json) includes synthetic requests, normalized responses,
caller outcomes, fixture and implementation hashes, and timing. The recorded Git
HEAD predates the adapter change; the implementation hashes identify the exact
working files used in the trial.

## Repeat a bounded local check

After installing `tests/requirements.txt`, point the probe at an already running
native System One server. It does not read `.env` or change the active course:

```bash
.venv-course/bin/python tests/check_local_decision.py \
  --base-url http://127.0.0.1:11434 \
  --model clef-flash \
  --output .course-data/clef-check.json
```

On Windows use `.venv-course\Scripts\python` and put the arguments on one line.
The output file must be new. If the local server requires authentication, supply
`--api-key-env NAME_OF_LOCAL_KEY_VARIABLE`; never put a key in the command itself.
Inspect mismatches and errors rather than repeatedly rerunning until green.

For the live course configuration, use the optional [native local decision
settings](../../pre-work/SETUP.md#native-local-decisions-with-clef). The hosted
Cerebras/TypeSafe defaults are unchanged.

## Clef on the Mac — 25 October 2026

The inspected Mac has 128 GiB of memory and oMLX 0.7.0 installed. Native decision
support is available in the newer oMLX line; the trial uses an isolated 0.7.2
environment rather than replacing the installed app. The selected decision
checkpoint is `Jundot/clef-flash-oQ4e`, revision
`4c190c57ae35c409e9a46c6069d52e7950e304b5`, which preserves the joint decision head.

The same probe returned **12 valid responses and 12 expected outcomes**. All six
choices matched the Bees trial, including abstention for the unsuitable task
and human review for the unsupported claim. Winning probabilities were not
identical across the different quantisations and runtimes; they remained above
the unchanged 0.65 gate in these examples.

| Synthetic case | Observed outcome, both repeats | Winning probability |
|---|---|---:|
| Data-engineering assessment | `evaluator-cv-data` | 0.827 |
| Frontend assessment | `evaluator-cv-frontend` | 0.937 |
| Image generation, outside the available AUs | `no_suitable_capability`; allocation held | 0.961 |
| Relevant architecture note | `promote` | 0.895 |
| Unrelated fiction | `reject` | 0.953 |
| Unsupported agent-cost claim | `review` | 0.763 |

Median request time was **0.249 seconds**. The first request, including model
loading, took **2.138 seconds**; subsequent requests ranged from **0.126 to
0.317 seconds**. These measurements differ from Bees in hardware, quantisation,
runtime and network path, so they do not isolate a hardware speed advantage.
[Mac decision evidence](mac-clef.json) records the full requests and results.

The server ran on loopback port 18000 with a 32 GB process memory guard,
Hugging Face offline mode and Transformers offline mode. The requests used no
hosted API. This verified the native decision route from the host Python probe,
not Docker-to-host connectivity or a complete course run. Both local models
were unloaded and the temporary server stopped after testing. The installed
oMLX app and active course `.env` remain unchanged. oMLX's shared cluster helper
was restored to the installed 0.7.0 app after the isolated runtime rewrote it.

## Local generation and the larger Qwen model

The existing `Qwen3.8-27B-4bit` model passed one local OpenAI-compatible JSON
generation check in oMLX 0.7.2. It reproduced three supplied CV task IDs in order;
this was **not intent decomposition, CV assessment or EVE acceptance testing**.
Elapsed time was 19.82 seconds, including a server-reported 16.8-second model
load; generation produced 35 tokens. The server warned that grammar-constrained
decoding was unavailable, so the valid JSON result was not schema-enforced.
[Generation evidence](mac-qwen-generation.json) records this narrow check.

Qwen3.8-Flash-Next-oQ4e-mtp is already downloaded on the Mac: its safetensor files
occupy approximately **98.99 GiB**. The existing Qwen3.8-27B-4bit weights occupy
approximately **14.95 GiB**. Weight size is not total runtime memory. Concurrent
Qwen Next, Clef, Docker and desktop applications need a separate memory and
latency rehearsal; the Bees decision result does not establish that this Mac
configuration fits or performs well. Flash-Next was not loaded during this
trial, and Qwen plus Clef were tested sequentially. The larger pair remains a
follow-up rehearsal; it is not yet a recommended classroom default.

Primary references: [Clef-Flash and its native API](https://ollama.com/library/clef-flash),
[Ollama decision interface](https://docs.ollama.com/capabilities/decision),
[oMLX 0.7.2](https://github.com/jundot/omlx/releases/tag/v0.7.2),
[the MLX checkpoint and joint head](https://huggingface.co/Jundot/clef-flash-oQ4e).
