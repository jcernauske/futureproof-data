# Eval Results — 2026-05-13-214236

Backend: `ollama`
Run mode: `full`

## Per-surface scores

| Surface | N cases | Metrics |
|---------|--------:|---------|
| career_intent | 20 | field_accuracy: 21/21 |
| explain_ern | 20 | field_accuracy: 20/20<br>content_check: 17/20<br>length_range: 40/40 |
| explain_roi | 20 | field_accuracy: 20/20<br>content_check: 18/20<br>length_range: 40/40 |
| explain_res | 20 | field_accuracy: 20/20<br>content_check: 13/20<br>length_range: 40/40 |
| explain_grw | 20 | field_accuracy: 20/20<br>content_check: 8/20<br>length_range: 40/40 |
| explain_aura | 20 | field_accuracy: 20/20<br>content_check: 10/20<br>length_range: 40/40 |

## Latency (all 20 surfaces, from logs/gemma.jsonl)

| Surface | n | p50 ms | p95 ms | p99 ms |
|---------|--:|------:|------:|------:|
| boss_narrative | 5 | 2736 | 16770 | 18380 |
| career_description | 1 | 1805 | 1805 | 1805 |
| career_intent | 20 | 2978 | 12987 | 18319 |
| explain_aura | 20 | 1662 | 4626 | 4983 |
| explain_ern | 20 | 1814 | 2756 | 5926 |
| explain_grw | 20 | 1774 | 3034 | 3208 |
| explain_res | 20 | 2354 | 4578 | 4682 |
| explain_roi | 20 | 1683 | 3823 | 4086 |
| guidance | 1 | 7662 | 7662 | 7662 |
| initial_major_resolution | 2 | 17166 | 25018 | 25716 |
| skill_recs | 1 | 21154 | 21154 | 21154 |
