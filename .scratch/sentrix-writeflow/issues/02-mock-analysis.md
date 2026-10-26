# Ticket 02 — mock analysis creation

## Scope

`POST /api/v1/findings/{finding_id}/analyses`

## Behaviour

- Reject unknown findings with 404.
- Use fixed mock model `modelversion-risk-4.8.2` and prompt
  `ptv-risk-1`.
- Insert `analysis` with `status=COMPLETED`, `simulated=true`,
  confidence 0.91, summary, limitations, input hash, latency 420.
- Return the analysis shape used by the UI.

## Acceptance

- 201 on a finding without a live analysis.
- 500 avoided for the unique live-analysis constraint; a second analysis
  for the same finding is rejected cleanly.
- Tracer analysis removed; seed count returns to 1.
