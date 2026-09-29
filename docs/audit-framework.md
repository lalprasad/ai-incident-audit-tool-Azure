# Audit framework

The rubric lives in `backend/app/config/audit_criteria.json`. Change weights, classification bands, confidence bands, timeliness expectations, or the wording of a score level there. The scoring engine and the UI read that file. The system prompt is `backend/app/ai/prompts/audit_system_prompt.txt`.

## Measures

Scores are integers from 1 to 5.

### User engagement and investigation handling

Looks at work notes and additional comments, not at how many comments exist. The mock checks for acknowledgement, investigation, progress, a blocker, a next step, and resolution communication, then applies a timeliness penalty only when both the first update and the longest gap exceed the priority expectation (P1 1 hour, P2 4 hours, P3 8 hours, P4 24 hours).

Scores 1 and 2 are system-defined extensions: very limited communication, or no meaningful updates. An empty trail is not evidence that people were informed.

### Issue diagnosis

The ticket should say what caused the issue, where it occurred, and why. Naming a configuration item only in the assignment metadata does not count. "Pipeline failed" is a symptom. Two different `Root cause:` statements are a conflict, not a license to pick one.

### Solutioning

The resolution should say what changed, who performed it, and how recovery was checked. The assigned-to field is not ownership. If the action is described and validated but no person is named, the mock scores 2 and the review flag is "missing resolution ownership".

## Totals

```
total = sum(score × weight)
maximum = sum(5 × weight)
percentage = round_half_up(total / maximum × 100, 2)
```

Default weights are 1, so the maximum is 15. Classification bands:

- 90 to 100 Excellent
- 75 to 89.99 Good
- 60 to 74.99 Fair
- 0 to 59.99 Needs Improvement

If the model returns `overall_score`, `percentage`, or `classification`, those fields are ignored.

## Evidence

A supported evidence item must contain at least 12 characters that appear in the ticket after whitespace is collapsed. Anything else is stored as insufficient evidence and is not shown as a quote. Invented timestamps and page numbers are removed.

## Confidence

- 0.85 and above: High confidence
- 0.70 to 0.84: Medium confidence
- below 0.70: Requires human review

## Reproducibility

Each stored audit records criteria version, prompt version, model version, and `totals_computed_by = scoring_engine`. Re-scoring a stored measure list with the same criteria file produces the same percentage.

`sample-data/evaluation-dataset.json` lists expected ranges for the mock auditor. It is not an answer key the scorer reads.
