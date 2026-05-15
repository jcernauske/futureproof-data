# Eval Results — 2026-05-13-183007

Backend: `ollama`
Run mode: `full`

## Per-surface scores

| Surface | N cases | Metrics |
|---------|--------:|---------|
| career_intent | 20 | field_accuracy: 0/21 |
| explain_ern | 20 | field_accuracy: 36/39 |
| explain_roi | 20 | field_accuracy: 33/37<br>adapter: 0/1 |
| explain_res | 20 | field_accuracy: 28/40 |
| explain_grw | 20 | field_accuracy: 40/40 |
| explain_aura | 20 | field_accuracy: 39/40 |

## Latency (all 20 surfaces, from logs/gemma.jsonl)

| Surface | n | p50 ms | p95 ms | p99 ms |
|---------|--:|------:|------:|------:|
| career_intent | 20 | 4730 | 5936 | 9550 |
| explain_aura | 20 | 3412 | 4684 | 5267 |
| explain_ern | 20 | 2506 | 2911 | 3262 |
| explain_grw | 20 | 2372 | 3133 | 3207 |
| explain_res | 20 | 5337 | 6010 | 6204 |
| explain_roi | 20 | 3210 | 4825 | 18380 |
