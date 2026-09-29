# Sample ServiceNow extracts

`multi-ticket.txt` is the canonical extract. `multi-ticket.pdf` is the same text rendered for upload. The UI action **Load sample extract** uploads that PDF.

The extract is line-oriented. Each incident starts with `INCIDENT NUMBER:`. Single-value fields are `LABEL: value`. Narrative sections use an all-caps header and continue until the next header:

`DESCRIPTION`, `CAUSE`, `RESOLUTION NOTES`, `CLOSE NOTES`, `WORK NOTES`, `ADDITIONAL COMMENTS`.

Work notes and comments use:

```
[YYYY-MM-DD HH:MM] Full Name (internal|customer): Message
```

| Ticket | Scenario | What the text does |
| --- | --- | --- |
| INC1001 | Excellent | Acknowledgement, investigation, progress, blocker, next step, resolution, cause with where and why, named fix and validation |
| INC1002 | Good | Regular updates without a blocker, cause and location, named action, no validation |
| INC1003 | Fair | Two thin updates, location and reason without a root cause, restart with no owner |
| INC1004 | Poor | Closed with no notes, no diagnosis, and no resolution |
| INC1005 | Missing RCA | Useful handling and a named fix, but the only problem statement is "Pipeline failed." |
| INC1006 | Missing owner | Cause and validation are present. The resolution never names who acted. Assignment is not treated as ownership |
| INC1007 | Missing updates | Cause and a named fix are present. Work notes and comments are empty |
| INC1008 | Conflicting information | Two different `Root cause:` lines |

`evaluation-dataset.json` holds expected score ranges for the mock auditor. It is not used as an answer key by the scorer.

Regenerate the PDF after editing the text:

```bash
python sample-data/build_pdf.py
```
