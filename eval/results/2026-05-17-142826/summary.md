# Eval Results — 2026-05-17-142826

Backend: `ollama`
Run mode: `full`

## Per-surface scores

| Surface | N cases | Metrics |
|---------|--------:|---------|
| career_intent | 100 | field_accuracy: 99/101 |
| explain_aura | 20 | field_accuracy: 20/20<br>content_check: 15/20<br>length_range: 39/40 |
| explain_ern | 20 | field_accuracy: 20/20<br>content_check: 18/20<br>length_range: 39/40 |
| explain_grw | 20 | field_accuracy: 20/20<br>content_check: 16/20<br>length_range: 40/40 |
| explain_res | 20 | field_accuracy: 20/20<br>content_check: 5/20<br>length_range: 40/40 |
| explain_roi | 20 | field_accuracy: 20/20<br>content_check: 12/20<br>length_range: 40/40 |

## Latency (all 20 surfaces, from logs/gemma.jsonl)

| Surface | n | p50 ms | p95 ms | p99 ms |
|---------|--:|------:|------:|------:|
| career_intent | 100 | 4502 | 6614 | 6799 |
| explain_aura | 20 | 3057 | 3507 | 3662 |
| explain_ern | 20 | 2506 | 3207 | 3325 |
| explain_grw | 20 | 2526 | 2813 | 3020 |
| explain_res | 20 | 3047 | 4270 | 4451 |
| explain_roi | 20 | 3120 | 3502 | 3574 |
