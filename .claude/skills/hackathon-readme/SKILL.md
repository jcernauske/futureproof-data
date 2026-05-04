---
name: hackathon-readme
description: Generate a world-class README.md for a full-stack web application being submitted to Kaggle's Gemma 4 Good Hackathon (Google DeepMind, deadline May 18, 2026). Use this skill whenever the user asks for a README, a project README, a hackathon submission README, a Gemma 4 README, a Kaggle submission writeup, README boilerplate, README polish, or anything that sounds like documentation for a hackathon code repo — even if they don't say the word "README." Also trigger when a user pastes a project description, repo tree, or pitch and asks for "documentation," "the writeup," "the markdown," or "something a judge will read." This skill produces a single README.md that meets Google's published documentation style guide, follows the structural patterns of flagship Google open-source repos (gemma, recurrentgemma, tensorflow), and answers the four questions a Kaggle judge needs in 60 seconds: what problem, what user, why Gemma 4, and how do I run it.
---

# Hackathon README Builder (Gemma 4 Good Hackathon)

You are producing the README.md for a code repo being submitted to the **Kaggle × Google DeepMind Gemma 4 Good Hackathon** (final deadline May 18, 2026, 23:59 UTC; total prize pool $200K USD across categories). The repo is a full-stack web application (frontend + backend) with Gemma 4 as the AI layer.

The README is one of the highest-leverage artifacts in the submission. It is read by a judge in roughly 60 seconds, then re-opened on a fresh laptop to verify reproducibility. If the README fails either pass, the project is dead even if the code is excellent.

---

## What "world-class" means here

Four jobs, in priority order:

1. **30-second test.** Above the fold (first viewport on github.com), a stranger can name the problem, the user, the stack, find the demo video, and find the live demo.
2. **Reproducibility test.** A teammate clones the repo on a fresh machine and reaches a running app in ≤ 10 minutes following only the README.
3. **Gemma 4 credibility test.** A Google engineer can tell, in one section, that Gemma 4 was used in a non-trivial, intentional way — not as a generic "LLM API" swap.
4. **Google voice test.** Reads in Google's documentation style: second person, active voice, imperative for instructions, present tense, no "please," US English, no marketing puff.

Every section below exists to serve one of those four jobs. Cut anything that doesn't.

---

## Workflow

Follow these steps in order. Don't skip the interview — a generic README is worse than no README.

### Step 1 — Interview the user (do this first, even if they pasted code)

Ask only what you can't infer from context. Batch the questions in a single message. Required answers before drafting:

1. **Project name** and **one-sentence pitch** (you'll rewrite the pitch; you just need their version).
2. **Hackathon track** — one of: Future of Education, Health and Sciences, Digital Equity, Global Resilience, Safety.
3. **The user and the pain** — who is the specific user, in what specific context, with what specific problem? Push back on vague answers like "students" or "anyone." A teacher in a rural classroom with no internet is a user. "Students" is not.
4. **Tech stack** — frontend framework, backend framework, database, deployment target.
5. **Gemma 4 specifics:**
   - Which variant? (E2B, E4B, 26B MoE, 31B Dense)
   - Which inference path? (Ollama, llama.cpp, Transformers, vLLM, Google AI Studio, Kaggle Models, Hugging Face Inference Endpoints)
   - Multimodal? (text only / + image / + audio)
   - Function calling / tool use? If yes, list the tools.
   - Thinking mode on or off?
6. **Demo assets** — do they have (a) a 2-minute video URL, (b) a hosted live demo URL, (c) screenshots? If any are missing, flag it as a submission blocker.
7. **Repo structure** — monorepo or separate frontend/backend repos? Where do the directories live?
8. **License** — default to **Apache 2.0** (matches Gemma 4 itself); only deviate if they have a specific reason.
9. **Team** — names, roles, links (GitHub / LinkedIn).
10. **Hardware floor** — what did they actually test on? (e.g., "M2 Pro 16GB ran E4B at 22 tok/s")

If they don't know an answer, say so in the README ("TBD before submission") rather than inventing one. Inventing details is the most common way these READMEs get caught.

### Step 2 — Draft the README using the template in §"Output template"

Write directly to a file named `README.md`. Don't preview it as a chat reply unless the user explicitly asks for inline preview — they want a file they can drop into the repo.

### Step 3 — Run the editing pass (§"Voice and tone editing pass")

This is the difference between a good README and a Google-tier one. Don't skip it.

### Step 4 — Run the final checklist (§"Submission gate checklist")

Read each item aloud. Anything unchecked is a real risk; tell the user explicitly.

---

## Output template

Use this exact structure. Reorder only with a stated reason. Sections marked **★** are non-negotiable for this hackathon.

```markdown
<h1 align="center">{{ProjectName}}</h1>

<p align="center"><i>{{One-sentence value proposition: who it's for, why it matters, in plain language.}}</i></p>

<p align="center">
  <a href="{{video_url}}"><img alt="Demo video" src="https://img.shields.io/badge/▶-Watch_2_min_demo-red"></a>
  <a href="{{live_demo_url}}"><img alt="Live demo" src="https://img.shields.io/badge/🌐-Live_demo-blue"></a>
  <img alt="License" src="https://img.shields.io/badge/license-Apache_2.0-green">
  <img alt="Built with" src="https://img.shields.io/badge/built_with-Gemma_4-orange">
  <img alt="Hackathon" src="https://img.shields.io/badge/Kaggle-Gemma_4_Good_Hackathon-20BEFF">
</p>

![{{descriptive alt text}}](docs/img/hero.gif)

> Submission to the [Gemma 4 Good Hackathon](https://www.kaggle.com/competitions/gemma-4-good-hackathon) — Track: **{{track_name}}**.

## The problem ★

{{3–6 sentences. Name a specific user in a specific context with a specific pain. Then state what changes for them when they use this project. No "leverage," "empower," "cutting-edge."}}

## Demo ★

- 📺 **2-minute walkthrough:** [{{video_title}}]({{video_url}})
- 🌐 **Live web demo:** [{{live_demo_url}}]({{live_demo_url}})
- 🖼️ **Screenshots:** [`/docs/screenshots`](docs/screenshots/)

{{If full-stack hosting is impractical because of model size, add ONE sentence: "The hosted demo uses recorded model responses; for live Gemma 4 inference, run locally — see Quickstart."}}

## Features

- {{Verb-led, concrete bullet 1}}
- {{Verb-led, concrete bullet 2}}
- {{... 5–8 total. Specifics, not adjectives.}}

## Architecture ★

```mermaid
flowchart LR
  U([User]) -->|HTTPS| FE[{{Frontend}}]
  FE -->|REST /api| BE[{{Backend}}]
  BE -->|HTTP localhost:11434| OL[Ollama Runtime]
  OL -->|loads| G4[(Gemma 4 {{variant}})]
  BE -->|reads/writes| DB[({{database}})]
```

**Why this stack:** {{One paragraph on the privacy/edge/offline/cost reasoning behind running Gemma 4 locally rather than calling a hosted frontier model.}}

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | {{e.g., React 18 + Vite + TypeScript + Tailwind}} |
| Backend | {{e.g., FastAPI 0.110 + Python 3.11}} |
| Model runtime | {{e.g., Ollama 0.x}} |
| Model | {{e.g., gemma4:e4b (4.5B effective params, 128K context)}} |
| Database | {{e.g., SQLite via SQLAlchemy 2.0}} |
| Deployment | {{e.g., Vercel (frontend), Modal (backend + GPU)}} |

## Quickstart ★

### Prerequisites
- Node.js ≥ 20
- Python ≥ 3.11
- [Ollama](https://ollama.com)
- {{disk}} GB free disk for Gemma 4 weights
- {{ram}} GB RAM minimum

### 1. Clone and install
```bash
git clone https://github.com/{{owner}}/{{repo}}.git
cd {{repo}}
{{install_command}}
```

### 2. Pull the Gemma 4 model
```bash
ollama pull {{model_tag}}
```

### 3. Configure environment
```bash
cp .env.example .env
# Edit .env — see Configuration below
```

### 4. Run
```bash
{{run_command}}
```

Open {{local_url}} and you should see the welcome screen within ~10 seconds.

## Configuration

| Variable | Required | Default | Description |
|---|---|---|---|
| `OLLAMA_HOST` | no | `http://localhost:11434` | Ollama HTTP endpoint |
| `MODEL_TAG` | yes | `{{model_tag}}` | Gemma 4 variant to load |
| `DATABASE_URL` | yes | — | Connection string |
| {{...}} | | | |

A complete reference lives in [`.env.example`](.env.example).

## Project structure

```
.
├── frontend/        # {{Frontend description}}
├── backend/         # {{Backend description}}
├── model/           # Gemma 4 prompts, function schemas, evals
├── docs/            # Architecture notes, screenshots, model card
├── scripts/         # Setup, eval, deployment helpers
├── .env.example
├── LICENSE
└── README.md
```

## How Gemma 4 is used ★

- **Variant:** {{variant + rationale: edge constraint, latency target, quality, memory floor}}
- **Inference path:** {{Ollama / Transformers / etc., with version}}
- **Multimodal:** {{text only / + image (visual token budget X) / + audio}}
- **Function calling:** {{N tools registered, JSON schemas in `model/tools/`}}
- **Thinking mode:** {{on / off — and why}}
- **System prompt:** see [`model/prompts/system.md`](model/prompts/system.md)
- **Sampling:** temperature {{T}}, top_p {{P}}, top_k {{K}} ({{rationale, ideally matching Gemma 4 defaults}})
- **Context budget:** typically {{X}}K of the {{128K|256K}} window
- **Measured latency:** {{X}} tok/s on {{hardware}}, p95 round-trip {{Y}} ms

## Model card

**Intended use.** {{1–2 sentences.}}

**Out-of-scope use.** {{1–2 sentences. Be specific about where this should NOT be used.}}

**Inputs / outputs.** {{Modalities, formats, prompt structure.}}

**Limitations.** {{3–5 honest bullets. Hallucinations, latency, language coverage, modality gaps.}}

**Safety mitigations.** {{Input/output filtering, refusal patterns, rate limiting, etc.}}

**Privacy posture.** {{Where data goes. If on-device only, say so explicitly — this is a real differentiator for the hackathon.}}

**Responsible AI.** This project follows Google's [Gemma Prohibited Use Policy](https://ai.google.dev/gemma/prohibited_use_policy) and the [Responsible Generative AI Toolkit](https://ai.google.dev/responsible).

A longer model card lives at [`docs/MODEL_CARD.md`](docs/MODEL_CARD.md).

## Testing

```bash
{{frontend_test_command}}    # frontend tests
{{backend_test_command}}     # backend tests
{{eval_command}}             # model-quality evals
```

{{If no tests exist: state it honestly. "Test coverage is limited to the model evals in `model/evals/` due to hackathon time constraints." Judges respect candor; they punish hidden gaps.}}

## Deployment

{{One paragraph + diagram or link describing the live demo's hosting. If the backend needs a GPU and you couldn't host it publicly, say so explicitly and link to a one-command Docker Compose or Modal/Replicate config that reproduces the deployment.}}

## Roadmap and known limitations

- {{Bullet 1: a specific limitation you preempt}}
- {{Bullet 2: a feature you deferred and why}}
- {{Bullet 3: a known failure mode and the workaround}}

## Team

- **{{Name}}** — {{role}} — [{{handle}}]({{link}})
- {{...}}

## License

Released under the [Apache License 2.0](LICENSE). Gemma 4 is also Apache 2.0; weights remain subject to Google's [Gemma Terms of Use](https://ai.google.dev/gemma/terms) and [Prohibited Use Policy](https://ai.google.dev/gemma/prohibited_use_policy).

## Acknowledgments

Built on [Gemma 4](https://ai.google.dev/gemma) by Google DeepMind. Thanks to [Ollama](https://ollama.com) for the local inference runtime, and to the [Kaggle](https://www.kaggle.com) team for hosting the hackathon.

---

*Hackathon submission. Not an official Google product.*
```

---

## Voice and tone editing pass

After drafting, do a find-and-replace pass over the whole file. Each row is a real pattern that turns up in nearly every first draft.

| Find | Replace with | Why |
|---|---|---|
| `we provide`, `we built`, `our app` | `This project provides`, `Use the …` | Google style is second person, not first person plural |
| `please run`, `please install` | `Run`, `Install` | No "please" in instructions |
| `you'll need to`, `you should`, `you can` | imperative verb (`Install`, `Run`) | Hedging weakens instructions |
| `is configured by`, `gets set` | active voice (`Configure …`) | Passive voice |
| `click here` | descriptive link text (`see the installation guide`) | Accessibility + scannability |
| `simply`, `just`, `easy` | delete | Condescending; nothing is "just" anything |
| `cutting-edge`, `state-of-the-art`, `powerful`, `seamless` | concrete capability | Marketing puff signals AI slop |
| `etc.` | finish the list, or use "such as X, Y, Z" | Vagueness |
| `will save`, `will be available` | present tense (`saves`, `is available`) | Google convention |
| `leverage`, `utilize` | `use` | Verbose synonyms |
| `solution`, `platform`, `ecosystem` | the actual thing it is | Jargon hides clarity |

Two specific Google conventions:
- **`README.md` is all-caps.** Don't rename it.
- **Always use fenced code blocks with language tags** (` ```bash`, ` ```python`), never 4-space indents.

---

## Examples

### Example 1 — Identity sentence

**Bad:** *"Our cutting-edge AI-powered solution leverages Gemma 4 to revolutionize the educational landscape for students worldwide."*

**Good:** *"FutureProof helps high school juniors pick a college major by analyzing their coursework against current labor-market data, running entirely on the student's laptop with Gemma 4."*

The good version names the user (high school juniors), the action (pick a college major), the method (analyze coursework against labor data), and the technical differentiator (runs locally on Gemma 4). No adjectives.

### Example 2 — Quickstart

**Bad:**
> *To get started, you'll first want to make sure you have all the prerequisites installed. Then you can clone the repo and we recommend running our setup script which will handle most of the configuration for you.*

**Good:**
```bash
git clone https://github.com/jeff/futureproof.git
cd futureproof
npm install
ollama pull gemma4:e4b
cp .env.example .env
npm run dev
```
*Open http://localhost:5173.*

The good version is six commands. Imperative. Copy-pasteable. No prose between them. No "we recommend."

### Example 3 — How Gemma 4 is used

**Bad:** *"We use Gemma 4, Google's powerful new AI model, to analyze student inputs and generate personalized recommendations."*

**Good:**
> - **Variant:** `gemma4:e4b` (4.5B effective parameters, 128K context). Chosen over the 26B MoE for sub-second response on a typical student laptop (8 GB RAM minimum).
> - **Inference path:** Ollama 0.5+ via the `/api/chat` endpoint (chat template handled by Ollama).
> - **Function calling:** 4 tools registered — `lookup_major`, `query_bls_outlook`, `compare_salary`, `find_courses`. JSON schemas in [`model/tools/`](model/tools/).
> - **Thinking mode:** off. The use case is conversational and latency-bounded; thinking adds ~3× tokens with no measurable quality lift on this task.
> - **Sampling:** temperature 0.7, top_p 0.95 (Gemma 4 recommended defaults).
> - **Measured:** 22 tok/s on M2 Pro (16 GB), p95 round-trip 1.8 s.

The good version makes specific, falsifiable claims. A judge can verify each one in the code. The bad version makes no claims and signals nothing.

---

## Submission gate checklist

Run this before handing the README to the user. Anything unchecked is a real risk; flag it explicitly.

**Above the fold (first viewport)**
- [ ] H1 with project name
- [ ] One-sentence value proposition
- [ ] Hero screenshot or GIF (≤ 5 MB, in `docs/img/`)
- [ ] Badges: license, hackathon, demo video, live demo
- [ ] 2-minute video link visible without scrolling

**Required sections present**
- [ ] Problem + user + hackathon track named
- [ ] Demo (video + live URL + screenshots)
- [ ] Features (5–8 concrete bullets)
- [ ] Architecture (Mermaid diagram, renders on GitHub)
- [ ] Tech stack table
- [ ] Quickstart (numbered, ≤ 5 commands)
- [ ] Configuration (.env table)
- [ ] How Gemma 4 is used (variant, prompts, tools, thinking mode, latency)
- [ ] Model card / responsible AI block
- [ ] Project structure tree
- [ ] Testing (or honest statement that tests are limited)
- [ ] Roadmap / known limitations
- [ ] Team
- [ ] License (Apache 2.0)
- [ ] Disclaimer line ("Hackathon submission. Not an official Google product.")

**Repo hygiene companions** (these aren't in the README, but the README references them)
- [ ] `LICENSE` file present (Apache 2.0)
- [ ] `.env.example` present, no real secrets
- [ ] `CONTRIBUTING.md` (even one line: "This is a hackathon submission; not accepting external PRs until after judging")
- [ ] `docs/MODEL_CARD.md` for the longer responsible-AI content
- [ ] Video uploaded publicly (YouTube unlisted is fine)
- [ ] Repo set to public

**Voice pass complete**
- [ ] Second person throughout (no "we")
- [ ] Imperative for instructions (no "you'll need to")
- [ ] Active voice
- [ ] No "please," "just," "simply," "easy," "leverage," "cutting-edge"
- [ ] Present tense
- [ ] All links have descriptive text (no "click here")
- [ ] US English

**Truth pass**
- [ ] Every command was actually run today on a fresh checkout
- [ ] Every claimed feature actually works in the demo
- [ ] Hardware floor reflects what was actually tested
- [ ] Latency / tok/s numbers are real, not aspirational

**The 30-second skim test**
- [ ] Read only what fits in viewport 1: can a stranger name the problem, the user, the stack, and find the demo?

**The reproducibility test**
- [ ] Send the README to a teammate cold. Did they reach a running app in ≤ 10 minutes?

---

## Common mistakes to avoid

1. **Burying the user.** Opening with the tech stack instead of the user/problem. Judges read the first paragraph; if it's about the framework, they bounce.
2. **Vague impact claims.** "Empowers communities" / "transforms education" — every submission says this. Replace with a specific user and a specific change.
3. **Skipping the hardware floor.** "Run with Gemma 4" without saying which size or how much RAM is the most common reason a judge can't reproduce.
4. **Treating Gemma 4 as a generic LLM.** If the README would read identically with "GPT-4o" search-and-replaced for "Gemma 4," the project misses the point of the hackathon. Spell out the on-device / privacy / edge / offline reasoning.
5. **Long prose, no structure.** A wall of paragraphs reads as effort but scans as nothing. Tables, bullet lists, numbered steps, fenced code blocks.
6. **Outdated commands.** The single most common reason setup fails. Re-run every command on a clean machine before shipping.
7. **No "limitations" section.** A README that claims everything works is less credible than one that names two things that don't.
8. **Markdown that doesn't render on GitHub.** Test the rendered view, not just the raw markdown. Mermaid diagrams, badge images, and relative links are the usual culprits.
9. **No license, or a non-Apache license.** Gemma 4 is Apache 2.0; deviate only with a real reason.
10. **Inventing details to fill gaps.** If a number is unknown, write "TBD before submission" — don't make it up. Inventing breaks the truth-in-advertising test and judges notice.

---

## Reference: exemplar READMEs to study

If the user wants to see what "great" looks like, point them at these:

| Repo | What to learn |
|---|---|
| `github.com/google-deepmind/gemma` | The canonical Gemma README — brief identity, immediate code snippet, hardware floor, "not an official Google product" disclaimer. |
| `github.com/google-deepmind/recurrentgemma` | Hardware-vs-feature compatibility table. |
| `github.com/google/gemma_pytorch` | Multiple installation paths (Docker / pip / source) cleanly separated. |
| `github.com/google/new-project` | Google's official open-source repo template. |
| `github.com/protocolbuffers/protobuf` | Crisp identity sentence; tight install instructions. |
| `google.github.io/styleguide/docguide/READMEs.html` | The actual Google README rule. |
| `developers.google.com/style/highlights` | The voice and tone one-pager. |
| `huggingface.co/google/gemma-4-E4B` | Gemma 4 model card — source for limitations and ethics phrasing. |

---

## Final note on length

A great hackathon README is 500–1500 lines of markdown. Below 500 it usually skips required sections; above 1500 it usually wasn't edited. If you're past 1500, push deep content into `docs/` and link to it from the README. The README is a router, not an encyclopedia.
