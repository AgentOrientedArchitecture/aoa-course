# Session 1: CV fit examples

Synthetic CVs and job descriptions for the CV fit workflow.
Start with the [Session 1 walkthrough](WALKTHROUGH.md): it covers startup,
capability inspection, evaluator selection, run review and live instruction
changes in one sequence. This page is the input catalogue and optional API
reference; [DECISIONS.md](DECISIONS.md) is optional background.

Use `cv-examples/` for parser input and `jd-examples/` for evaluator input.
The examples are deliberately small enough to paste into the Studio or drop as
plain text files.

## Example pairs

The walkthrough uses matching and mismatched pairs so you can compare the
assessment and report. These are expected directions for discussion, not
guaranteed verdicts: inspect the evidence when a model disagrees. The data job
document is titled **Senior Data Engineer — Healthcare Payments**; its existing
filename contains `fintech`.

| CV | JD | Expected verdict |
| --- | --- | --- |
| `cv-examples/jordan-okafor.txt` | `jd-examples/senior-data-engineer-fintech.txt` | strong / fit |
| `cv-examples/sam-everett.txt` | `jd-examples/frontend-engineer-design-systems.txt` | fit |
| `cv-examples/jordan-okafor.txt` | `jd-examples/frontend-engineer-design-systems.txt` | weak / no |
| `cv-examples/sam-everett.txt` | `jd-examples/senior-data-engineer-fintech.txt` | weak / no |

## Using the examples

In Studio, choose **CV fit**, drop a CV into **CV** and a job document into
**Job description**, then enter **Assessment emphasis** and choose **Run CV fit**.
Studio writes both documents to the shared `system/inbox/` folder and submits
their container paths to the planner. The emphasis helps choose among the
three evaluator AUs; the selected evaluator assesses the document contents.

## Optional: call the planner directly

With Session 1 running, copy the two example files into `system/inbox/` in the
same checkout. Docker exposes that folder to the services as `/data/inbox/`.
This Bash example submits a CV workflow without an assessment emphasis:

```bash
curl -s http://localhost:7200/intent \
  -H 'content-type: application/json' \
  -d '{
    "kind": "cv-fit",
    "inputs": {
      "cv_path": "/data/inbox/jordan-okafor.txt",
      "jd_path": "/data/inbox/senior-data-engineer-fintech.txt"
    }
  }'
```

Inspect the returned trace in Studio. A path in the request must name a file
inside the container; an arbitrary laptop path is not accessible to the AU.
