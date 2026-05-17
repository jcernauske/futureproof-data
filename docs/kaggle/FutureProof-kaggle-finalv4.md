## FutureProof: Every Student Should See Where Their Degree Leads

My 17-year-old daughter sat across from a counselor responsible for 400 students (60% over the 250 recommended by the American School Counselor Association), deciding between three majors at five schools. The best tools on offer were slick brochures and "do some Googling." She got 15 minutes of one-on-one planning.

The schools were selling lazy rivers, omelette stations and Sallie Mae loans. Nobody showed her salary data, debt projections, or what the work looks like in 10 years. She was asked to commit six figures on marketing and guesswork.

I built FutureProof to give students like her what no brochure would: a picture of where each path leads, including which may not survive AI.

### The Problem

Every year, millions of students commit to expensive programs without seeing their outcomes. The data exists. The Department of Education publishes earnings by program, BLS tracks occupation growth, O*NET catalogs every task inside every job. None of it is connected, and none of it makes sense to a 17-year-old. The result is $1.77 trillion in student loan debt, a third of graduates working jobs that don't require their degree, and a counseling system running on fumes.

And the part no brochure will ever mention: betting four years and six figures on a job description that AI may automate away before graduation.

Wealthy families hire $400/hr private consultants for this research. Some schools don't have reliable internet for "Googling." Lack of data isn't the problem. Interpretation is, and right now only money buys it.

### What FutureProof Does

FutureProof turns nine public datasets into an RPG-style career profile a student will click through.

You pick a school and major. Gemma resolves your free-text input ("Marketing, Deaf Ed, Accounting, Info Sec") into the precise CIP code, queries a sovereign data lakehouse, and builds your character. You get five stats on a pentagon: **ERN** (earnings, from College Scorecard + BLS), **ROI** (15-year return vs. 4-year cost), **RES** (AI resilience, where Gemma 4 26B scores each occupation's AI exposure on a 0–10 scale by reasoning over its O*NET task list, blended with Karpathy and Anthropic's Economic Index), **GRW** (BLS employment growth), and **AURA** (institutional brand gravity from IPEDS finance and EADA athletics data).

After that come the boss fights. Five threats every career faces (AI automation, student loan debt, market saturation, burnout, and the earnings ceiling) are scored and rendered as WIN/DRAW/LOSE with Gemma-generated narratives. When a student loses, Gemma generates a personalized skill pool of certifications, tools, and experiences. Equip a skill, reroll, and the stats change. Telling a 17-year-old AI is coming for her career is the easy part. Telling her what to learn to stay ahead of it is the product.

### Why Gemma 4

FutureProof could not work with a closed-model API.

Gemma calls MCP tools that query an Apache Iceberg lakehouse via DuckDB. Every structured Gemma surface (CIP resolution, the five explain-stat receipts, boss narratives, skill pools) issues real tool calls, backed by a three-tier resilience path: native tool call, content-JSON extraction, structural re-prompt. The deterministic split (Gemma routes and explains, Gold tables score) holds on both runtimes, so every number stays reproducible.

E4B on Ollama lets any school run FutureProof on their own hardware with `ollama pull gemma4:e4b`. No API key, no token cost, no student data leaving campus. A Title I school with a $600 Mac Mini gets the same AI-aware guidance as a private school or a $400/hr consultant. Public schools can't sign enterprise AI contracts or send student data to the cloud without FERPA review, and open weights are how that wall comes down.

The model is also natively multilingual. FutureProof switches between English, Spanish, and Arabic. Spanish covers ~75% of US English-learner students, and Arabic is among the fastest-growing home languages in midwestern Title I districts. Canonical English values (BLS, O*NET, CIP/SOC codes, JSON keys) stay consistent across languages so the data layer never breaks. Six-figure decisions should be supported in the language a family speaks at home.

### Technical Architecture

![FutureProof architecture: Gemma resolves CIP intent, FutureProof splits into a deterministic path (Gold tables compute scores) and a generative path (Gemma 4 writes narratives and skills); skills feed back into scoring on rematch.](https://futureproof.hyenastudios.com/architecture.png)

A medallion-architecture lakehouse joins nine public datasets into Gold-zone tables: *College Scorecard*, *BLS*, *ONET*, the *NCES CIP-SOC crosswalk*, *BEA Regional Price Parities*, *IPEDS finance*, *EADA*, *Karpathy AI Exposure*, and the *Anthropic Economic Index*. The MCP server exposes 9 tools to Gemma covering the core school+major query, occupation and ONET detail, branch trees, reverse career-to-school search, AURA, and three geographic tools for cost-of-living and purchasing-power.

The stack is FastAPI plus React/TypeScript/Vite over Apache Iceberg and DuckDB, with Ollama or OpenRouter behind one environment variable. The user-facing difference between cloud 26B and local E4B is about 30 additional seconds of loading time during build creation.

### Evaluation

I ran 215 labeled cases against the highest-leverage Gemma integration points: career intent, the five stat explainers (ERN/ROI/RES/GRW/AURA), and the generated skill pool.

On Ollama + `gemma4:e4b`, career intent scored 100/100 across common majors, niche specialties, typos, conversational input, and nonsense. Stat explainers scored 100% schema validity and 100% correct stat-code identification across 100 runs. 87% of generated skills were very likely to exist at the named school, 91% were factually accurate, and 4.5% (5 of 111) were flagged as convincing hallucinations. If a student catches the hallucination by doing follow-up research, Gemma and I did our job.

Latency on local E4B is fast enough for interactive use: median 1.7-2.5s on stat receipts, 3.4s on skill pool, 2.8s on career intent, with p99 tails reaching 12-22s on the largest outputs.

Full methodology, per-surface latency, and per-skill fact-check judgments are in `reports/eval-v3-2026-05-13.md`.

### Challenges and What I Learned

The CIP-SOC crosswalk is the hardest table in education data. Mapping "what you study" to "what you become" requires a government crosswalk designed for statisticians. "Pre-med" returns biology-adjacent SOCs but not physician, because becoming a doctor requires post-graduate education the crosswalk doesn't model. "Deaf education" maps to "Special Education" and stops. I built Gemma-driven SOC expansion: when intent signals suggest missing occupations, Gemma receives a candidate pool from `occupation_profiles` and uses tool calling to select missing SOCs, capped at five additions. The alternative was asking a 17-year-old to know which of 1,949 CIP classifications matched her intent.

Function calling adherence scales with model size. The 26B path chains live tool calls inside free-form "Ask the Guide"; on E4B I answer from the build context already in the prompt, because a chat that sometimes calls tools and sometimes hallucinates one was the worse product. Both paths share the MCP server and the deterministic Gold-zone scoring.

Grounding Gemma took most of the prompt work. Every surface receives the student's actual numbers, and a shared voice-contract module enforces strict rules with tests asserting forbidden tokens never appear in output.

The RPG framing is deliberate. A pentagon stat sheet resonates with students who grew up on Pokemon Go, and "Fight AI" with a LOSE lands differently than "82% AI exposure score." Applying skills before rematches forces students to face the work, and surfaces questions they didn't know to ask.

### For Every Student

FutureProof didn't tell my daughter what to choose. Who am I to crush dreams? My goal was to show her the road and the effort to navigate it, and push her to weigh hard data alongside everything else. The tool is free. The data is public. The weights are open. Any school can run this for any student, to make the most of those 15 minutes with the counselor.
