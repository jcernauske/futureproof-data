# FutureProof -- Application Chrome Design

**Author:** @fp-design-visionary
**Date:** 2026-04-12
**Status:** For human review
**Governing documents:** PRD v8, Brightpath Design System, Full Vision Report

---

## The Emotion First

Before a single pixel of chrome: what should the student feel about the *application itself* as a container?

The answer is **invisible trust.** The chrome should feel like the walls of a movie theater -- you know they are there, they keep you safe, they help you navigate to the exit if needed, but you never look at them during the film. FutureProof is a cinematic experience. The chrome must serve without competing.

The second emotion is **progressive familiarity.** On Screen 1, the student does not know this app. By Screen 10, they own it. The chrome should grow with the student -- absent at first, appearing gradually, reaching full presence only when the student is ready for a hub experience.

Here is why this matters: most app shells are designed as if the user already knows the product. A top nav, a sidebar, a footer -- all present from moment one, all screaming "I am an APPLICATION." FutureProof is not an application. It is a *journey that becomes an application.* The chrome must reflect that arc.

---

## 1. The Recommendation: Breathing Chrome

### Architecture: Minimal Top Bar + Contextual Footer Actions

No sidebar. No bottom tab bar. No hamburger menu during the linear flow. One thin, frosted header bar that fades in after the student receives their identity, and contextual action buttons at the bottom of each screen's content.

Here is the layout:

```
Desktop (1440px)                       Mobile (375px)
+------------------------------------+ +------------------+
| [back]  dancing happy bear 🐻  [...] | | [<] d.h.bear 🐻  |
+------------------------------------+ +------------------+
|                                    | |                  |
|                                    | |                  |
|          Screen Content            | |  Screen Content  |
|        (centered column,           | |  (full-width,    |
|         max-width: 640px)          | |   16px padding)  |
|                                    | |                  |
|                                    | |                  |
|                                    | |                  |
|        [Primary CTA Button]       | | [Primary CTA]    |
+------------------------------------+ +------------------+
```

There is no persistent bottom bar. There is no footer. The CTA at the bottom of each screen IS the navigation forward. The back button in the header IS the navigation backward. That is the entire navigation model.

### Why This Approach

**Alternatives I considered and rejected:**

1. **Full top nav with step indicators** -- Rejected because it makes FutureProof feel like a form wizard. "Step 3 of 9" kills the sense of adventure. You do not show a chapter counter while someone is reading a novel.

2. **Bottom tab bar (mobile app style)** -- Rejected because (a) this is a web app, not a native app, and browser chrome already occupies the bottom on mobile, (b) there are no persistent tabs during the linear flow, and (c) tab bars signal "dashboard" not "journey."

3. **Sidebar navigation** -- Rejected because the content is single-column. A sidebar would create empty space on the left and push the content off-center. The branch tree (Screen 8) needs full viewport width -- a sidebar would steal from the signature moment.

4. **No chrome at all (fully chromeless)** -- Rejected because students need an escape hatch. "How do I go back?" is a real question. The back button and profile identity must be somewhere persistent.

5. **Hamburger menu from Screen 1** -- Rejected because there is nothing to navigate TO during the linear flow. A hamburger menu with no items is worse than no menu at all.

The breathing chrome model works because it matches the product's emotional arc: absent in the void, present during the journey, fully expressed at the hub.

---

## 2. The Header Bar: FutureProof's Only Persistent Chrome

### What It Is

A 48px fixed header bar with frosted glass treatment. It contains three zones:

```
+-----------------------------------------------+
| [Left Zone]    [Center Zone]    [Right Zone]   |
+-----------------------------------------------+
```

**Left Zone:** Back navigation. A ghost-style back arrow icon. On screens where back is not possible (Screen 1, Screen 2), this zone is empty.

**Center Zone:** Profile identity. The student's profile name and emoji: "dancing happy bear" with the emoji. Displayed in Nunito at `text-small` (14px), `text-muted` color. Subtly present, never dominant. On screens before the profile exists (Screen 1), this zone shows a small FutureProof wordmark or is empty.

**Right Zone:** Contextual actions. On most screens, this is empty. On Screen 10 (Menu) and subsequent hub screens, this zone holds a small "New Build" icon button. On screens with receipts/provenance, a small "?" info icon could live here.

### Frosted Glass Treatment

The header is not a solid bar. It is frosted glass -- a semi-transparent surface that lets the background imagery bleed through with a blur:

```css
.chrome-header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 48px;
  background: rgba(27, 29, 48, 0.88);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
  z-index: 100;
}
```

Here is why this matters: a solid `bg-deep` header would feel like a ceiling -- a hard surface capping the content. The frosted glass maintains the sense that the world extends above the viewport. The blur picks up background glows (the pentagon on Screen 1, the boss color washes on Screen 7, the branch tree radial on Screen 8) and integrates them into the header, making the chrome feel like part of the world rather than sitting on top of it.

### Animation: The Fade-In

The header does not exist on Screen 1 (Landing). It fades in during the transition from Screen 1 to Screen 2:

```typescript
// Framer Motion
<motion.header
  initial={{ opacity: 0, y: -20 }}
  animate={{ opacity: 1, y: 0 }}
  transition={{ type: "spring", stiffness: 200, damping: 25, delay: 0.3 }}
>
```

The 300ms delay lets the profile name render first on Screen 2, so the student reads their name in the hero position, THEN notices it also appears in the header. The name in the header is the echo, not the proclamation.

### Progressive Illumination in the Header

The header participates in Progressive Illumination via two subtle mechanisms:

1. **Border brightness:** The bottom border starts at `rgba(255, 255, 255, 0.04)` on Screens 2-5 and steps up to `rgba(255, 255, 255, 0.08)` on Screens 6-10. Imperceptible in isolation, noticeable in aggregate.

2. **Profile name color:** The profile name starts at `text-muted` (#8A8595) on Screens 2-5 and shifts to `text-secondary` (#C4BFB0) on Screen 6 onward. The student has been "revealed" -- their identity is now brighter because their future is illuminated.

---

## 3. Navigation Model

### During the Linear Flow (Screens 1 through 9)

Navigation is **forward-dominant**. Each screen has a primary CTA at the bottom of its content that moves the student forward. The back button in the header allows retreating one step.

**Forward:** The CTA button at the bottom of each screen's content. "Begin Your Quest" (Screen 1), "Let's Go" (Screen 2), "Lock In" (Screen 3), "Spec My Build" (Screen 4), etc.

**Backward:** The back arrow in the header's left zone. One tap = one screen back. No confirmation dialogs during the linear flow -- the student can freely navigate backward.

**Skipping:** Not supported. The linear flow is sequential. You cannot jump from Screen 2 to Screen 6. This is intentional -- each screen builds context that the next screen requires.

**Browser back button:** Works naturally. Each screen pushes a route to browser history. The browser back button and the in-app back button do the same thing. This is critical for web apps -- fighting the browser back button is a cardinal sin.

### The Mode Shift: Linear to Hub (Screen 9 to Screen 10)

After Save + Share (Screen 9), the student enters the Menu (Screen 10). This is a significant transition. The product shifts from "guided journey" to "open-ended exploration."

The chrome communicates this shift through two changes:

1. **The header's right zone activates.** A "New Build" button appears (small, `accent-info`, icon-only on mobile, icon+label on desktop). This signals: "You now have capabilities beyond forward/back."

2. **The back button becomes a home icon.** In the linear flow, the left zone shows a back arrow (left chevron). On Screen 10 and all hub sub-screens, the back arrow is replaced by a home icon (a small house or the FutureProof "F" glyph) that always returns to the Menu. This signals: the Menu is the new center of gravity.

### From Hub Sub-Screens

Hub sub-screens (Compare, Ask Gemma, Branch Explorer) use the header's home icon to return to Menu. They do NOT push additional back-stack entries for internal navigation within the sub-screen -- the home icon is the escape hatch.

Exception: if the Branch Explorer has deep node selections, the header back button can step back through selections before returning to Menu. But this is internal state, not route changes.

### Deep Links and Bookmarks

If a student bookmarks or shares a deep link (e.g., `/build/12345/branches`):

- The app checks if build data exists for that build ID
- If yes: render the screen with a "Return to Menu" home icon in the header
- If no: redirect to Screen 1 (Landing) with a gentle message: "That build could not be found. Start a new quest?"

The profile name in the header is populated from the build's stored profile name, so even a deep-linked screen shows identity.

---

## 4. Progress Indication

### The Decision: No Explicit Progress Bar

FutureProof does **not** show "Step 3 of 9" or a progress bar during the linear flow.

Here is why: showing progress turns the experience into a form. The student starts counting steps. "I am on step 4, I have 5 more to go." This is the opposite of immersion. A game does not show you what percentage of the game you have completed during a level -- it lets you play.

Additionally, the 9-screen flow is misleading. Screen 7 (Boss Gauntlet) contains 5-6 internal fights. Screen 8 (Branch Tree) is an open-ended exploration. A "Step 7 of 9" label would suggest you are almost done when you are actually in the middle of the most complex sequence.

### What We Do Instead: Implied Progress Through Illumination

Progressive Illumination IS the progress indicator. The student does not need a number to know they are progressing -- the world is getting brighter. Backgrounds shift from `bg-void` to `bg-deep`. The profile name in the header gets brighter. Content becomes richer and more data-dense. The student feels progress without counting it.

### Exception: Boss Gauntlet Internal Progress

Screen 7 is the one place where explicit progress indication is warranted. The gauntlet has 5 mini-boss fights plus a Final Boss -- the student needs to know where they are in the sequence. The existing mockup uses "progress pips" -- small circles that fill with win/lose/draw colors as fights complete. This is correct and should be kept. The pips sit below the boss display area, not in the header.

```
[ O ]  [ O ]  [ O ]  [ . ]  [ . ]  |  [ O ]
 win    win   lose  current  next    final
```

The pips are colored: `accent-thrive` for wins, `accent-alert` for losses, `accent-caution` for draws, `text-primary` for current, and empty (`bg-surface` outline) for upcoming. A thin divider separates the five mini-bosses from the Final Boss pip.

This works because it is internal progress within a single screen, not application-wide progress. It has the energy of a fighting game health bar, not a form wizard.

### Exception: Stat Tutorial Internal Progress

Screen 6's first-build stat tutorial has 5 steps (one per stat). Small dots at the bottom of the tutorial overlay indicate which stat explanation the student is viewing. Same pattern as the gauntlet pips but smaller and simpler -- just filled/unfilled circles in `text-muted` and `text-primary`.

---

## 5. Profile Persistence

### How the Profile Name Travels

The profile name appears in these locations, in order of when the student first sees it:

| Location | When It Appears | Style | Purpose |
|----------|----------------|-------|---------|
| Screen 2 hero | Screen 2 load | `text-hero` (48px), Fredoka, `text-primary` | Proclamation. "You ARE this." |
| Header center | Screen 2 (with 300ms delay) | `text-small` (14px), Nunito, `text-muted` | Persistent identity. An echo. |
| Loading states | Screen 5-6 transition and others | `text-body` (16px), Nunito, `text-secondary` | "Specing dancing happy bear..." |
| Wrapped frames | Screen 9 | Various sizes | Social identity. |
| Menu header | Screen 10 | `text-heading`, Fredoka | Welcome back. "dancing happy bear's builds" |

The header display is the constant thread. It is deliberately small and muted -- the profile name should feel like a quiet companion, not a shouting label.

### Growth Over Time

The profile name in the header does not visually "grow" (no size changes). What changes is the header's overall energy:

- **Screens 2-5:** Profile name alone. `text-muted`. The header is minimal.
- **Screens 6-9:** After the reveal, the profile name shifts to `text-secondary`. Very slightly brighter. The student has been revealed -- they deserve to be more visible.
- **Screen 10 (Menu):** The header profile name stays at `text-secondary`. The Menu screen itself shows a larger welcome message. The header does not duplicate this.

Adding stats or additional data to the header would clutter it. The header's job is identity and navigation, not information density. Stats live in the screens.

---

## 6. Cinematic Chrome Recession

Three screens demand that the chrome recede or adapt to avoid competing with the content:

### Screen 1 (Landing): Fully Chromeless

The landing screen has NO header, NO back button, NO profile name. It is a full-viewport cinematic canvas. The pentagon glow, the tagline, and the CTA are the only elements. Adding chrome to this screen would be like putting a navigation bar on a movie poster.

### Screen 7 (Boss Gauntlet): Header Dims

During boss fight sequences, the header reduces its opacity to 60%. The profile name fades to near-invisible. The back button remains functional but visually recedes. The student's attention should be on the boss, not the chrome.

```css
.chrome-header--cinematic {
  background: rgba(27, 29, 48, 0.6);
  border-bottom-color: rgba(255, 255, 255, 0.02);
}
.chrome-header--cinematic .profile-name {
  opacity: 0.4;
}
```

Between fights (result display, reroll flow), the header returns to normal opacity.

### Screen 8 (Branch Tree): Header with Void Background

The branch tree uses `bg-void` as its background and fills the full viewport. The header remains present (the student may need to navigate back) but its frosted glass background matches the void -- essentially becoming nearly invisible against the dark canvas. The profile name stays visible because the tree's radial glow from the center does not extend to the header area.

The tree should NOT be constrained by a `padding-top: 48px` from the header. Instead, the tree renders underneath the header (using `padding-top: 0` and `z-index` layering). The header floats over the tree's top edge, letting the tree extend to the full viewport edges.

---

## 7. Screen-by-Screen Chrome State

| Screen | Header Visible | Left Zone | Center Zone | Right Zone | Background | Chrome Notes |
|--------|---------------|-----------|-------------|------------|------------|-------------|
| 1 Landing | No | -- | -- | -- | `bg-void` | Fully chromeless. Cinematic. |
| 2 Profile Name | Yes (fades in) | Empty | "FutureProof" wordmark, tiny | Empty | `bg-deep` | Header animates in. Profile name NOT in header yet (it is the hero content). |
| 3 School + Major | Yes | Back arrow | "dancing happy bear" (`text-muted`) | Empty | `bg-deep` | First screen with full header. |
| 4 Effort + Loans | Yes | Back arrow | Profile name (`text-muted`) | Empty | `bg-deep` + warm gradient | |
| 5 Career Pick | Yes | Back arrow | Profile name (`text-muted`) | Empty | `bg-deep` | |
| 6 Reveal + Stats | Yes | Back arrow | Profile name (**`text-secondary`** -- brighter) | Empty | `bg-deep` + radial glow | Progressive Illumination step: name brightens. |
| 7 Boss Gauntlet | Yes (dimmed) | Back arrow (dimmed) | Profile name (dimmed) | Empty | `bg-void` + boss color | Header at 60% during fights, full between. Gauntlet pips in screen content, not header. |
| 8 Branch Tree | Yes (void-blended) | Back arrow | Profile name (`text-secondary`) | Empty | `bg-void` + radial | Header floats over tree. No content padding for header height. |
| 9 Save + Share | Yes | Back arrow | Profile name (`text-secondary`) | Empty | `bg-deep` | |
| 10 Menu | Yes | Home icon (replaces back) | Profile name (`text-secondary`) | "New Build" button | `bg-deep` | Mode shift. Right zone activates. Left zone changes icon. |
| Hub sub-screens | Yes | Home icon | Profile name | Contextual | Varies | Compare, Ask Gemma, Branch Explorer all show home icon. |

---

## 8. Mobile vs Desktop Chrome

### Desktop (768px and above)

The header spans the full viewport width. Content below it is centered in a max-width column (typically 640px for form screens, full-width for the branch tree). The header's three zones spread across the full width with comfortable spacing:

```
| 32px | [back icon] | ------- profile name (centered) ------- | [action] | 32px |
```

### Mobile (below 768px)

The header is the same 48px height. The profile name truncates if needed -- "d.h.bear" is acceptable if the full name does not fit. The back arrow and any right-zone icons use 44x44px touch targets even though they render smaller visually.

```
| 16px | [<] | ---- d.h.bear 🐻 ---- | 16px |
```

There is no bottom tab bar on mobile. The primary CTA buttons at the bottom of each screen's content are the forward navigation, and they already receive full-width treatment on mobile viewports. Adding a bottom bar would compete with these CTAs and fight the browser's own bottom UI.

### Swipe Gestures

Not supported in the MVP. Swipe-to-go-back is a native mobile convention that is unreliable in web apps (conflicts with the browser's own swipe-back gesture). The back button in the header is sufficient.

---

## 9. The Transition Between Linear and Hub

This deserves its own section because it is the most significant chrome state change in the product.

After the student saves their build (Screen 9), they arrive at the Menu (Screen 10). Three things change simultaneously during the transition:

1. **The header's left zone:** The back arrow morphs into a home icon. This is animated -- the arrow fades out (150ms), the home icon fades in (150ms). The morph signals: "You are no longer in a sequence. You are at a hub."

2. **The header's right zone:** A "New Build" pill button fades in from the right. `accent-info` border, Nunito `text-small`, icon + label on desktop ("+ New"), icon-only on mobile. This button did not exist during the linear flow.

3. **The screen content:** The Menu itself is a grid of action cards, not a single CTA. The layout change from "centered column with one button" to "grid of options" reinforces the mode shift.

```typescript
// Framer Motion for the right-zone activation
<motion.button
  initial={{ opacity: 0, x: 20 }}
  animate={{ opacity: 1, x: 0 }}
  transition={{ type: "spring", stiffness: 200, damping: 25, delay: 0.5 }}
  className="new-build-pill"
>
  + New
</motion.button>
```

### Can Students Access the Menu Early?

No. The Menu is not accessible until the student completes at least one build. There is no hamburger icon, no menu button, no escape hatch to the hub during the linear flow. This is intentional -- the Menu has nothing useful to show until a build exists.

The one exception: if a returning student looks up their profile name on Screen 2 and has existing builds, they can proceed directly to the Menu. In this case, the header transitions directly to the hub state (home icon, right-zone active).

---

## 10. Edge Cases

### Bookmarked Deep Screens

A student bookmarks `/build/abc123/branches` and returns later.

- The app loads the build data from the backend
- The header renders in hub state (home icon, profile name from the stored build)
- The branch tree renders with the stored data
- The home icon navigates to the Menu for this profile

If the build ID is invalid or expired, redirect to Screen 1 with a gentle message.

### Screen 1 Chrome State

Screen 1 is fully chromeless. No header, no navigation. The only interactive element is the CTA. This is non-negotiable -- the landing is a cinematic moment. Chrome on the landing would be like credits rolling before the movie starts.

### Returning Users Skipping to Menu

A returning student enters their profile name on Screen 2. The app finds their builds. Two paths:

1. **Resume linear flow:** If the student has an in-progress build (started but not saved), offer to resume. The header renders in linear-flow state (back arrow, profile name, no right zone).

2. **Jump to Menu:** If the student has completed builds, navigate to Menu. The header renders in hub state.

### Browser Refresh Mid-Flow

If the student refreshes mid-flow (e.g., on Screen 5), the app should:

- Check for any in-progress build state in the session/local storage
- If found: re-render the current screen with the stored state, header in linear-flow mode
- If not found: redirect to Screen 1

This is a frontend state management concern, not a chrome concern. The chrome simply reflects whatever state the app resolves to.

### Very Long Profile Names

Profile names are three words + emoji. The longest realistic name would be something like "adventurous magnificent turtle" (approximately 30 characters + emoji). The header handles this by:

- Desktop: full name displayed, no issue at any reasonable viewport width
- Mobile: truncate with ellipsis after ~20 characters if needed. The emoji is never truncated -- it is the visual anchor.

---

## 11. Implementation Notes

### React Component Structure

```typescript
// AppShell.tsx -- the chrome wrapper
interface AppShellProps {
  children: React.ReactNode;
  screen: ScreenId;           // 1-10
  profileName?: string;       // absent on Screen 1
  hasCompletedBuild: boolean; // controls hub mode
}

function AppShell({ children, screen, profileName, hasCompletedBuild }: AppShellProps) {
  const showHeader = screen > 1;
  const isHubMode = screen >= 10 || (screen === 2 && hasCompletedBuild);
  const isCinematic = screen === 7; // boss gauntlet dims header
  const isVoidBlended = screen === 8; // branch tree

  return (
    <div className="app-shell">
      <AnimatePresence>
        {showHeader && (
          <ChromeHeader
            profileName={profileName}
            isHubMode={isHubMode}
            isCinematic={isCinematic}
            isVoidBlended={isVoidBlended}
            screen={screen}
          />
        )}
      </AnimatePresence>
      <main className={cn(
        "screen-content",
        showHeader && "pt-12", // 48px header offset
        screen === 8 && "pt-0" // branch tree: no offset, renders under header
      )}>
        {children}
      </main>
    </div>
  );
}
```

### Route Structure

```
/                       → Screen 1 (Landing)
/start                  → Screen 2 (Profile Name)
/build/new/school       → Screen 3 (School + Major)
/build/new/effort       → Screen 4 (Effort + Loans)
/build/new/career       → Screen 5 (Career Pick)
/build/:id/reveal       → Screen 6 (Reveal + Stats)
/build/:id/gauntlet     → Screen 7 (Boss Gauntlet)
/build/:id/branches     → Screen 8 (Branch Tree)
/build/:id/save         → Screen 9 (Save + Share)
/menu                   → Screen 10 (Menu)
/compare                → Compare sub-screen
/chat                   → Ask Gemma sub-screen
```

Each route pushes to browser history, making the browser back button work naturally.

### CSS Token Additions

The chrome requires these additions to the token system:

| Token | Value | Purpose |
|-------|-------|---------|
| `--chrome-height` | `48px` | Header height |
| `--chrome-bg` | `rgba(27, 29, 48, 0.88)` | Header background |
| `--chrome-bg-cinematic` | `rgba(27, 29, 48, 0.6)` | Dimmed header during boss fights |
| `--chrome-blur` | `16px` | Backdrop blur |
| `--chrome-border` | `rgba(255, 255, 255, 0.04)` | Default border |
| `--chrome-border-bright` | `rgba(255, 255, 255, 0.08)` | Post-reveal border |

---

## 12. What Makes This Feel Like FutureProof

The chrome system I have described is deliberately minimal. Here is why that IS the premium choice, not a compromise:

**The best game UIs are invisible.** Breath of the Wild, Journey, Monument Valley -- the UI recedes so the world can speak. FutureProof's screens are the world. The chrome should do exactly three things: tell the student who they are (profile name), let them go back (back button), and signal when the experience shifts to a hub (mode change). Anything more than that is noise.

**The frosted glass is the key detail.** A solid header says "I am an application." A frosted header says "I am a window into a world." The blur picks up background glows and boss color washes, making the chrome feel alive and responsive to the content beneath it. This is the difference between a frame and a membrane.

**The profile name growing brighter is earned storytelling.** The student starts as a muted name in a muted header. By Screen 6, they have been revealed -- their stats are known, their career is named, their future is visible. The name deserves to be brighter. This is not decorative -- it is narrative design in the chrome layer.

**The mode shift at Screen 10 is the product's graduation ceremony.** The student moves from "guided journey" to "empowered exploration." The chrome marks this transition with exactly two changes: a home icon replaces the back arrow, and a New Build button appears. Subtle, meaningful, unmistakable. The student knows, without being told, that something has changed.

This is the application shell for a product that is a world first and a tool second. The chrome serves the world.
