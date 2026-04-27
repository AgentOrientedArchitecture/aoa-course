# Example data

Synthetic CVs and JDs used in the Session 2 walkthrough. None of the people
or companies here are real. Add your own files alongside these — the system
doesn't care which inputs it receives, as long as they look roughly like CVs
and job descriptions in plain text.

## Pairings

The walkthrough uses two contrasting pairs so you can see the evaluator and
reporter behave differently when fit is strong vs weak.

| CV | JD | Expected verdict |
| --- | --- | --- |
| `cv-examples/jordan-okafor.txt`  | `jd-examples/senior-data-engineer-fintech.txt`     | strong / fit |
| `cv-examples/sam-everett.txt`    | `jd-examples/frontend-engineer-design-systems.txt` | fit          |
| `cv-examples/jordan-okafor.txt`  | `jd-examples/frontend-engineer-design-systems.txt` | weak / no    |
| `cv-examples/sam-everett.txt`    | `jd-examples/senior-data-engineer-fintech.txt`     | weak / no    |

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
