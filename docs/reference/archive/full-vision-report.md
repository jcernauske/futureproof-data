# FutureProof — Full Design Vision Report

**Author:** @fp-design-visionary
**Date:** 2026-04-12
**Status:** For human review
**Governing documents:** PRD v8, Brightpath Design System Proposal, tokens.css, tailwind.config.ts

---

## Preamble: What This Report Is

> **This is the original design vision report — the emotional arc, screen-by-screen intent, and transition design for FutureProof.** For the authoritative design system spec (tokens, component specs, motion values), see **`DESIGN.md`** at the project root. Where this document and DESIGN.md conflict, DESIGN.md wins.

This document describes how the product should *feel* as a complete experience — the emotional arc from first landing to Instagram share, the transitions between screens, the three moments that win the hackathon, and the design system gaps identified during the original vision pass.

---

## 1. Full Emotional Arc

### The Journey From Darkness to Light

FutureProof is a story told in light. The student begins in the dark — literally and emotionally. They do not know what their degree leads to. They do not know what risks they face. The unknown is vast and paralyzing. Over the course of 10 screens, FutureProof illuminates that darkness systematically, and the visual design mirrors this journey through Progressive Illumination.

Here is the emotional arc mapped to a light curve:

```
Light Level
    |
100 |                                              ___________
    |                                         ____/   Branch
 80 |                                   ____/         Tree
    |                              ____/ Reveal
 60 |                        ____/
    |              _________/  Boss fights
 40 |        _____/ Effort     oscillate here
    |   ____/ School           (tension/relief
 20 |  / Profile               creates drama)
    | / Landing
  0 |/___________________________________________________
    Screen: 1    2    3    4    5    6    7    8    9   10
```

**Screen 1 (Landing):** Void darkness. A faint pentagon constellation pulses. One bright CTA. The emotion is cinematic anticipation — the movie is about to start. Light level: 10%.

**Screen 2 (Profile Name):** One step brighter. The student receives a name. The darkness is still dominant, but there is warmth — the emoji animal glows, the name is bold and bright. The emotion is playful ownership. Light level: 20%.

**Screen 3 (School + Major):** The first real input. The student is committing to something. The screen brightens slightly as data enters — school search results glow on selection, Gemma's intent resolution creates a moment of AI-mediated discovery. The emotion is curious anticipation, tinged with the first flutter of "this is getting real." Light level: 30%.

**Screen 4 (Effort + Loans):** An honest reckoning. The sliders are the most emotionally delicate moment in the product. The student confronts: how much can I give? How much will I borrow? The screen must feel compassionate, not clinical. Stat previews shift in real time — the student sees their choices affecting their future before the future is even revealed. Light level: 35%.

**Screen 5 (Career Pick):** The first glimpse of where the degree leads. Careers appear in tiers — Common, Less Common, Stretch. The student picks a destiny. The emotion is discovery combined with agency: "I had no idea these paths existed, and I get to choose." Light level: 40%.

**Screen 6 (Reveal + Stats):** The first emotional peak. Personalized loading builds suspense. Then: Gemma's Take drops as a coaching narrative. The pentagon blooms. Numbers count up. The stat tutorial (first build only) highlights each axis with plain-English explanation. This is the "I can see myself" moment. Light level: 70%.

**Screen 7 (Boss Gauntlet):** The emotional rollercoaster. Light oscillates with each fight — bright on wins, dimmed on losses, amber on draws. The reroll mechanic creates the product's signature interactive moment: the student equips a skill, the fight rescores live, a loss can flip to a win. This is where learning happens. Structural loss is the most honest thing the product says. Next Steps drops the RPG metaphor entirely and gives the student concrete actions. Light level: 40-80% (oscillating).

**Screen 8 (Branch Tree):** The second peak — and the signature moment. The tree extends outward from the career center. Branches glow. Silhouettes at endpoints pulse with possibility. The full viewport becomes a constellation of futures. This is the telescope moment: the fog lifts, and the student sees not one path but dozens. Light level: 90%.

**Screen 9 (Save + Share):** Satisfaction and social anticipation. The Wrapped sequence packages everything into a shareable story. The emotion is pride: "Look what I got." Light level: 80%.

**Screen 10 (Menu):** Command center. Compare builds, explore branches deeper, ask Gemma anything. The emotion shifts from journey to mastery — the student owns their data and can interrogate it freely. Light level: 75%.

### The Three Emotional Valleys

Not every moment is bright. Three moments in the product intentionally bring the student into confrontation with difficult truths:

1. **Effort Slider (Screen 4):** "I'm working two jobs and can barely focus on school." This slider position produces lower ERN. The product does not judge. It shows the math. The design language around this must be warm, compassionate, and absolutely free of shame.

2. **Boss Fight Loss (Screen 7):** The student loses a fight. The screen does not punish. It dims gently. Amber glow replaces green. The narrative explains why. The reroll mechanic offers a path forward. If the student exhausts all skills and still loses, the structural loss message is the most honest thing the product says: "The gap isn't a skill-tree problem. It's structural to this combination."

3. **Risk Comparison (Screen 10):** Two builds side by side. One survives AI but gets crushed by loans. The other is the opposite. The product never declares a winner. It names the tradeoffs and steps back. The student decides which risks they can live with.

These valleys are essential. Without them, the product is a toy. With them, it is a tool that happens to feel like a game.

---

## 2. Screen-by-Screen Vision

### Screen 1: Landing

**The emotion:** Cinematic anticipation. The student should feel like they walked into a dark theater and the lights just dimmed. Something is about to happen.

**Overall composition:** Full viewport height. Vertically centered content on a `bg-void` canvas. The visual hierarchy is: pentagon glow (atmospheric, decorative, draws the eye) above tagline (the thesis statement) above CTA (the single action). Nothing else. No nav, no footer, no sidebar. This is a movie poster, not a dashboard.

**Key interactive moments:** The CTA button is the only interactive element. Its hover state — a soft `shadow-glow-thrive` bloom — should feel like touching something alive. The button press should have physical weight: scale to 0.97, spring back, then trigger the loading state.

**The signature element:** The pentagon glow. Five faint points of light — gold, green, purple, blue, pink — pulsing gently out of phase with each other against the void. It is not a chart. It has no axes, no labels, no data. It is a constellation, a promise of structure to come. When the student eventually sees their stat pentagon on Screen 6, they will recognize the shape and feel: "That's what the landing was hinting at."

**Mobile treatment (375px):** The pentagon scales down to ~150px. The tagline steps down one type tier. The CTA goes full-width with side margins. The vertical rhythm compresses but never crowds. The pentagon glow is the first thing that sacrifices space — it can shrink significantly and still work because it is atmospheric, not informational.

**Video moment:** 2-3 seconds. The demo video opens here. The pentagon pulses. The tagline is visible just long enough to read. Then the presenter clicks the CTA and we are moving. This screen exists in the video to establish mood, not to explain.

**Danger zones:** Making the pentagon too literal (adding labels or grid lines kills the mystery). Making the tagline too long (it needs to land in one breath). Adding any UI chrome (nav, logo, links) that breaks the cinematic full-bleed.

---

### Screen 2: Profile Name

**The emotion:** Playful ownership. The stakes are zero. The charm is maximum. The student receives a name that is theirs — silly, warm, memorable. "You are dancing happy bear" should make them smile.

**Overall composition:** Full viewport height. Centered column. Background steps up to `bg-deep` — Progressive Illumination begins. The visual hierarchy is: "You are" (small, secondary) above the profile name (hero-sized, primary, dominant) above the reroll button (secondary action) above the CTA (primary action) above the returning-user link (tertiary, muted).

**Key interactive moments:**

1. **Name reveal:** The name should not snap into place. It should arrive — scale from 0.9 with a spring-bouncy overshoot, opacity from 0 to 1 over 300ms. The emoji animal renders large, almost as a character portrait. This is the first moment of identity in the product.

2. **Reroll:** The student taps the dice button. The old name crossfades out (150ms), the new name crossfades in (150ms). The emoji might change — a bear becomes a fox becomes a turtle. Each reroll should feel like spinning a slot machine: quick, satisfying, "just one more."

3. **Returning user lookup:** "Already have a name?" is a small text link in `text-muted`. On click, an input field slides down (200ms ease-out). The student types their name, hits "Look up." Three outcomes — found (celebration, auto-navigate), suggestion ("Did you mean steady bold turtle?"), not found (gentle error).

**The signature element:** The emoji animal rendered at oversized scale. The emoji IS the visual identity in the absence of rendered character art. A single emoji at 48-64px with the profile name in Fredoka at display scale creates a surprisingly effective character moment. The student reads "dancing happy bear" and the oversized bear emoji anchors it visually.

**Mobile treatment:** The name may wrap to two lines. The emoji should always stay with the animal word, never orphaned on its own line. The reroll button and CTA stack vertically with generous spacing.

**Video moment:** 3-4 seconds. The name appears. The presenter laughs ("I'm dancing happy bear"). They reroll once. They click "Let's go." Quick, charming, memorable. In the video voiceover: "FutureProof gives you a name. No accounts, no passwords."

**Danger zones:** Making the name too small (it needs to feel like a proclamation, not a label). Making the reroll animation sluggish (it should feel instant and playful). Overcomplicating the returning-user flow (it is a secondary path and should feel like it).

---

### Screen 3: School + Major

**The emotion:** Curious anticipation. "This is getting real." The student is committing to a school and a field of study. The inputs feel weighty but not overwhelming.

**Overall composition:** Single centered column. School search is the hero input — large, prominent, 56px height, search icon. Below it, the major input appears after a school is selected (animated reveal, slide down). Below both inputs, a confirmation card shows what Gemma matched. Background: `bg-deep`, same as Screen 2 — the illumination holds steady during input.

**Key interactive moments:**

1. **School search autocomplete:** As the student types, results filter with 150ms debounce. Each result shows school name, city/state in `text-secondary`. Selection highlights with `accent-info` border and `bg-surface` background. The selected school should feel "locked in" — a subtle state change that signals commitment.

2. **Gemma intent resolution:** The student types free text ("pre-med," "CS," "business"). A "thinking" state appears — perhaps the Gemma insight icon pulsing. Then Gemma's match appears: "Gemma thinks 'pre-med' maps to **Biology (CIP 26.0101)**." Below: a preview of 3-5 career titles this program leads to. The student confirms, clarifies, or picks an alternative. This is a genuine AI moment — the model is doing real work, and the student can see it.

3. **Career preview on confirmation:** Once the student confirms the match, a brief preview of career paths fades in. Career titles in pills, each with a tiny stat hint. This is the first taste of "where does this degree lead?" — it builds anticipation for Screen 5.

**The signature element:** The Gemma intent resolution moment. Most career tools have a dropdown. FutureProof has an AI that understands "I want to do something with money stuff" and maps it to Finance. The presentation of this match — the audit, the career previews, the confirm/clarify flow — is a demo-worthy AI showcase. The thinking state and the match reveal should feel intelligent, not mechanical.

**Mobile treatment:** Single column, full-width inputs. The career preview pills may stack vertically instead of horizontally. The Gemma match card gets generous vertical space.

**Video moment:** 10-15 seconds. The presenter types "ISU" — autocomplete shows Illinois State University — selects it. Types "business." Gemma thinks for a beat. "Gemma thinks 'business' maps to Business Administration. This would show you careers like: Financial Analyst, Marketing Manager, Management Consultant." Confirms. This demonstrates the AI doing real work.

**Danger zones:** Making the Gemma thinking state too long without feedback (the student should never wonder if the app froze). Making the audit rejection too harsh on joke inputs (firm but not condescending). Showing too many career previews and overwhelming the student before they have even picked a career.

---

### Screen 4: Effort + Loans

**The emotion:** Honest self-reflection with compassion. This screen asks: "How much can you give? How much will you borrow?" These are deeply personal questions. The design must be warm, never judgmental.

**Overall composition:** Centered column. Two slider sections stacked vertically, each with its own question, slider, and label set. Below both sliders, a live stat preview panel shows ERN and ROI adjusting in real time as sliders move. Background: `bg-deep`, possibly with a very subtle warm gradient overlay to signal that input is happening.

**Key interactive moments:**

1. **Effort slider movement:** Three discrete positions (not continuous — the PRD specifies three levels, not a spectrum). As the student moves between positions, ERN adjusts. The stat preview below updates smoothly with counting animation. The labels — "Working + school," "Balanced," "All-in" — are plain and respectful.

2. **Loan slider movement:** Five discrete positions (0%, 25%, 50%, 75%, 100%). As the student moves, ROI adjusts. The loan slider at 100% should feel consequential but not alarming — the number changes, the student sees the impact, and they internalize it.

3. **Live stat preview:** A miniature pentagon preview and numeric stat values update in real time as sliders move. The student sees their choices reshaping their future before the future is revealed. This is where agency lives.

**The signature element:** The wording. "How much time will you have to focus on school?" is carefully chosen — it is about time, not ability or desire. The loan question is about coverage, not burden. Every label, every position name, every description must pass the compassion test: would a student working two jobs to support their family feel respected reading this? If not, rewrite it.

**Mobile treatment:** Sliders stack vertically (they likely do on desktop too). The stat preview panel may simplify to just ERN and ROI numbers rather than a full mini-pentagon. Touch targets on slider thumbs must be minimum 44px.

**Video moment:** 5-8 seconds. Quick. The presenter adjusts effort to "All-in," shows ERN going up. Adjusts loans to 100%, shows ROI dropping. "Your choices here change everything. Watch the numbers." Then "Spec my build" click. This screen demonstrates that FutureProof is personalized, not generic.

**Danger zones:** Making the slider aesthetically dominant over the question text (the question is more important than the widget). Using financial jargon ("debt-to-earnings ratio") instead of plain language. Making the 25th-percentile effort position feel like a failure.

---

### Screen 5: Career Pick

**The emotion:** Discovery and agency. The student sees — for the first time — where their degree actually leads. Careers they did not know existed appear in the "Less Common" and "Stretch" tiers. They get to choose.

**Overall composition:** Centered column. Three expandable sections: Common, Less Common, Stretch. Each section header shows the tier name and count. Individual careers are cards or rows showing occupation title, a hint of salary range (Space Mono), and perhaps the dominant stat for that career. The student taps one to select it. Background stays at `bg-deep`.

**Key interactive moments:**

1. **Tier expansion:** Common tier is expanded by default. Less Common and Stretch are collapsed. Expanding a tier should feel like opening a door — slide down with spring-smooth, stagger children 50ms.

2. **Career selection:** Tapping a career highlights it with `accent-thrive` border and glow. A brief preview — perhaps the top 2-3 stats or a one-line description — helps the student decide. Only one career can be selected at a time.

3. **Stretch tier labeling:** Stretch paths need a subtle indicator that they are possible but less typical. Perhaps a small icon or tag. Not discouraging — exciting. "These paths exist if you chase them."

**The signature element:** The moment a student opens the "Less Common" tier and discovers a career they did not know was possible from their major. A Marketing student seeing "User Experience Designer" or a Biology student seeing "Patent Agent." The tiering is Gemma's insight — the AI is surfacing non-obvious career paths, and the design must make those discoveries feel exciting, not buried.

**Mobile treatment:** Full-width cards. Each career row has generous touch targets. The tier sections are accordion-style — only one expanded at a time on small viewports.

**Video moment:** 3-5 seconds. Show the tiers briefly. The presenter opens "Less Common," finds an interesting career, taps it. "Gemma groups your careers into tiers. Common paths, less obvious ones, and stretch goals. Pick the one you want to build around."

**Danger zones:** Making the career list feel like a spreadsheet (it needs the card treatment — bg-mid, rounded corners, gentle shadows). Showing too much data per career at this stage (salary, stats, and description is too much — one or two signals, not five). Making Stretch feel discouraging.

---

### Screen 6: Reveal + Stats

**The emotion:** Awe and pride. "That's my future. Those are my numbers." This is the first major emotional peak.

**Overall composition:** Full viewport experience. The screen unfolds in sequence:

1. Personalized loading: "Specing dancing happy bear..." with the student's actual profile name. Not a spinner — a narrative loading state that uses the student's identity.

2. Gemma's Take: A 4-6 sentence coaching narrative in a distinct card. This leads the reveal — the student reads the story before seeing the numbers. The narrative is warm, specific, and grounded. It references their actual school, major, and career.

3. Pentagon radar chart: The five-stat pentagon animates from center outward. Each axis extends with spring-smooth, staggered 100ms. Stat numbers count up simultaneously. The pentagon is the signature visual — 280px+ diameter on desktop, centered, with stat labels at each vertex.

4. Stat tutorial (first build only): A guided overlay that highlights each stat one at a time. Highlight, explain in plain English, next. Five beats. Then the overlay fades and the full pentagon is visible. Subsequent builds skip the tutorial. A persistent "?" icon on each stat provides the explanation on tap.

5. Career title and key data: Occupation title in Fredoka heading. Median salary in Space Mono data-large. The data is prominent — this is the first hard number the student sees.

**Key interactive moments:**

1. **Pentagon animation:** The polygon draws from center outward. Each axis line extends, colored by its stat. Vertex dots appear with spring-bouncy at the endpoints. Numbers count from 0 to final value. This animation is the money shot for the video.

2. **Stat tutorial taps:** On first build, the student taps through five guided explanations. Each tap highlights the next stat, dims the others, shows a plain-English card. The rhythm should feel like a teacher pointing at a diagram: "This one means... and this one means..."

3. **"?" icons on stats:** Persistent on every build. Tap to see the stat explanation plus the receipt (raw data inputs, thresholds, sources). The receipt is the provenance layer — but on this screen, the explanation comes first, the receipt is secondary and collapsible.

**The signature element:** The pentagon bloom animation. The moment the five axes extend outward and the stat numbers count up is the single most important animation in the product. It must be polished to demo-video quality. The spring physics, the stagger timing, the glow at each vertex — every millisecond matters.

**Mobile treatment:** Pentagon scales to ~200px. Stat labels may need to be abbreviated (ERN instead of "Earning Power"). Gemma's Take card becomes full-width. The tutorial overlay needs careful mobile treatment — the highlight area and explanation text must not overlap on small viewports.

**Video moment:** 15-20 seconds. This is the longest screen in the video. Show the personalized loading. Gemma's Take appears — read a sentence aloud. The pentagon blooms. Numbers count up. On first build, show one or two stat tutorial beats. "FutureProof explains every number in plain English. And every number comes from public data."

**Danger zones:** Making the personalized loading too slow (it should feel like anticipation, not waiting — 2-3 seconds maximum before content appears). Making Gemma's Take too long (4-6 sentences is the ceiling). Making the pentagon too small (it is the signature visual — give it room to breathe). Making the stat tutorial feel like a quiz (it is a gift of understanding, not a test).

---

### Screen 7: Boss Gauntlet

**The emotion:** Tension, excitement, humor, and — at its deepest — honest confrontation with risk. The gauntlet is the reality check wrapped in game language.

**Overall composition:** One boss at a time, full viewport. Each boss fight is a self-contained mini-scene. The background shifts to the boss's signature color at very low opacity (4-8%) over `bg-void`. The emoji boss icon renders large and centered. Stats being tested are highlighted. A calculating beat builds suspense. Then: result.

The five fights plus Final Boss run sequentially. Between fights: a brief transition (300-400ms) that maintains momentum. The gauntlet should feel like a gauntlet — rapid, sequential, building toward the composite verdict.

After the gauntlet: Next Steps. The RPG metaphor drops entirely. Gemma produces a concrete, data-grounded action checklist. Four sections of specific items the student can take to a meeting with a counselor or parent.

**Key interactive moments:**

1. **Boss entrance:** The emoji icon scales in from 0.8 with spring-bouncy. The boss name types in with Fredoka impact. The stats being tested highlight and pulse. A 600-800ms calculating beat (shimmer on stat values) builds suspense.

2. **Win state:** Green burst. The boss emoji shrinks with a comical deflation. "WIN" appears in accent-thrive. A brief one-line narrative from Gemma explains why.

3. **Loss state:** This is the most critical design moment. The screen does NOT punish. It dims gently — a deeper navy with a soft amber glow from behind the boss. The boss emoji grows slightly (it is smug, not terrifying). The narrative explains why — grounded in data, compassionate in tone. Then: the reroll offer.

4. **Reroll flow:** The signature interactive feature. On loss or draw, 3-5 skill options appear. Each shows a title, a one-line rationale, and machine-readable stat deltas ("+2 RES"). The student equips skills. The fight rescores live — the result indicator animates from LOSE to DRAW or WIN. The "aha" moment: "If I add a Data Analytics Minor, I beat the AI." Skills are build-wide, so equipping one here carries forward.

5. **Structural loss:** When all skills are exhausted and the result has not improved, the structural loss message appears. This is not a failure state — it is the most important signal the product gives. The design should feel contemplative: amber tones, generous whitespace, the message in Nunito at body size (not display — not shouting). "The gap isn't a skill-tree problem. It's structural."

6. **Next Steps checklist:** After the gauntlet, a new section slides in. No boss icons, no game language. A clean, organized checklist of concrete actions. "1. Meet with your ISU Business advisor about adding a data analytics minor. 2. Research the CFA certification timeline..." Each item references something specific from the student's data.

**The signature element:** The reroll mechanic. The moment a student equips a skill and watches LOSE flip to WIN is the coaching moment that makes FutureProof more than a data viewer. The animation of this flip — the red result indicator crossfading to green, the stat delta applying visually, the boss deflating — must feel satisfying and earned.

**Mobile treatment:** Each boss fight is already one-at-a-time, which works perfectly on mobile. The reroll skill options may need to be scrollable if there are 5. Touch targets on skill equip buttons must be generous (minimum 44px height).

**Video moment:** 20-30 seconds. The gauntlet gets significant video time because it is the most dynamic sequence. Show 2-3 fights quickly (wins are fast). Show one loss in detail: the reroll options appear, the presenter equips a skill, the fight flips from LOSE to WIN. Show one structural loss: "Some weaknesses you can fix. Some you can't." Then the Next Steps checklist: "After the game, FutureProof drops the metaphor and tells you exactly what to do."

**Danger zones:** Making losses feel punishing instead of instructive (amber and contemplative, never red and harsh). Making the reroll options feel random or generic (each skill must reference the student's actual career — "Data Analytics Minor" for a Business major, not "Generic Skill #3"). Making the structural loss feel like a dead end instead of a fork (it should make the student think about trying a different build). Making the Next Steps feel like an afterthought (it is the deliverable).

---

### Screen 8: Branch Tree

**The emotion:** AWE. This is the telescope moment. The student has been looking at one career. Now the fog lifts and they see the entire landscape of where that career leads over decades.

**Overall composition:** Full viewport. Horizontal tree growing left to right. The selected career sits at the left edge as the root node — not a rendered character, but the career title with the profile emoji and a warm glow emanating outward. Branch lines extend rightward as smooth bezier curves. Nodes along the branches represent career progressions. Endpoint nodes at the right edge represent terminal careers 2-3 levels deep.

This screen breaks the centered-column layout used by every other screen. The tree needs the full width. On desktop at 1440px, the tree should spread across the entire viewport — this is the one moment where the product goes cinematic-wide.

**Key interactive moments:**

1. **Tree reveal animation:** The most important animation in the entire product. Empty viewport. The root node appears with a warm glow. Then branch lines draw outward — organic easing, fast at first, gently decelerating. Branch label nodes pop in at fork points with spring-bouncy (staggered 100ms). Career nodes appear along the branches. Endpoint nodes fade in at terminal positions with a brief pulse of ambient glow. Total: ~3.5 seconds from empty to full tree. This is the gasp.

2. **Branch exploration:** Hovering a branch brightens its line and nodes, dims others to ~30% opacity. Clicking an endpoint node opens a detail panel (right side on desktop, bottom sheet on tablet/mobile) showing: branch path description, full stat pentagon for the endpoint career, boss fight results recalculated for this branch, and skill/unlock requirements. Clicking another endpoint crossfades the panel content.

3. **Branch lines:** Not straight lines. Smooth bezier curves with a 2px stroke, gradient-colored from the root glow to the endpoint's dominant stat color. Subtle animated particles flowing along the lines at low density (2-3 per branch, slow drift). On selection: the branch line thickens to 3px and glows with `shadow-glow-thrive`. This creates the sense that energy is flowing along career paths.

**The signature element:** The reveal animation. Full stop. This is the moment that wins the hackathon. A 1440px viewport filled with a glowing career tree — branches extending, nodes popping, particles drifting — is the image that judges will remember. The tree must be simultaneously beautiful (cinematic, atmospheric) and informational (tap any node, get real data). Both qualities must coexist.

**Mobile treatment (375px):** The horizontal tree does not fit. On mobile, the tree collapses into a vertical list of branches, each expandable. The list view shows branch direction names ("Stay Technical," "Go Management," "Pivot Lateral") as expandable cards. Tapping a direction reveals the career progression nodes as a vertical timeline. Less cinematic, fully functional. The demo video uses desktop — the mobile view is for the student on their phone after seeing a friend's Wrapped story.

**Video moment:** 20-30 seconds. The tree reveal is the climactic moment of the video. The presenter clicks "See your branches." The viewport is dark. The career node appears. Then the branches grow — fast, organic, spreading across the full width. The presenter pauses. "A degree isn't a destination. It's a starting position." They click a management branch. A detail panel slides in — new pentagon, new stats. "Every branch leads somewhere different. See where your path goes." This is the money shot. The tree fills the screen. The viewer gasps.

**Danger zones:** Making the tree too small or cramped (it needs full viewport width, no max-width constraint). Making the node layout algorithmic-looking (the bezier curves and staggered reveals create organic feel — a rigid grid would kill it). Making the detail panel too data-dense (pentagon + key stats + one narrative sentence, not a full report). Letting the animation run too long (3.5 seconds is the sweet spot — beyond 5 seconds, anticipation becomes impatience). Making the mobile fallback feel like a punishment (the list view should still feel considered, with good typography and spacing).

---

### Screen 9: Save + Share

**The emotion:** Satisfaction and social anticipation. The build is complete. The student has explored their future. Now they save it and share it.

**Overall composition:** Two sections. Top: save section with a build name (editable, with a fun default like "Build #1: Financial Analyst") and a save button. Below: the Wrapped story experience — a vertical phone-frame mockup showing the current Wrapped frame, with dots/indicators for the full sequence. Share and download buttons prominent.

**Key interactive moments:**

1. **Save:** Simple, satisfying. The save button animates briefly on success (checkmark replaces text, then fades back). The build appears in a save-slot list below — styled like RPG save files (build name, school, major, date, mini emoji).

2. **Wrapped preview:** The student sees their Wrapped story in a phone-shaped frame (9:16 aspect ratio). They can tap through the frames — each frame shows a different aspect of their build. The preview feels like looking at their own Instagram Story before posting.

3. **Download/Share:** Primary action. Download renders the frame sequence as PNGs. Share (if the platform supports it) triggers the native share sheet.

**The signature element:** The Wrapped preview in the phone frame. Seeing your build data packaged as a social story — "Steady Bold Turtle just speced ISU Business" with a glowing pentagon — triggers the "I want to show this to people" impulse. The phone frame is key: it signals "this is ready for social media" without the student having to imagine it.

**Mobile treatment:** On mobile, the phone frame preview is unnecessary — the student IS on their phone. The Wrapped frames render at full width. Download buttons are prominent. The save section stacks above the share section.

**Video moment:** 5-8 seconds. Quick. "Save your build, share your story." Show the Wrapped preview. Click download. "What name did you get?"

**Danger zones:** Making the save flow feel like enterprise software (it should feel like saving a game — quick, satisfying, with a hint of personality). Making the Wrapped frames too data-dense (each frame should be one idea, beautifully presented, not a data dump). Making the download slow or unreliable (the Puppeteer pipeline must be pre-warmed).

---

### Screen 10: Menu

**The emotion:** Mastery and open-ended exploration. The student has completed the core loop. Now they own their data and can interrogate it freely.

**Overall composition:** A hub with clear navigation tiles or cards. Four primary actions: Compare builds (if 2+ builds exist), Explore branches deeper, Ask Gemma, Create new build. Secondary: Download report (if built). The layout is a grid of large, inviting cards — each with an icon, title, and one-line description. Background: `bg-deep`.

**Key interactive moments:**

1. **Compare builds:** Opens the risk comparison screen. Two or three builds side by side. Pentagon overlays. Boss scorecard comparison. Gemma tradeoff summary. The compare never declares a winner — it names the tradeoffs.

2. **Ask Gemma:** Opens a chat panel. Full build context loaded. Multi-turn conversation. The student can ask anything: "What internships should I look for?" "What if I add a data science minor?" The chat panel has the Gemma insight styling — `accent-insight` border, Gemma's responses in a slightly different card background.

3. **New build:** Returns to Screen 3 (School + Major) with the same profile name. The student builds a second career to compare against the first.

**The signature element:** The Ask Gemma chat. This is the 10th Gemma integration surface and a strong demo moment. The student has a real conversation with an AI that knows everything about their build — their school, their major, their stats, their boss fight results, their branches. It is the culmination of the AI showcase.

**Mobile treatment:** The menu tiles stack vertically as full-width cards. The chat panel becomes a full-screen view.

**Video moment:** 5-10 seconds. Show the compare screen briefly — two builds, different risk profiles. "Build A survives AI but gets crushed by loans. Build B is the opposite. Which risk can you live with?" Then briefly show Ask Gemma: "And you can ask Gemma anything about your build."

**Danger zones:** Making the menu feel like a settings page (it should feel like a command center — RPG hub energy). Making the compare too data-dense (risk profiles and tradeoff narrative, not a spreadsheet). Making Ask Gemma feel like a chatbot bolted on (it needs the full build context visible in the UI, not just behind the scenes).

---

## 3. Transition Design

### Page-Level Transitions

Every screen transition follows the same language:

- **Exiting screen:** Fades out (opacity 1 to 0, 200ms ease-out) with a subtle slide upward (translateY 0 to -10px). The screen lifts away.
- **Entering screen:** Fades in (opacity 0 to 1, 300ms ease-out) with a subtle slide upward (translateY 20px to 0). The new screen rises into place.
- **Overlap:** No overlap. The exit completes before the entry begins. Total transition: ~500ms. Fast enough to feel responsive, slow enough to feel intentional.

**Exception: Screen 6 (Reveal) entry.** The reveal screen does NOT use the standard transition. Instead, it uses the personalized loading state as its entry: the loading message appears immediately, the previous screen has already exited, and the reveal unfolds from the loading state. The transition *is* the loading.

**Exception: Screen 8 (Branch Tree) entry.** The tree screen enters with a longer, more dramatic transition. The viewport goes to `bg-void` for 300ms (pure darkness), then the tree reveal animation begins. The darkness is the "curtain opening."

### Background Color Progression

Progressive Illumination is expressed through background tier changes:

| Screen | Background | Why |
|--------|-----------|-----|
| 1 (Landing) | `bg-void` | Deepest dark. The unknown. |
| 2 (Profile) | `bg-deep` | One step lighter. Identity claimed. |
| 3 (School) | `bg-deep` | Holds steady during input. |
| 4 (Effort) | `bg-deep` with warm gradient | Subtle warmth during self-reflection. |
| 5 (Career Pick) | `bg-deep` | Holds steady. Data visible. |
| 6 (Reveal) | `bg-deep` with radial glow from pentagon | Bursts during the reveal. |
| 7 (Gauntlet) | `bg-void` + boss color wash | Returns to darkness for tension. |
| 8 (Branch Tree) | `bg-void` with radial from center | The tree illuminates the void. |
| 9 (Save + Share) | `bg-deep` | Warm and settled. |
| 10 (Menu) | `bg-deep` | Command center. Comfortable. |

The background is not decorative — it is narrative. The shift from `bg-void` to `bg-deep` between Screen 1 and Screen 2 is the first act of illumination. The return to `bg-void` for the gauntlet and branch tree is intentional: darkness for drama.

### Element Continuity

Three elements persist across screens:

1. **Profile name + emoji:** Appears in a fixed header/bar starting from Screen 3 onward (after the profile is established). Small, unobtrusive, `text-muted` Nunito with the emoji. Anchors identity throughout.

2. **Pentagon shape:** The pentagon glow on Screen 1 echoes the stat pentagon on Screen 6, which echoes the pentagon in the compare screen and the Wrapped frames. The shape becomes a visual signature — the student learns to recognize it.

3. **Background progression:** The background tier is the ambient thread. It never jumps — it steps smoothly between tiers with 300ms color transitions.

### Loading States

All loading states are personalized:

- "Specing dancing happy bear..." (career build computation)
- "Asking Gemma about your Marketing path..." (Gemma calls)
- "Mapping your branches..." (branch tree computation)

The loading state is never a spinner. It is a message in Nunito at body size, `text-secondary`, with the student's profile name embedded. A subtle pulsing animation (opacity 0.6 to 1.0, 1.5s cycle) indicates activity. Below the message: a very understated progress indication — not a bar, but perhaps three dots pulsing in sequence.

### "Moment of Truth" Transitions

Three transitions in the product carry special weight:

1. **CTA click on Landing to Name Reveal (Screen 1 to 2):** The CTA button animates (scale press, loading state), then the landing fades out and the profile name fades in with the spring-bouncy entrance. The student crosses from anonymous to named.

2. **"Spec my build" to Reveal (Screen 4 to 6, through Screen 5):** After the student picks a career (Screen 5), the personalized loading state is the bridge. "Specing dancing happy bear..." The computation happens behind this screen. Then Gemma's Take appears, followed by the pentagon bloom. The transition from loading to reveal should feel like a curtain rising.

3. **Boss fight loss to Reroll (Screen 7, internal):** The loss state dims the screen. The reroll skill options slide up from below. The student equips a skill. The fight rescores. The result indicator crossfades from red (LOSE) to yellow (DRAW) or green (WIN). This is not a screen transition — it is a state transition within the gauntlet — but it must be the most satisfying animation in the product.

---

## 4. The Three Signature Moments

These are the three moments that must be extraordinary. They are the moments judges remember, the moments students screenshot, the moments that make the demo video. If these three moments are polished to perfection, the rest of the product can be competent and the product will still be exceptional.

### Signature Moment 1: The Pentagon Bloom (Screen 6)

**What happens:** The student has been through input screens. They have picked a school, a major, an effort level, a loan percentage, a career. They have read Gemma's Take. Now the pentagon appears. Five axes extend outward from center, each colored by its stat. Numbers count from 0 to their final values. The shape is unique to this student's build — no two pentagons look the same.

**What it feels like:** Discovery and ownership. "Those are MY numbers." The counting animation creates emotional investment — the student watches each number climb and roots for it. A high ERN feels like a win. A low RES feels like a warning. The pentagon is simultaneously beautiful and informational.

**Why it matters:** The pentagon is the visual metaphor of the entire product. Five data-backed dimensions of a career, rendered as a shape. It appears on Screen 1 as a glow, on Screen 6 as a reveal, on Screen 8 in branch endpoints, on Screen 10 in comparisons, and on Wrapped frames for sharing. It is the logo of the student's build.

**What would ruin it:** Making the animation too fast (the counting needs to breathe — 800ms minimum). Making the pentagon too small (it needs 280px+ on desktop). Adding too much around it (give the pentagon a moment alone before surrounding it with data). Using linear animation instead of spring physics (linear counting feels robotic; spring-bouncy counting feels alive).

### Signature Moment 2: The Reroll Flip (Screen 7)

**What happens:** The student loses a boss fight. The screen is dimmed. Amber glow. Then: skill options appear. The student reads them — "Data Analytics Minor: RES +2." They equip one. The fight rescores. The result indicator animates from LOSE (amber) to WIN (green). The boss emoji deflates. The student feels: "I can fix this."

**What it feels like:** Empowerment through understanding. The reroll is not magic — it is education. The student learns that adding a data analytics minor makes them more resilient to AI automation. The stat delta is the mechanism. The emotional flip — from loss to win — is the reward. Together, they create a coaching moment disguised as a game mechanic.

**Why it matters:** This is the interaction that makes FutureProof more than a data viewer. Every other career tool shows you a number and leaves you alone with it. FutureProof shows you a number, challenges you with a boss fight, and then — when you lose — teaches you how to improve. The reroll is where the RPG metaphor earns its keep.

**What would ruin it:** Making the skill options feel generic ("Improve your skills" instead of "Data Analytics Minor"). Making the result flip too subtle (the crossfade from LOSE to WIN needs to be visually dramatic — color change, boss reaction, celebration particle). Making the structural loss feel like the same experience as a rerollable loss (structural loss is different in kind, not degree — it needs its own visual treatment).

### Signature Moment 3: The Branch Tree Reveal (Screen 8)

**What happens:** The viewport is dark. The student's career sits at the left edge with a warm glow. Then branches begin extending rightward — bezier curves drawing themselves across the screen. Fork labels pop in. Career nodes appear along the paths. Endpoint silhouettes fade in at the terminals. The full tree fills a 1440px viewport in 3.5 seconds. It is a constellation of futures.

**What it feels like:** Awe and possibility. The student has been thinking about one career. Now they see fifteen, twenty possible futures branching from that one starting point. A Financial Analyst can become a Quant, a Portfolio Manager, a CFO, a Strategy Director. Each branch carries its own stats, its own boss fights, its own risks. The student realizes: "My degree is not a destination. It is a starting position with many possible destinations."

**Why it matters:** The branch tree is the product. It is the answer to the question FutureProof exists to answer: "Where does this degree actually lead?" Everything before the tree — the profile name, the school search, the sliders, the stat reveal, the boss fights — is preamble. The tree is the payoff. If the tree is extraordinary, the product is extraordinary.

**What would ruin it:** Showing the tree all at once (the reveal animation IS the magic — a static tree is just a diagram). Making the branches too short (the tree needs visual spread — short stubby branches feel unexplored). Making the endpoint data too sparse (each node needs real stats when tapped — the data must be as rich as the aesthetics). Making the tree feel like an org chart (bezier curves, particle flow, glow, and staggered animation are what make it feel alive rather than corporate).

---

## 5. Design System Gaps

After reviewing `tokens.css`, `tailwind.config.ts`, and the design system proposal against the full product scope, the following gaps need to be closed.

### 5.1 Animation Tokens

The current `tokens.css` has three CSS transition values (`--transition-fast`, `--transition-normal`, `--transition-slow`). The design system proposal defines four spring configs. But the implemented token file has no animation tokens beyond CSS transitions. This is the largest gap.

**Proposed: `frontend/src/lib/motion.ts`** (Framer Motion spring configs as exported constants)

| Token Name | Config | Usage |
|-----------|--------|-------|
| `springBouncy` | `{ stiffness: 300, damping: 20 }` | Character reveals, boss entrance, stat counters, branch node activation, reroll flip |
| `springSmooth` | `{ stiffness: 200, damping: 25 }` | Page transitions, card entrances, panel expansions, pentagon axis extension |
| `springGentle` | `{ stiffness: 150, damping: 30 }` | Background shifts, ambient glow, branch tree initial render |
| `springSnappy` | `{ stiffness: 400, damping: 25 }` | Button press, toggle, slider thumb, micro-interactions |

**Proposed: Stagger and duration constants**

| Token Name | Value | Usage |
|-----------|-------|-------|
| `staggerChildren` | `50` (ms) | Default stagger for list items, stat bars |
| `staggerFast` | `30` (ms) | Rapid sequences like skill pills |
| `staggerSlow` | `100` (ms) | Branch nodes, pentagon vertices |
| `durationCount` | `800` (ms) | Stat number counting animation |
| `durationReveal` | `3500` (ms) | Branch tree full reveal |
| `durationBossBeat` | `600` (ms) | Boss fight calculating suspense |

### 5.2 State Tokens

The current system has no tokens for interactive states beyond hover shadows.

**Proposed additions to `tokens.css`:**

| Token | Value | Usage |
|-------|-------|-------|
| `--color-state-loading` | `rgba(184, 169, 232, 0.15)` | Loading state background wash (insight-tinted) |
| `--color-state-success` | `rgba(125, 212, 163, 0.15)` | Success flash background |
| `--color-state-error` | `rgba(244, 169, 126, 0.15)` | Error state background |
| `--color-state-disabled` | `rgba(138, 133, 149, 0.3)` | Disabled element overlay |
| `--color-state-active` | `rgba(125, 212, 163, 0.1)` | Active/selected element background |
| `--color-focus-ring` | `rgba(123, 184, 224, 0.4)` | Focus ring (accessibility) |

### 5.3 Component Pattern Tokens

Several recurring patterns across screens need shared definitions.

**Receipt tooltip pattern:**

| Token | Value | Rationale |
|-------|-------|-----------|
| `--receipt-bg` | `var(--color-bg-raised)` | Receipts sit at highest elevation |
| `--receipt-border` | `rgba(184, 169, 232, 0.2)` | Subtle insight-tinted border — data provenance is an "insight" concept |
| `--receipt-radius` | `var(--radius-lg)` | 14px, consistent with cards |
| `--receipt-max-width` | `360px` | Prevents receipts from sprawling |

**Slider pattern:**

| Token | Value | Rationale |
|-------|-------|-----------|
| `--slider-track-height` | `4px` | Thin, elegant |
| `--slider-track-bg` | `var(--color-bg-void)` | Deepest dark for contrast |
| `--slider-thumb-size` | `24px` | Large enough to grab, small enough to feel precise |
| `--slider-thumb-bg` | `var(--color-bg-raised)` | Highest elevation — the thumb is the most interactive element |

**Pill/chip pattern:**

| Token | Value | Rationale |
|-------|-------|-----------|
| `--pill-height` | `28px` | Compact but tappable |
| `--pill-padding` | `4px 12px` | Snug horizontal, minimal vertical |
| `--pill-radius` | `var(--radius-full)` | Fully rounded — pills are always round |
| `--pill-font-size` | `var(--text-small)` | 14px |

### 5.4 Typography Gaps

**Profile name scale:** The profile name on Screen 2 needs to be larger than `--text-display` (36px). It is the hero element on a full-viewport screen. Propose:

| Token | Value | Usage |
|-------|-------|-------|
| `--text-profile-name` | `2.5rem` (40px) | Profile name display. Between display and hero. |

Actually, on reflection, `--text-hero` at 48px may be sufficient. The emoji rendering at 48-64px beside it will create adequate visual weight. No new token needed — use `--text-hero` for the profile name.

**Stat tutorial overlay typography:** The stat tutorial needs an explanation card style. Propose using existing tokens: Nunito body at `--text-body` for explanations, Fredoka at `--text-heading` for the stat name being explained, Space Mono at `--text-data-large` for the stat value. No new tokens needed — the existing scale covers this.

**However:** The tutorial needs an overlay-specific token for the backdrop dim:

| Token | Value | Usage |
|-------|-------|-------|
| `--overlay-backdrop` | `rgba(18, 19, 31, 0.85)` | Tutorial and modal backdrop. Matches the void with high opacity. |
| `--overlay-blur` | `8px` | Backdrop blur for overlays. |

### 5.5 Color Gaps

**Boss fight result state colors:** The current system has boss colors (per-boss signature hues) but no semantic tokens for fight result states.

| Token | Value | Usage |
|-------|-------|-------|
| `--color-result-win` | `var(--color-accent-thrive)` | Win state — green |
| `--color-result-lose` | `var(--color-accent-alert)` | Lose state — amber |
| `--color-result-draw` | `var(--color-accent-caution)` | Draw state — gold |
| `--color-result-structural` | `var(--color-text-muted)` | Structural loss — muted, not red |

These are semantic aliases — they point to existing accent colors but give them fight-specific meaning. This prevents the codebase from scattering `accent-alert` everywhere when the semantic meaning is "boss fight loss."

**Reroll state colors:**

| Token | Value | Usage |
|-------|-------|-------|
| `--color-reroll-available` | `var(--color-accent-insight)` | Skills available to equip — purple/insight |
| `--color-reroll-equipped` | `var(--color-accent-thrive)` | Skill equipped — green/confirmed |
| `--color-reroll-exhausted` | `var(--color-text-muted)` | Skill pool empty — muted |

**Wrapped frame background:** Wrapped frames render on `bg-deep` per the PRD. No gap here — existing tokens cover it.

### 5.6 Responsive Tokens

The current breakpoints (`--bp-mobile` through `--bp-ultra`) and spacing scale are adequate. But the design system proposal defines responsive spacing values that are not yet in `tokens.css`:

| Token | Mobile | Tablet | Desktop | Usage |
|-------|--------|--------|---------|-------|
| `--space-page-x` | 16px | 24px | 32px | Horizontal page padding |
| `--space-page-y` | 16px | 24px | 32px | Vertical page padding |
| `--space-section` | 24px | 32px | 48px | Between major sections |
| `--space-card-gap` | 12px | 16px | 20px | Between cards in a grid/list |

These should be implemented via Tailwind responsive utilities rather than CSS custom properties (custom properties cannot respond to media queries without JavaScript). The Tailwind config already has the `screens` breakpoints — the spacing application should use `p-4 tablet:p-6 desktop:p-8` patterns.

**Recommendation:** Do not add responsive spacing tokens to `tokens.css`. Instead, document the responsive spacing patterns in the design system and enforce them through code review. The existing spacing scale (`--space-4` through `--space-8`) combined with Tailwind responsive prefixes covers the need.

### 5.7 Pentagon Chart Tokens

The pentagon chart appears on Screen 1 (glow), Screen 6 (reveal), Screen 8 (branch endpoints), Screen 10 (compare overlay), and Wrapped frames. It needs its own token set.

| Token | Value | Usage |
|-------|-------|-------|
| `--pentagon-size-hero` | `300px` | Screen 6 reveal, primary display |
| `--pentagon-size-default` | `200px` | Screen 1 glow, Wrapped frames |
| `--pentagon-size-mini` | `120px` | Branch endpoints, compare |
| `--pentagon-size-micro` | `80px` | Career cards, compact previews |
| `--pentagon-fill-opacity` | `0.15` | Interior fill (gradient from center) |
| `--pentagon-stroke-width` | `2px` | Axis lines and polygon outline |
| `--pentagon-vertex-size` | `8px` | Vertex dot diameter |
| `--pentagon-glow-radius` | `20px` | Glow at each vertex (for Screen 1) |

---

## 6. Receipts and Provenance UI

Receipts appear on almost every screen. They are a cross-cutting pattern that needs its own design language.

### The Design Problem

Receipts serve two audiences simultaneously:

1. **The student** who wants to understand where a number came from. "Why is my ERN a 7?" The receipt shows the raw salary data, the effort adjustment, the percentile mapping.

2. **The adversarial auditor** (hackathon judges, parents, counselors) who wants to verify that FutureProof is not making things up. "Where did this AI exposure score come from?" The receipt shows: Karpathy model, O*NET task data, specific SOC code, computed score, threshold applied.

These audiences need different densities of information, but the same entry point.

### The Pattern

**Entry point:** A small "?" icon (Lucide HelpCircle or similar) rendered in `text-muted`, positioned inline next to any data point that has provenance. The icon is unobtrusive — it should not clutter the emotional experience. Opacity 0.5 by default, 1.0 on hover.

**On tap:** A popover appears (not a modal — the student should not lose context). The popover uses the receipt token set defined in section 5.3:

- Background: `--receipt-bg` (`bg-raised`)
- Border: insight-tinted at 20% opacity
- Max width: 360px
- Radius: `--radius-lg` (14px)
- Shadow: `--shadow-lg`

**Content structure:**

```
┌──────────────────────────────────────┐
│  ERN: Earning Power                  │  ← Fredoka heading
│  Score: 7 / 10                       │  ← Space Mono data-large
│                                      │
│  Raw Data                            │  ← Nunito body-bold
│  Median earnings: $68,400            │  ← Space Mono data
│  Percentile used: 75th (All-in)      │
│  Source: College Scorecard 2022      │
│                                      │
│  Threshold                           │  ← Nunito body-bold
│  1-2: < $30K | 3-4: $30-45K |       │  ← Space Mono data-small
│  5-6: $45-65K | 7-8: $65-90K |      │
│  9-10: > $90K                        │
│                                      │
│  ◊ Data last updated: Jan 2024      │  ← text-muted, micro
└──────────────────────────────────────┘
```

**Progressive disclosure:** The receipt opens showing the score and raw data by default. The threshold section is collapsed behind a "How is this scored?" toggle. This serves both audiences: students get the explanation, auditors get the methodology.

**Positioning:** Popovers anchor to the "?" icon and prefer to open downward and to the right. On mobile, receipts open as bottom sheets (slide up from the bottom, 60% viewport height) to avoid floating popovers that occlude content.

**Dismiss:** Tap outside the popover, or tap the "?" icon again. On mobile bottom sheet, swipe down to dismiss.

### Where Receipts Appear

| Screen | Receipt Locations |
|--------|------------------|
| 6 (Reveal) | Each stat vertex on the pentagon, the salary figure, the ROI calculation |
| 7 (Gauntlet) | Each boss fight result, each reroll rescore |
| 8 (Branch Tree) | Each branch endpoint's stats |
| 10 (Compare) | Each stat in the comparison, the tradeoff summary |

Receipts do NOT appear on Screens 1-5 (no computed data to show provenance for) or Screen 9 (the Wrapped frames do not include interactive receipts — they are static images).

---

## 7. The Wrapped Experience

### What It Is

A multi-frame story sequence designed for Instagram Stories (1080x1920, 9:16 aspect ratio). Each frame is a self-contained visual that tells one aspect of the student's build story. The student taps through the sequence in the app, screenshots individual frames, or downloads all frames as PNGs.

This is not a screen. It is a mini-product within the product. Its quality determines whether FutureProof goes viral.

### Frame-by-Frame Vision

**Frame 1: Identity**
- Dark background (`bg-deep`)
- Large emoji animal centered: 120px
- Below: profile name in Fredoka hero size
- Below: "just speced [School] [Major]" in Nunito secondary
- Bottom: FutureProof logo/wordmark, small
- Feeling: "Here I am. This is my name." Students screenshot this frame for their profile.

**Frame 2: Pentagon**
- Dark background with subtle radial glow from center
- Full stat pentagon, 400px (fills most of the frame width at 1080px)
- Stat labels and values at each vertex
- Profile name + emoji small at top
- No additional text — the shape speaks
- Feeling: "These are my numbers." The pentagon shape is instantly recognizable from the app. Students who have used FutureProof recognize each other's pentagons.

**Frame 3: Boss Scorecard**
- Dark background
- Five rows, each showing: boss emoji, boss name, result (WIN/LOSE/DRAW in result colors)
- Final Boss result at bottom, larger, with the composite verdict
- Brief headline: "I fought five bosses"
- Feeling: "Did you beat yours?" This is the frame that triggers competitive comparison between friends.

**Frame 4: Comparative Insight**
- Dark background
- One bold stat comparison: "Your AI Resilience is higher than 62% of business paths"
- Stat icon large, stat color dominant
- This is Gemma-generated — personalized to the student's build
- Feeling: "I'm doing better than I thought." Or: "Huh, I should think about that." Either way, it is a conversation starter.

**Frame 5: Risk Highlight**
- Dark background
- "Your biggest risk:" in Nunito secondary
- Large boss emoji + boss name in accent-alert
- Brief one-line reason: "Student loan debt at your school is among the highest in the state"
- Feeling: Honest but not devastating. This is the frame that starts real conversations — "Yeah, the loans are rough."

**Frame 6: CTA**
- Dark background
- "See where your path leads" in Fredoka hero
- Pentagon glow (same as Screen 1 landing) subtle behind text
- URL: futureproof.app
- Feeling: "Your friend just showed you something cool. You want to try it."

### The Social Loop

The loop works like this:

1. Student A builds a career in FutureProof
2. Student A shares Wrapped frames to Instagram Stories
3. Student A captions: "I'm Dancing Happy Bear" or "I beat 4 out of 5 bosses"
4. Student B sees the story and thinks: "What name would I get? What would my pentagon look like?"
5. Student B opens FutureProof
6. Repeat

The key insight: the Wrapped frames are not reports. They are identity artifacts. "I'm Steady Bold Turtle" is a claim about who you are, just like "I'm a Hufflepuff" or "I'm an INFJ." The profile name system creates the identity. The Wrapped frames broadcast it.

### Design Constraints

- Every frame must be legible at Instagram Stories resolution (1080x1920)
- Every frame must be legible in the small circular "story dot" preview (32px circle)
- Text must be large enough to read on a phone at arm's length
- The dark background must be `bg-deep`, not `bg-void` — Stories compress heavily, and pure dark backgrounds create banding artifacts
- No interactive elements — these are static images rendered by Puppeteer
- Each frame must stand alone — a student might screenshot only Frame 3 and share it

---

## 8. Open Questions

### Q1: Should the profile name header persist across all screens, or only appear from Screen 3 onward?

**My recommendation:** Appear from Screen 3 onward. Screens 1 and 2 are immersive full-bleed experiences. Adding a persistent header breaks the cinematic quality. From Screen 3 forward, the profile name in a thin fixed header (24px height, `bg-deep` with border-subtle bottom, profile name + emoji in text-muted) provides identity continuity without breaking immersion.

**Alternative:** No persistent header at all. The profile name only appears in the personalized loading states and on the Wrapped frames. This is cleaner but risks the student forgetting their name if they step away and come back.

### Q2: Pentagon glow on Landing — pure CSS animation or Framer Motion?

**My recommendation:** Pure CSS animation. The pentagon glow is ambient and continuous. It does not respond to user interaction. CSS `@keyframes` with `animation-iteration-count: infinite` is more performant than a Framer Motion animation loop and does not require the Framer Motion runtime to be loaded before the landing screen renders. The glow should be visible the instant the page loads.

**Alternative:** Framer Motion's `animate` with `repeat: Infinity`. This keeps all animation logic in one system. The performance difference is negligible on modern browsers. But the CSS approach has the advantage of working even if JavaScript is slow to load.

### Q3: How much data should each branch endpoint show when tapped on the tree?

**My recommendation:** Pentagon + salary + top risk (worst boss fight result). Three pieces of data. The student can compare branches at a glance without being overwhelmed. If they want more, they can do a full build on that career.

**Alternative:** Full stat pentagon + all 5 boss fight results + skill requirements + salary + growth. This is maximally informational but risks turning the tree exploration into a data analysis exercise. The tree should feel like exploration, not homework.

### Q4: Should the Wrapped frames be rendered server-side (Puppeteer) or client-side (html2canvas or dom-to-image)?

**My recommendation:** Server-side Puppeteer. Client-side rendering libraries produce inconsistent results across browsers and devices, especially with custom fonts and SVG. Puppeteer produces pixel-perfect output every time. The latency tradeoff (1-3 seconds to render all 6 frames) is acceptable given that the student has just completed a multi-minute build experience and is in "share" mode, not "hurry" mode.

**Alternative:** Client-side rendering. Eliminates the Puppeteer dependency and server-side compute cost. Faster for the student (instant rendering). But the quality risk is real — a poorly rendered Wrapped frame that a student shares to Instagram reflects badly on the product.

### Q5: Should the Next Steps checklist appear as part of Screen 7 (Gauntlet) or as its own screen?

**My recommendation:** Part of Screen 7. The Next Steps follow the gauntlet as a natural conclusion — "you fought the bosses, here is what to do about it." Making it a separate screen would add a navigation step that breaks the flow. The gauntlet screen already has sequential sub-states (each boss fight). Next Steps is simply the final sub-state, after the Fight the Future scorecard.

**Alternative:** Own screen. This gives the Next Steps more visual weight and makes it clearer that the RPG metaphor has dropped. The risk is that adding another screen makes the product feel longer.

### Q6: How should the stat tutorial behave if the student has seen it once, creates a new build, and returns to the Reveal screen?

**My recommendation:** Skip it entirely on subsequent builds. Show only the persistent "?" icons. The student already knows what the stats mean. Repeating the tutorial would be patronizing.

**Alternative:** A condensed version — a single-screen reminder card instead of the guided walkthrough. "Remember: ERN is earning power, ROI is return on investment..." This acknowledges that the student might have forgotten while respecting their time. I lean against this — the persistent "?" icons handle the "I forgot" case.

### Q7: Noise texture overlay — ship it or skip it?

The design system proposal mentions a subtle noise texture at 2-4% opacity over backgrounds to prevent the "flat CSS" look. The interactive mockup (`brightpath-design-system.html`) includes it as a `body::before` pseudo-element with an SVG filter.

**My recommendation:** Ship it. The noise texture is the difference between "dark CSS page" and "dark velvet curtain." It adds materiality. At 2-3% opacity, it is barely perceptible consciously but subconsciously elevates the feel. The SVG filter approach has near-zero performance cost (it is a single fixed-position overlay).

**Alternative:** Skip it. It complicates screenshots and Wrapped frame rendering. If the noise texture is applied via `body::before`, Puppeteer will capture it in Wrapped frames, which could create moire patterns at Instagram's compression level. One solution: apply the noise texture only to the main app container, not to the Wrapped frame templates.

---

## Appendix: Screen-to-API Mapping

For reference, here is how each screen maps to the backend API surface (from the fastapi-router-wiring spec):

| Screen | Primary API Calls |
|--------|------------------|
| 1 (Landing) | None (static) |
| 2 (Profile) | `POST /profile`, `POST /profile/reroll`, `POST /profile/lookup` |
| 3 (School + Major) | `GET /schools?q=`, `GET /schools/{unitid}/programs`, `POST /intent`, `POST /intent/confirm` |
| 4 (Effort + Loans) | None (client-side state) |
| 5 (Career Pick) | `POST /build/outcomes`, `POST /build/tier` |
| 6 (Reveal) | `POST /build` (includes guidance), stat tutorial is client-side |
| 7 (Gauntlet) | Gauntlet comes from build response. `POST /build/{id}/reroll` for rerolls. `POST /build/{id}/next-steps` for checklist. |
| 8 (Branch Tree) | `GET /branches/{soc}`, `GET /tree/{soc}` |
| 9 (Save + Share) | `POST /build/{id}/save`, `GET /build/{id}/wrapped` |
| 10 (Menu) | `POST /builds/compare`, `POST /build/{id}/chat`, `GET /build/{id}` |

---

*— @fp-design-visionary, 2026-04-12*
