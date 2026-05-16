## FutureProof: Every Student Should See Where Their Degree Leads

My 17-year-old daughter Olivia sat across from a counselor responsible for 400 students (60% over the 250 recommended by the American School Counselor Association), deciding between three majors at five schools. The best tools anyone offered her were slick brochures and a suggestion to "do some Googling." Olivia got 15 minutes of one-on-one planning.

The schools are selling lazy rivers and omelette stations. Nobody showed her salary data, debt projections, or what the work actually looks like in 5 to 10 years. She was asked to commit six figures based on aggressive marketing and guesswork.

I built FutureProof to give students like Olivia what no brochure would: a clear picture of where each path leads, including which ones may not survive AI.

### The Problem

Every year, millions of students commit to expensive college programs without ever seeing where those programs lead. The data exists: the Department of Education publishes earnings by program, BLS tracks occupation growth, O*NET catalogs every task inside every job. But none of it is connected, and none of it makes sense to a 17-year-old. The result: $1.77 trillion in student loan debt, a third of graduates working jobs that don't require their degree, and a counseling system running on anecdote.

Wealthy families hire $400/hr private consultants who do this research for them. Some schools don't even have reliable internet for "Googling." Teenagers get a 15-minute meeting and a brochure. Lack of data isn't the problem; interpretation is, and right now only money buys it.

### What FutureProof Does

FutureProof translates nine datasets into something a student actually wants to explore: an RPG-inspired career profile.

Pick a school and major. Gemma resolves your free-text input ("Marketing, Deaf Ed, Accounting, Info Sec") into the precise CIP code, queries a sovereign data lakehouse, and builds your character. You see five stats on a pentagon chart: **ERN** (earnings, from College Scorecard + BLS), **ROI** (15-year return vs. 4-year cost), **RES** (AI resilience: Gemma 4 26B scores each occupation's AI exposure on a 0–10 scale by reasoning over its O*NET task list, blended with Karpathy and Anthropic's Economic Index), **GRW** (BLS employment growth), and **AURA** (institutional brand gravity from IPEDS finance and EADA athletics data).

Then: boss fights. Five threats every career faces — **AI automation**, **student loan debt**, **market saturation**, **burnout risk**, and the **earnings ceiling** — scored from data and rendered as **WIN/DRAW/LOSE** outcomes with Gemma-generated narratives. Lose a fight? Gemma generates a personalized skill pool of certifications, tools, and experiences that shift the odds. Equip a skill, reroll the fight, watch your stats change. I don't just tell a 17-year-old AI is coming for her career. I tell her what to learn to stay ahead of it.

A branching career tree shows where careers fork over time. A Marketing major doesn't just become a "marketing analyst." They can branch into product management, UX research, or data science, each with stat deltas from O*NET transition data.

On every screen, a chat panel is available that calls MCP tools in real time to answer follow-ups grounded in actual data. "What if I moved to Austin?", "What other schools lead to this career?"

### Why Gemma 4

FutureProof could not work with a closed-model API.

**Tool calling against local data.** Gemma calls MCP tools that query an Apache Iceberg lakehouse of federal education and labor data via DuckDB — selecting the right tool, passing typed arguments, and synthesizing tabular results into grounded responses. Every structured Gemma surface (CIP resolution, the five explain-stat receipts, boss narratives, skill pools) issues real tool calls on both backends, backed by a three-tier resilience path (native tool call → content-JSON extraction → structural re-prompt). On the hosted 26B path, free-form Ask the Guide additionally chains tool calls live. On the local E4B path, free-form Ask the Guide answers from the build context already loaded into the prompt — a deliberate call to keep open-ended chat predictable on small-model hardware. The deterministic scoring split (Gemma routes and explains, Gold tables score) holds on both runtimes, so every number a student sees stays reproducible.

**Zero-cost local inference via Ollama.** Any school can run FutureProof on their own hardware with `ollama pull gemma4:e4b`. No API key, no token cost, no vendor lock-in, no student data leaving campus. This is the entire point for the Ollama track: a Title I school with a $600 Mac Mini gets the same AI-powered guidance as a private school with a $400/hr consultant.

**Open weights for education.** Public schools cannot sign enterprise AI contracts. They can't send student data to the cloud without FERPA review. Gemma makes deployment simple.

**Multilingual at the model level.** FutureProof switches between English, Spanish, and Arabic. Spanish covers ~75% of English-learner students in US schools and Arabic is among the fastest-growing home languages in midwestern Title I districts. Western numerals and canonical English values (BLS, O*NET, CIP/SOC codes, JSON keys) stay consistent across languages so the data layer never breaks. Important decisions should be supported by the language a family is most comfortable speaking.

### Technical Architecture

**Data pipeline.** A Bronze-Silver-Gold pipeline ingests nine datasets (College Scorecard, BLS, O*NET, NCES CIP-SOC crosswalk, BEA Regional Price Parities, IPEDS finance, EADA, Karpathy AI Exposure, Anthropic Economic Index).

**MCP server.** `futureproof_server.py` exposes 9 tools to Gemma: the core school+major career query, occupation detail, O*NET task breakdown, career branch trees, reverse career-to-school search, institutional brand (AURA), regional cost-of-living, cross-state purchasing-power comparison, and national purchasing-power ranking. Each validates typed args, queries Iceberg, and returns structured results.

**Gemma integration depth.** The app wouldn't be possible without Gemma's ability to determine student intent, and most importantly, suggest additional skills to help the student overcome challenges.

**Stack.** FastAPI + React/TypeScript/Vite + Apache Iceberg + DuckDB + Ollama (local) or OpenRouter (cloud). The inference backend switches between Ollama and OpenRouter via one environment variable.

### Evaluation

I ran 215 labeled cases against the highest-leverage Gemma integration points: career intent, the five stat explainers (ERN/ROI/RES/GRW/AURA), and the generated skill pool.

**Headline results on Ollama + `gemma4:e4b`.** Career intent: 100/100 across common majors, niche specialties, typos, conversational input, and nonsense. Stat explainers scored 100% schema validity and 100% correct stat-code identification across 100 runs. Skill pool: 87% of skills were very likely to exist at the named school, 91% were factually accurate, but 4.5% (5/111) flagged as convincing hallucinations. But if the student discovers the hallucination because they *actually* did extra research, Gemma and I did our job.

**Latency on local E4B Gemma is fast enough for interactive use.** Median: stat receipts 1.7-2.5s, skill pool 3.4s, career intent 2.8s. p99 tails reach 12-22s on the largest outputs.

Full methodology, per-surface latency distributions, per-skill fact-check judgments, and the iteration history (including two methodology bugs the eval caught in its own design and I walked back) are in `reports/eval-v3-2026-05-13.md`.

### Challenges and What I Learned

**The CIP-SOC crosswalk is the hardest table in education data.** Mapping "what you study" to "what you become" requires a government crosswalk that was designed for statisticians. Some CIP codes map to 15+ SOC codes. Some map to none. When a student types "pre-med," the crosswalk returns biology-adjacent SOCs but not physician, because becoming a doctor requires post-graduate education the crosswalk doesn't model. When a student types "deaf education," the crosswalk barely knows what to do with it, as it maps to "Special Education." I built Gemma-driven SOC expansion: when intent signals suggest missing occupations, Gemma receives a candidate pool from `occupation_profiles` and uses tool calling to select the missing SOCs, capped at five additions to limit the blast radius of hallucinated picks. Without Gemma, a student would have to know which of 1,949 CIP classifications matches their intent. Gemma is what makes "deaf education," "pre-med," or a student's own words actually work.

**Function calling adherence scales with model size, so the product adapts.** Structured Gemma surfaces on E4B clear the bar reliably through a three-tier resilience path (native → content-JSON → structural re-prompt), but for free-form "Ask the Guide" on E4B I made a deliberate call to leverage the context already available in the prompt instead of chaining live tool calls. The 26B hosted path runs the full live-tool-call chat. Both paths use the same MCP server and the same deterministic Gold-zone scoring; only the open-ended chat composition differs.

**Grounding Gemma in data without letting it hallucinate.** Every Gemma surface receives the student's actual numbers: earnings, debt, boss scores, real dollar figures. A shared voice-contract module enforces strict rules across all services (no stat codes, no game framing), and tests assert forbidden tokens never appear. Gemma still occasionally fabricates school facts. Rare, low-risk hallucination is the tradeoff of not fine-tuning.

**Making federal data resonate for 17-year-olds.** The RPG framing is deliberate. A pentagon stat sheet resonates with students who grew up on Pokemon Go. Boss fights give emotional weight to abstract risks: "Fight AI" with a LOSE outcome lands differently than "82% AI exposure score." Applying skills before rematches forces students to face the work involved, and surfaces questions they didn't know to ask.

### For Every Student

FutureProof didn't tell Olivia what to choose. Who am I to crush dreams? My goal was to show her the road ahead and the effort required to navigate it, and to push her to weigh hard data in her decision. The tool is free, the data is public, and the weights are open. Any school can run this, for any student, to make the most of those 15 minutes with the counselor.
