# Session 1 CV Fit Data

Synthetic CVs and job descriptions for the three-agent CV fit workflow.
The learner instructions are in [`WALKTHROUGH.md`](WALKTHROUGH.md).

Use `cv-examples/` for parser input and `jd-examples/` for evaluator input.
The examples are deliberately small enough to paste into the Studio or drop as
plain text files.

## Expected verdicts

The walkthrough uses two contrasting pairs so you can see the evaluator and
reporter behave differently when fit is strong vs weak.

| CV | JD | Expected verdict |
| --- | --- | --- |
| `cv-examples/jordan-okafor.txt` | `jd-examples/senior-data-engineer-fintech.txt` | strong / fit |
| `cv-examples/sam-everett.txt` | `jd-examples/frontend-engineer-design-systems.txt` | fit |
| `cv-examples/jordan-okafor.txt` | `jd-examples/frontend-engineer-design-systems.txt` | weak / no |
| `cv-examples/sam-everett.txt` | `jd-examples/senior-data-engineer-fintech.txt` | weak / no |

## How to use

In the studio, drop a CV into the CV slot and a JD into the JD slot, then
hit submit. The studio writes both to the shared inbox volume and submits
their paths to the planner.

Or, if you'd rather drive the planner directly:

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

(With files of those names placed in the `inbox` volume by hand.)
