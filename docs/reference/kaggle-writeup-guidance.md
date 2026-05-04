# FutureProof + Gemma 4 Good Hackathon: A Winning Playbook

> *Last updated May 4, 2026 — final submission deadline May 18, 2026 (23:59 UTC). You have ~14 days.*

## TL;DR

- **Win the video, win the hackathon.** The single most predictive factor in the Gemma 3n Impact Challenge (the direct predecessor) was a 2–3 minute story-driven demo video showing a real user with a real problem getting a real result on-device. Treat the video as the deliverable; treat the writeup, repo, and notebook as supporting evidence. Judges may not watch past minute 2–3 of any video — the Gemini 3 sister hackathon explicitly says "if the video is longer than 2 minutes, only the first 2 minutes will be judged."
- **Lean hard into local-first + a named, specific student.** The Future of Education and Ollama prizes both reward "AI where it matters most" — offline, private, on cheap hardware. Generic "AI career chatbot for students" loses. "Aisha, a 17-year-old in a connectivity-limited classroom in [place], gets a personalized career path from FutureProof running entirely on a $300 Chromebook with no internet" wins. The 2025 Ollama prize winner (LENTERA) was literally "offline AI microserver for rural schools running Gemma 3n via Ollama" — that is the exact pattern Google rewards.
- **The de-facto rubric is four buckets, in this priority order: Impact & Vision (~35–40%), Video Pitch & Storytelling (~25–30%), Technical Depth & Execution (~25–30%), Reproducibility/Documentation (~10%).** Hit every bucket explicitly with named section headers in your writeup. Don't make judges hunt.

---

## Key Findings

### 1. What the Gemma 4 Good Hackathon actually is (verified facts)

- **Host/sponsor:** Kaggle × Google DeepMind. Announced April 2, 2026.
- **Total prize pool:** **$200,000** (multiple secondary sources confirm this; the user's $80K figure appears to be a sub-track ceiling, not the full pool — verify on the Kaggle page directly).
- **Deadline:** May 18, 2026, 23:59 UTC.
- **License requirement:** Submissions go out under Apache 2.0; you must use at least one Gemma 4 model (E2B, E4B, 26B MoE, or 31B Dense).
- **Five impact tracks announced:** Future of Education, Health & Sciences, Digital Equity, Global Resilience (Climate & Green Energy), and Safety. Plus **special technology prizes**, including a **dedicated Ollama prize** and an **Unsloth prize** (each historically $10,000 in the Gemma 3n round; Unsloth confirmed $10K again for Gemma 4).
- **Required submission artifacts** (confirmed across multiple sources):
  1. Working demo / public app or runnable prototype
  2. Public code repository (GitHub typical)
  3. Technical write-up on Kaggle explaining how Gemma 4 was used
  4. Short demonstration video showing real-world use

### 2. The official rubric (inferred from the published Kaggle ecosystem)

Kaggle has not published a numerical rubric on the public competition page (the page is JavaScript-rendered and requires login to see full details). However, two strong proxies tell you exactly what judges score:

**Proxy A — The Gemma 3n Impact Challenge (the direct predecessor, same sponsor, same format, same prize structure, ran June–Aug 2025).** Submissions were judged on:
- **Impact & Vision** — does it solve a real problem, who benefits, is the vision inspiring
- **Video Pitch & Storytelling** — engaging, story-driven, "wow factor"
- **Technical Depth & Execution** — does it actually work, is the engineering robust, does it leverage Gemma's unique capabilities (on-device, multimodal, function calling)
- **Reproducibility** — can someone else clone and run it

The Awaaz hackathon repo (a publicly shared 3n submission) explicitly named these four buckets in its README, and Google's own announcement of the 3n winners says they were looking for "a compelling video story and a 'wow' factor demo that shows real-world impact."

**Proxy B — The concurrent Gemini 3 hackathon (Devpost, $100K, same Google DeepMind sponsor, same April–May 2026 cycle) published explicit weights:**
- Impact: **40%**
- Innovation / Wow Factor: **30%**
- Technical Depth & Execution: **30%** (sometimes split as Technical Execution 30% + Presentation 10%)

**Working assumption for FutureProof:** Treat the rubric as roughly **Impact 35–40% / Video & Storytelling 25–30% / Technical Execution 25–30% / Reproducibility 10%**. Build to that.

### 3. Past winners — what they actually had in common

The **eight winners of the Gemma 3n Impact Challenge** (announced Dec 10, 2025; over 600 submissions) shared an unmistakable pattern:

| Project | Track / Prize | Pattern |
|---|---|---|
| **Gemma Vision** (1st + Google AI Edge prize) | Accessibility | AI for the developer's blind brother — phone strapped to chest, controller-driven, MediaPipe LLM Inference API + flutter_gemma |
| **Vite Vere Offline** (2nd) | Cognitive disability | Took an existing Gemini API product offline using Gemma 3n |
| **3VA** (3rd) | AAC for cerebral palsy | Fine-tuned Gemma 3n on a single named user (Eva) with MLX |
| **Sixth Sense for Security Guards** (4th) | Security | YOLO-NAS + Gemma 3n cascade, real perf numbers (16 cameras, 360fps) |
| **Dream Assistant** | Unsloth prize | Personalized fine-tune for one user with speech impairment |
| **LENTERA** | **Ollama prize** | **Offline AI microserver — local WiFi hotspot serving Gemma 3n via Ollama to a rural classroom** |
| **Graph-based LeRobot** | LeRobot prize | Novel pipeline (scanning-time-first), genuine research contribution |
| **My (Jetson) Gemma** | NVIDIA Jetson prize | CPU-GPU hybrid voice interface on Jetson Orin |

**Six common traits of every winner:**
1. **A named human protagonist with a specific disability, geography, or constraint.** Not "students." Not "underserved communities." A named person or a single classroom.
2. **The model runs *on the user's device or local network*** — not a Gradio demo hitting Gemini API. The whole point of Gemma is local; judges are explicitly looking for that.
3. **The demo video opens with the problem, not the tech.** Gemma Vision opens with the brother walking with a cane. better-ed opens with a student speaking an answer aloud.
4. **One unique technical move** — fine-tuning, a novel cascade with a small CV model, an unusual hardware target, etc. Not "we wrapped Gemma in a chatbot."
5. **The README/writeup explicitly enumerates the rubric.** Awaaz's README literally has sections titled "Impact & Vision," "Video Pitch & Storytelling," "Technical Depth & Execution." This is not subtle — winners hand judges the scorecard.
6. **Apache 2.0 license + clean, non-trivially organized repo** with one-command setup (`ollama pull`, `pip install -r`, `python run.py`).

### 4. The Future of Education track specifically

Per the official competition framing, this track wants:
- **Personalized learning experiences** for individual students
- **Tools that support educators** (admin automation, teaching assistance)
- **Solutions that work in low-bandwidth or offline classroom settings**

The bar set by the 3n round (Lentera, better-ed) is **education tools that work without reliable internet**. If FutureProof requires cloud APIs, you will lose this track to someone offering the same idea offline. Since you're already on Ollama locally, you're already aligned — emphasize this in every artifact.

### 5. The Ollama prize specifically

The Ollama prize (~$10K, sponsored by Ollama itself) goes to "the best project that utilizes and showcases the capabilities of [Gemma] running on Ollama." The 2025 winner (LENTERA) won by:
- Running Gemma via `ollama serve` on a cheap edge device (Raspberry Pi-class)
- Broadcasting a local WiFi hotspot so multiple student devices could share one inference server
- Being **genuinely unable to function without Ollama as the local serving layer** — Ollama wasn't a wrapper, it was the architectural keystone

What Ollama (the company) wants: a project where **Ollama is non-substitutable**. If your project would work identically with the OpenAI API, you won't win the Ollama prize. Show:
- Local-first architecture diagram with Ollama as a labeled component
- Cold-start times, tokens/sec on consumer hardware
- A specific Gemma 4 quant you chose and **why** (e.g., `gemma4:e4b-it-q4_K_M` for 8GB RAM laptops)
- Use of Ollama-specific features: model file customization, local function calling, running multiple Gemma 4 sizes for routing (E2B for fast paths, 26B MoE for hard reasoning)

---

## Details

### A. Optimal writeup structure (the 8-section template that mirrors winners)

Submit on Kaggle (Writeups tab) with this exact structure. Aim for **1,500–2,500 words**, heavy on screenshots and short paragraphs. Judges skim.

1. **Hook (2–3 sentences + 1 image)** — A named student, a concrete problem. Example: *"Aisha, 17, lives in [place]. Her school's career counselor sees 800 students. Internet at school cuts out by 2pm. She has been told to 'pick a major' in three weeks and has no idea what jobs even exist for the skills she enjoys. FutureProof is a 100% offline career-guidance counselor that runs on a $400 laptop and gives Aisha a personalized 5-year plan in 4 minutes."*
2. **The Problem (Impact & Vision section)** — Quantify: how many students globally, what's broken about existing tools (cloud-only, expensive, generic, privacy-violating). Cite a stat. Name your beneficiary archetype.
3. **The Solution: FutureProof in 60 seconds** — One paragraph + one architecture diagram + a link to the demo video at the top.
4. **Why Gemma 4 (and why local)** — This is where you score the technical-depth points. Specifically: which Gemma 4 model size, why you chose it (latency/RAM/quality tradeoff with numbers), how you use multimodal/function calling/thinking mode, why a cloud API would be wrong for this user.
5. **Technical Architecture** — System diagram, Ollama as a labeled component, data flow, prompt design, any RAG/fine-tune, function-calling tool list (e.g., `lookup_university`, `compute_career_match`, `save_plan_pdf`). Include real numbers: tokens/sec, RAM footprint, time-to-first-response on a named machine ("MacBook Air M2 8GB" or "Lenovo IdeaPad with 16GB").
6. **Demo & Evaluation** — Embed the YouTube/Loom video. Then: **how do you know it works?** A small evaluation table — e.g., 20 simulated student personas, accuracy of career suggestions reviewed by a school counselor, latency distribution. This is what separates serious entries from "we built a chatbot."
7. **Impact Story & Roadmap** — Who benefits, expected reach, what's next (pilot with X school, NGO partnership). One sentence on safety/limitations (how you handle bad advice, hallucinations, age-appropriate content).
8. **Reproducibility** — Repo link, exact `ollama pull gemma4:...` command, hardware required, license (Apache 2.0), team. End with: "*Built for the Gemma 4 Good Hackathon — Future of Education & Ollama tracks.*"

**Tone:** Accessible-first, technical-second. The judges include marketing/PMM people (Glenn Cameron, Kristen Quan are Google product marketing) — not just ML engineers. Write like a Google blog post, not a NeurIPS paper.

### B. The video — the single highest-leverage artifact

- **Length: 2:30–3:00.** Not longer. The Gemini 3 hackathon caps useful judging at the 2-minute mark; treat 3 minutes as a hard ceiling.
- **Format:** YouTube unlisted or public, 1080p, captioned (accessibility = bonus credibility). Loom is fine but YouTube embeds better in Kaggle writeups.
- **Structure (steal this beat sheet):**
  - 0:00–0:15 — The student's problem in their own (acted/scripted) voice. Show the pain.
  - 0:15–0:30 — "Existing tools fail because [generic / cloud / expensive / English-only]."
  - 0:30–1:45 — **Live screen recording of FutureProof running locally**, with the network *visibly disabled* (turn off WiFi on camera — Gemma Vision did this). Voiceover narration, not text-only.
  - 1:45–2:15 — Architecture flash card (10 seconds): "Gemma 4 E4B via Ollama, 100% on device, 6GB RAM."
  - 2:15–2:45 — A second user persona OR a teacher reaction shot — proves it generalizes.
  - 2:45–3:00 — Tagline + GitHub URL + "Built for Gemma 4 Good Hackathon."
- **Cardinal sins to avoid:** talking-head intro >15s; reading the README aloud; showing terminal output for >10s; showcasing Gemma's general intelligence ("look it can write a poem!") instead of the specific job; demoing on a beefy workstation when the value prop is on-device.

### C. Code/repo standards

- **One-command run.** `git clone && ollama pull gemma4:e4b && pip install -r requirements.txt && python app.py`. If a judge can't run it in 5 minutes, you lose the reproducibility points.
- **Repo layout** (winners follow this nearly identically):
  ```
  /src           # core app
  /notebooks     # one Kaggle-runnable demo notebook
  /assets        # screenshots, architecture.png
  /eval          # eval scripts + results
  README.md      # mirrors the writeup structure
  LICENSE        # Apache 2.0 — required
  requirements.txt
  ```
- **Notebook quality:** Have **one Kaggle notebook** that pulls Gemma 4 from Kaggle Models, runs a canonical inference, and links to the GitHub repo. This is your "technical proof" artifact for judges who want depth. Don't bloat it; one clean end-to-end pass beats five experimental ones.
- **README.md** should literally have section headings: `## Impact & Vision`, `## Video Pitch`, `## Technical Depth & Execution`, `## Reproducibility`. Make scoring trivial for the judge.

### D. Common failure modes (what kills otherwise-good projects)

Based on patterns from past Kaggle hackathons and the Gemma 3n round:

1. **"Generic chatbot" framing.** If your one-line description is "an AI chatbot for X," you lose. Winners describe a *workflow* or *device*, not a chatbot.
2. **Cloud dependency in an "AI for Good" context.** Submitting an offline-themed project that secretly calls a cloud API will get caught by judges looking at the repo. Be ruthless: every API call must be local.
3. **Demo video that's a slideshow, not a demo.** Judges have explicitly said they prioritize "wow factor" working demos. Voice-over over Keynote ≠ demo.
4. **No named user / no specific geography.** "Helps students" is invisible in a pile of 600 entries. "Helps Aisha in [place]" is memorable.
5. **Technical depth without narrative.** A beautiful fine-tune notebook nobody can connect to a real-world payoff scores poorly on Impact (40%).
6. **Narrative without technical depth.** A polished Figma walkthrough with a fake backend is the most common failure mode and gets flagged immediately.
7. **Submitting only to one prize track.** You can submit once and be considered for Main + Future of Education + Ollama. Make sure your writeup explicitly names *all three* tracks you're targeting in the closing line — the Gemma 3n process showed projects winning multiple prizes (Gemma Vision won Main + Google AI Edge).
8. **Last-minute video.** Audio quality and pacing make or break it. Plan **two full days** for video editing alone.
9. **Forgetting Apache 2.0 / license file.** Trivially disqualifying.
10. **No evaluation at all.** Even a small "we tested 20 student personas, here's the table" massively raises perceived rigor.

### E. "AI for Good" / education-specific tactics

- **Get a real third party on camera.** A teacher, counselor, or student saying "this would help me" is worth 10x a feature list. better-ed had their CEO interview students; Gemma Vision featured the developer's brother. This is the single highest-leverage thing you can do this week.
- **Quantify reach.** "There are 1.6B students globally; 300M lack reliable internet" — sourced. Then anchor: "FutureProof targets the connectivity-limited segment." Specific numbers > vague aspiration.
- **Show one classroom pilot, even an informal one.** Hand FutureProof to 5 actual students, record their reactions, screenshot one real career plan it produced. Even tiny field validation beats hypothetical impact every time.
- **Address harm honestly.** "Career advice from an LLM can be wrong. We mitigate by [list of citations / counselor handoff / confidence flags]." Judges working at Google care about responsible AI claims.
- **Multilingual is a force multiplier in education.** Gemma 4 supports 140+ languages. If FutureProof works in one non-English language relevant to your target user, demo that — it differentiates instantly from the wave of English-only US-centric submissions.

### F. Ollama-prize-specific tactics

- **Make Ollama architecturally load-bearing.** Use Ollama's local function-calling support with Gemma 4 (newly first-class in Gemma 4) so students can trigger structured tools — `search_jobs`, `match_skills`, `generate_resume_pdf`. This is exactly the kind of "novel use of Ollama features" the prize rewards.
- **Multi-model routing through Ollama.** Run E2B for fast/cheap interactions, route hard reasoning to 26B MoE (only 4B active params, fast). Show in the writeup: "We use `ollama run gemma4:e2b` for chitchat and `ollama run gemma4:26b-a4b` for the multi-step career planning agent." This is exactly the kind of intelligence-per-watt thinking judges reward.
- **Publish performance numbers on consumer hardware.** Tokens/sec on a MacBook Air, RAM peak, cold-start time. The Ollama team loves benchmarks because it validates their platform.
- **Use a custom Modelfile.** Show you understand Ollama beyond `ollama pull`. A `Modelfile` that sets system prompt, temperature, and any tool definitions specific to FutureProof signals depth.
- **Document the offline test.** A 30-second video clip with airplane mode visibly on. This was a recurring move in 3n winners.

### G. Timeline — final 14 days, day-by-day

**Days T-14 to T-10 (May 4 → May 8): Lock the story and the architecture**
- T-14: Pick the named user persona. Pick the *one* differentiating technical move (function-calling? E2B↔26B routing? a small fine-tune?). Don't keep changing.
- T-13: Write the one-line pitch and the 4-paragraph problem statement. If you can't make a friend understand and care in 60 seconds, the video won't either.
- T-12: Lock architecture diagram. Set up the repo with proper structure + Apache 2.0 license + draft README using the rubric headings.
- T-11 to T-10: Get the core E2E flow working end-to-end on Ollama with Gemma 4. **Working ugly > polished broken.**

**Days T-9 to T-6 (May 9 → May 12): Build polish + evaluation**
- T-9: UI polish + at least one screenshot-worthy moment.
- T-8: Build the eval — 15–20 student personas, run them through, log outputs, get a teacher/counselor friend to sanity-check 5 of them. Capture as a table for the writeup.
- T-7: Test the offline mode (airplane mode) end to end. Test on a second machine.
- T-6: Draft the full Kaggle writeup. Get 2 people unfamiliar with the project to read it and tell you what FutureProof does in one sentence.

**Days T-5 to T-3 (May 13 → May 15): The video**
- T-5: Storyboard the 2:30 video. Write the script, time it.
- T-4: Record screen capture and voice-over. Re-record at least once.
- T-3: Edit, add captions, add the architecture flash card, upload to YouTube as unlisted, get feedback from someone outside the project.

**Days T-2 to T-1 (May 16 → May 17): Final pass + submission**
- T-2: Clean repo. Tag a v1.0 release. Verify one-command setup works on a fresh checkout. Final README pass. Cross-link writeup ↔ GitHub ↔ video.
- T-1 morning: Submit on Kaggle. Don't wait for the deadline day — last-day submission systems get hammered.
- T-1 evening: Check submission preview renders correctly. Check video link, repo link, license, and that you've explicitly named **Main Track + Future of Education + Ollama** in the writeup.

**Day T (May 18, before 23:59 UTC):** Re-verify submission is live. Don't edit unless something is broken.

### H. Submission checklist (pin this)

- [ ] Kaggle writeup posted on the competition's Writeups tab (~1,500–2,500 words, 8 sections above)
- [ ] GitHub repo public, Apache 2.0 LICENSE file present, README mirrors writeup structure
- [ ] One Kaggle notebook that loads Gemma 4 and runs a representative inference, linked from the writeup
- [ ] YouTube video, 2:30–3:00, captioned, embedded in writeup, named "[FutureProof] — Gemma 4 Good Hackathon"
- [ ] Architecture diagram (PNG) embedded in writeup AND in repo `/assets`
- [ ] Three tracks explicitly named in writeup closing: Main Track, Future of Education, Ollama prize
- [ ] Performance numbers stated for at least one named consumer hardware target
- [ ] One named beneficiary persona with a specific geography
- [ ] Evaluation table present (even if small)
- [ ] One-command setup verified on a fresh machine
- [ ] Offline mode tested and shown in video with WiFi visibly disabled
- [ ] Custom Ollama Modelfile in the repo (extra credit for Ollama prize)
- [ ] Function-calling demo somewhere (Gemma 4 native feature — leverage it)
- [ ] License language for any third-party assets in video and repo

---

## Caveats

- **The exact official rubric for Gemma 4 Good is not publicly fetchable from the Kaggle page without a logged-in browser session.** All weight percentages above are inferred from (a) the Gemma 3n Impact Challenge predecessor, (b) the concurrent Gemini 3 hackathon's published rubric (40/30/30), and (c) the explicit framing in Google's announcement ("compelling video story and 'wow' factor demo"). Verify by logging into the Kaggle page and reading the Overview/Rules tabs directly before submission. Both the official rules tab and the overview tab require JavaScript-rendered access this research could not complete.
- **The user's stated $80K prize pool figure is inconsistent with all secondary sources, which say $200K total.** $80K may be the user's track-specific ceiling (e.g., grand prize) or a misremembered number. Verify on the official page.
- **The Future of Education and Ollama track-specific prize amounts** are not separately confirmed in public secondary reporting for Gemma 4 — they're inferred from the Gemma 3n round (Ollama prize was $10K there, Unsloth $10K, and Unsloth has confirmed $10K again for Gemma 4). Treat these as approximate.
- **"FutureProof" as a name** doesn't appear in any past Gemma hackathon writeup, so this is a clean field. But verify nobody else has registered the same name in this round before submitting (search the Writeups tab on May 16).
- **Some sources for this report (Medium articles, blog posts) are commentary by third parties, not official Kaggle/Google communications.** Where possible, the Google blog (blog.google) and the Kaggle competition page itself are the authoritative sources; the Medium and EdTech Hub pieces are corroborating/interpretive. The pattern of winners (LENTERA, Gemma Vision, etc.) is from Google's official Dec 10, 2025 announcement and is reliable.
- **All advice here is calibrated to win prize money, not to maximize technical novelty for its own sake.** A more research-y submission targeting a NeurIPS-style audience would invert some of these priorities (more eval, less video polish). For Kaggle hackathons sponsored by Google product teams, the playbook above is the right one.

**Key URLs for further reading:**
- Competition page: https://www.kaggle.com/competitions/gemma-4-good-hackathon
- Predecessor winners: https://blog.google/innovation-and-ai/technology/developers-tools/developers-changing-lives-with-gemma-3n/
- Gemma 4 model docs (Ollama): https://ollama.com/library/gemma4
- Gemma 4 announcement: https://blog.google/innovation-and-ai/technology/developers-tools/gemma-4/
- Sister hackathon's published rubric (useful proxy): https://gemini3.devpost.com/
- Awaaz (3n submission with rubric-aligned README): https://github.com/abhishekblue/gemma3n-hackathon
- Submission template repo: https://github.com/johnsonhk88/Kaggle-The-Gemma-4-Good-Hackathon
- LENTERA (Ollama prize winner, 3n) writeup: https://www.kaggle.com/competitions/google-gemma-3n-hackathon/writeups/lentera-offline-ai-microserver-for-remote-and-rura
- Gemma Vision (1st place, 3n): https://www.kaggle.com/competitions/google-gemma-3n-hackathon/writeups/gemma-vision

Now stop reading and go shoot the video. That's the bottleneck.