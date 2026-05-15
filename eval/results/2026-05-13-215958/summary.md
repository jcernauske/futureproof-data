# Eval Results — 2026-05-13-215958

Backend: `ollama`
Run mode: `full`

## Per-surface scores

| Surface | N cases | Metrics |
|---------|--------:|---------|
| career_intent | 100 | field_accuracy: 100/100<br>adapter: 0/1 |
| skill_pool | 15 | skill_specific_rate: 10/15<br>skill_school_attributed_rate: 0/15<br>skill_boss_relevant_rate: 15/15<br>skill_voice_compliant_rate: 15/15<br>skill_realism_aggregate: 5/15 |

## Latency (all 20 surfaces, from logs/gemma.jsonl)

| Surface | n | p50 ms | p95 ms | p99 ms |
|---------|--:|------:|------:|------:|
| ask_gemma_chat | 1 | 8119 | 8119 | 8119 |
| career_intent | 100 | 2769 | 18519 | 22169 |
| skill_pool | 15 | 3440 | 10099 | 12561 |
