# Spec B2: Profile Service

**Spec ID:** B2
**File:** `docs/specs/profile-service.md`
**Scope:** New `profile.py` service — three-word name generation, collision detection, fuzzy lookup, reroll.
**Depends on:** B1 (router wiring — profile router already defined in B1)
**Blocks:** F1 (landing + profile screen)

-----

## What This Spec Does

Creates `backend/app/services/profile.py` — the identity layer for FutureProof. Students get a whimsical three-word name (adjective + adjective + animal emoji) that serves as their profile identity across all builds. No PII, no accounts, no passwords.

The profile service handles four things:

1. **Generate** a name with silent collision detection
2. **Reroll** to a new name (same rules, excludes current)
3. **Lookup** a returning student by name (case-insensitive, fuzzy-tolerant)
4. **Persist** the mapping of profile names to saved builds

-----

## Name Generation

### Format

`{adjective_1} {adjective_2} {animal_emoji}`

Examples: "dancing happy bear 🐻", "brave curious fox 🦊", "steady bright turtle 🐢"

### Word Pools

**Adjective Pool 1** (~50 words) — personality/energy:

```python
ADJECTIVES_1 = [
    "brave", "bold", "bright", "calm", "clever",
    "cosmic", "cozy", "daring", "dancing", "dreamy",
    "eager", "electric", "epic", "fearless", "fierce",
    "free", "gentle", "glad", "glowing", "golden",
    "grand", "happy", "humble", "keen", "kind",
    "lively", "lucky", "loyal", "magic", "merry",
    "mighty", "noble", "plucky", "proud", "quick",
    "quiet", "rad", "ready", "rising", "roaming",
    "shining", "smooth", "snappy", "soaring", "sparky",
    "speedy", "spirited", "steady", "stellar", "stoked",
]
```

**Adjective Pool 2** (~50 words) — quality/vibe:

```python
ADJECTIVES_2 = [
    "agile", "awesome", "breezy", "chill", "clear",
    "crisp", "curious", "dapper", "deft", "earnest",
    "fair", "fancy", "fleet", "fluffy", "focused",
    "fresh", "frisky", "fun", "fuzzy", "groovy",
    "gutsy", "handy", "hearty", "honest", "jazzy",
    "joyful", "jumpy", "legit", "nimble", "nifty",
    "peppy", "perky", "plush", "polished", "prime",
    "pumped", "quirky", "rare", "real", "robust",
    "savvy", "sharp", "slick", "snug", "solid",
    "spry", "sure", "swift", "true", "vivid",
]
```

**Animal Emoji Set** (from Brightpath design system):

```python
ANIMALS = [
    ("bear", "🐻"),
    ("bunny", "🐰"),
    ("turtle", "🐢"),
    ("chipmunk", "🐿️"),
    ("fox", "🦊"),
    ("owl", "🦉"),
    ("penguin", "🐧"),
    ("cat", "🐱"),
]
```

### Pool Size

50 × 50 × 8 = **20,000 combinations**. Sufficient for hackathon. At 1,000 active profiles, collision probability per generation is ~5% — handled by silent retry.

-----

## Collision Detection

### Rules

1. Generate a candidate name: `random.choice(ADJECTIVES_1) + " " + random.choice(ADJECTIVES_2) + " " + random.choice(ANIMALS)`
2. Normalize: lowercase, strip extra whitespace
3. Check against all existing profile names (case-insensitive exact match)
4. If collision: silently regenerate. Retry up to 10 times.
5. If 10 retries fail (extremely unlikely at hackathon scale): append a single digit (1-9) to adjective_2 and retry. Never expose the collision to the student.

### What "Existing Profile Names" Means

The profile service maintains a set of all names that have been generated in this server session, plus all names found in saved build files on disk. On startup, scan the `builds/` directory for saved builds and extract `profile_name` from each.

```python
_active_profiles: set[str] = set()  # normalized names

def _load_existing_profiles():
    """Scan builds/ directory on startup."""
    builds_dir = Path("builds")
    if builds_dir.exists():
        for f in builds_dir.glob("*.json"):
            try:
                data = json.loads(f.read_text())
                name = data.get("profile_name", "").strip().lower()
                if name:
                    _active_profiles.add(name)
            except (json.JSONDecodeError, KeyError):
                continue
```

-----

## Fuzzy Lookup

### Purpose

Returning students type their profile name to retrieve saved builds. They won't remember exact capitalization or might misspell a word.

### Matching Strategy

1. **Exact match (case-insensitive):** `"Dancing Happy Bear 🐻"` matches `"dancing happy bear 🐻"`. Fastest path.
2. **Fuzzy match:** If no exact match, use `difflib.get_close_matches()` against all known profile names with `cutoff=0.6`. Return the single best match if similarity ≥ 0.8. If the best match is between 0.6 and 0.8, return it as a suggestion ("Did you mean...?") rather than auto-resolving.
3. **No match:** Return 404 with a helpful message.

### Normalization

Before matching:
- Lowercase
- Strip leading/trailing whitespace
- Collapse multiple spaces to single space
- Strip the emoji for fuzzy text comparison, then re-attach for display

### Response Shape

```python
class ProfileLookupResult(BaseModel):
    found: bool
    profile_name: str | None = None  # canonical name if found
    animal_emoji: str | None = None
    builds: list[BuildSummary] = []  # saved builds for this profile
    suggestion: str | None = None  # "Did you mean...?" if fuzzy match
```

```python
class BuildSummary(BaseModel):
    build_id: str
    school_name: str
    major_text: str
    career_title: str
    created_at: str  # ISO timestamp
```

### Build Retrieval

When a profile is found, scan the `builds/` directory for all saved builds with a matching `profile_name` (case-insensitive). Return `BuildSummary` for each — not the full `Build` object. The frontend fetches full builds individually via `GET /build/{id}`.

-----

## Reroll

Same as `generate_name()` but excludes the current name from the pool. Since generation is random with collision detection, just call `generate_name()` and add the current name to the exclusion set.

```python
def reroll(current_name: str) -> ProfileResult:
    """Generate a new name, excluding the current one."""
    return generate_name(exclude={current_name.strip().lower()})
```

-----

## Service API

### File: `backend/app/services/profile.py`

```python
from pydantic import BaseModel
import random
from pathlib import Path
import json
from difflib import get_close_matches


class ProfileResult(BaseModel):
    profile_name: str  # display format: "Dancing Happy Bear 🐻"
    animal_emoji: str  # just the emoji: "🐻"
    animal_name: str   # just the word: "bear"


class ProfileLookupResult(BaseModel):
    found: bool
    profile_name: str | None = None
    animal_emoji: str | None = None
    builds: list[dict] = []  # BuildSummary dicts
    suggestion: str | None = None


def generate_name(exclude: set[str] | None = None) -> ProfileResult:
    """
    Generate a three-word profile name with silent collision detection.
    
    Args:
        exclude: additional names to exclude (for reroll)
    
    Returns:
        ProfileResult with the generated name
    
    Raises:
        RuntimeError if unable to generate a unique name after retries
    """
    pass


def reroll(current_name: str) -> ProfileResult:
    """Generate a new name, excluding the current one."""
    pass


def lookup(name_query: str) -> ProfileLookupResult:
    """
    Look up a profile by name (case-insensitive, fuzzy-tolerant).
    
    Returns:
        ProfileLookupResult with found=True and builds list if matched,
        found=False with optional suggestion if close match exists,
        found=False with no suggestion if no match at all.
    """
    pass


def register_profile(profile_name: str) -> None:
    """Register a name in the active profiles set. Called after generation."""
    pass


def _load_existing_profiles() -> None:
    """Scan builds/ directory on startup to populate active profiles set."""
    pass


def _normalize(name: str) -> str:
    """Lowercase, strip, collapse spaces."""
    pass
```

-----

## Pydantic Models

Add to `backend/app/models/career.py` (or `api.py` if preferred — keep response models with the other models):

```python
class ProfileResult(BaseModel):
    profile_name: str
    animal_emoji: str
    animal_name: str


class ProfileLookupResult(BaseModel):
    found: bool
    profile_name: str | None = None
    animal_emoji: str | None = None
    builds: list[BuildSummary] = []
    suggestion: str | None = None


class BuildSummary(BaseModel):
    build_id: str
    school_name: str
    major_text: str
    career_title: str
    created_at: str
```

-----

## Router Integration (B1)

The profile router is defined in B1 (`backend/app/routers/profile.py`). Once this service exists, the router calls:

```python
from backend.app.services.profile import generate_name, reroll, lookup

@router.post("/")
async def create_profile():
    result = generate_name()
    return result

@router.post("/reroll")
async def reroll_profile(current_name: str):
    result = reroll(current_name)
    return result

@router.post("/lookup")
async def lookup_profile(request: ProfileLookupRequest):
    result = lookup(request.name_query)
    if not result.found and result.suggestion is None:
        raise HTTPException(status_code=404, detail="No matching profile found")
    return result
```

-----

## Build Integration

The `Build` model already has a `profile_name: str` field. When `POST /build` is called:

1. The `profile_name` from the request body is attached to the `Build` object
2. When `POST /build/{id}/save` persists the build, the profile name travels with it
3. When `profile.lookup()` scans for builds, it matches on this field

No schema changes to `Build` needed — `profile_name` is already there.

-----

## Startup Initialization

In `backend/app/main.py`, call `_load_existing_profiles()` on startup:

```python
from backend.app.services.profile import _load_existing_profiles

@app.on_event("startup")
async def startup():
    _load_existing_profiles()
```

-----

## Execution Checklist

1. **Read `backend/app/services/builds.py`** — understand save/load format and directory structure.
2. **Read `backend/app/models/career.py`** — confirm `Build.profile_name` exists.
3. **Create `backend/app/services/profile.py`** — full implementation with word pools, generation, collision detection, fuzzy lookup.
4. **Add `ProfileResult`, `ProfileLookupResult`, `BuildSummary`** to models.
5. **Update `backend/app/routers/profile.py`** (created in B1) to call the real service instead of returning 501.
6. **Add startup hook** in `main.py` to load existing profiles.
7. **Test manually** — generate names, check collisions, test fuzzy lookup with typos.

### What NOT to Do

- Do not add a database. JSON files in `builds/` + in-memory set is sufficient.
- Do not add rate limiting on name generation. 20K combinations, hackathon scale.
- Do not implement WebSocket push for name updates. HTTP request/response is fine.
- Do not use external fuzzy matching libraries (fuzzywuzzy, rapidfuzz). `difflib` is in the standard library and sufficient.
- Do not store any PII. The profile name IS the identity. Nothing else is collected.

-----

## Acceptance Criteria

- [x] `generate_name()` returns a `ProfileResult` with a three-word name in the format "adjective adjective animal 🐻"
- [x] Generated names use only words from the defined pools
- [x] Two consecutive calls to `generate_name()` return different names (probabilistic but near-certain with 20K combinations)
- [x] `reroll("dancing happy bear 🐻")` never returns "dancing happy bear 🐻"
- [x] `lookup("Dancing Happy Bear 🐻")` matches `"dancing happy bear 🐻"` (case-insensitive)
- [x] `lookup("dancin hapy bear")` returns a suggestion (fuzzy match)
- [x] `lookup("xyzzy nonsense platypus")` returns `found=False, suggestion=None`
- [x] After `generate_name()`, the name appears in `_active_profiles`
- [x] On server startup, existing build files are scanned and their profile names loaded
- [x] Profile endpoints in the FastAPI router return correct responses
- [x] No PII is stored anywhere

-----

*— End of Spec B2 —*
