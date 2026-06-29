# StyleMatch — Architecture

AI-powered pipeline that ingests Pinterest boards, extracts aesthetic profiles, and surfaces matching secondhand listings on Vinted.

---

## Tech Stack

- **Frontend:** Next.js (App Router) + Tailwind CSS
- **Backend:** Python FastAPI
- **Database:** Supabase (Postgres + file storage)
- **AI:** Anthropic API (claude-sonnet-4-6) — raw calls, no framework
- **Pinterest:** Official OAuth v5 API (`boards:read`, `pins:read`, `boards:write`, `pins:write`)
- **Vinted:** `vinted-api-wrapper` PyPI package (internal API wrapper); Apify fallback if wrapper breaks
- **Auth:** Google OAuth via NextAuth.js (frontend session); Pinterest OAuth token stored locally (not server-side)
- **Session store:** Supabase — user records created on first Google sign-in

---

## Architecture Decisions

### ADR-001: Raw Anthropic API over a framework
Using direct API calls instead of LangChain/LlamaIndex/Mastra. Rationale: forces explicit context window management and agent boundary decisions. Hiding those in a framework would defeat the learning purpose of this project.

### ADR-002: Pluggable SearchSource abstraction
Vinted integration is behind a `SearchSource` interface (`search(terms, filters) → [Listing]`). The agent pipeline never calls Vinted directly. Rationale: vinted-api-wrapper uses an undocumented internal API that can break without warning; Apify is the drop-in fallback with zero agent changes required.

### ADR-003: Parallel sub-agents for style analysis
The Style Analyst spawns N sub-agents in parallel, each receiving a batch of ~10 pins. Results are aggregated into a StyleProfile capped at 5 features. Rationale: a 200-pin board cannot fit in one context window; parallel batching is faster than sequential and produces more representative coverage than strategic sampling alone.

### ADR-004: style_context.md as living correction log
User feedback (accept/reject) is written back to `style_context.md` per session. This file is injected into the Style Analyst and Results Evaluator context on subsequent runs. Rationale: mirrors Zocdoc's `learning.md` pattern — the same mistake never happens twice.

### ADR-006: Google OAuth for user identity
User authentication is handled by Google OAuth via NextAuth.js. The session JWT is validated by FastAPI on protected API calls. User records (google_id, email) are persisted to Supabase on first sign-in. Rationale: avoids building custom auth; keeps the FastAPI side stateless (JWT verification only); Google sign-in has zero friction for the target user who likely already has a Google account open alongside Pinterest.

### ADR-005: 5 representative anchor pins passed to Results Evaluator
Rather than passing only the text StyleProfile, the evaluator receives 5 representative pin images alongside it. Rationale: the StyleProfile is a lossy compression of the board; visual anchors preserve signal that text descriptions lose (e.g. exact tone of "muted earth").

---

## Pipeline

```
AUTH GATE
  / (landing page — app description + "Sign in with Google")
         │ Google OAuth flow (NextAuth.js)
         ▼
  /setup (protected — unauthenticated visitors redirect to /)

INPUT LAYER
  Pinterest OAuth → board selector → user preferences (size, price, brands)
         │
         ▼
AGENT 1: STYLE ANALYST  [parallel sub-agents]
  • Spawns sub-agents, each receiving ~10 pins (images + metadata)
  • Each sub-agent returns a partial aesthetic description
  • Coordinator aggregates → StyleProfile (≤5 features) + 5 anchor pins
  • Writes StyleProfile to supabase; stores anchor pins by URL
         │ StyleProfile + [anchor_pin_urls]
         ▼
AGENT 2: QUERY TRANSLATOR
  • Input: StyleProfile + user prefs (size, price range, brands)
  • Output: 3–5 search strategies (keyword sets + Vinted filters)
  • Strategies run in parallel batches of 3–5 with rate-limit backoff
         │ [SearchStrategy]
         ▼
SEARCH EXECUTION LAYER  [deterministic, not an agent]
  • Executes each SearchStrategy via SearchSource
  • Deduplicates across strategies by listing ID
  • Returns raw listings with images
         │ [RawListing]
         ▼
AGENT 3: RESULTS EVALUATOR
  • Input: RawListings + StyleProfile + 5 anchor pin images
  • Scores each listing image against the aesthetic (0–10)
  • Returns score + one-sentence reasoning per listing
  • Threshold filter: surfaces listings scoring ≥ 6
         │ [ScoredListing]
         ▼
UI SURFACE  [Next.js]
  • Left panel: 5 anchor pins from your board
  • Right panel: ranked Vinted listings with score + reasoning
  • Feedback: ✓ love it / ✗ wrong vibe per listing
         │ UserFeedback
         ▼
AGENT 4: LEARNING LOOP
  • Parses feedback deltas (what was rejected and why)
  • Appends correction rules to style_context.md
  • e.g. "user rejects visible logos even when silhouette matches"
  • style_context.md is injected into Agent 1 + Agent 3 on next run
```

---

## Data Model

```
User
  id: uuid
  google_id: string
  email: string
  created_at: timestamp

StyleProfile
  id: uuid
  created_at: timestamp
  board_ids: string[]           # Pinterest board IDs analyzed
  features: StyleFeature[]      # max 5
  anchor_pin_urls: string[]     # 5 representative pins
  style_context_path: string    # path to style_context.md in storage

StyleFeature
  label: string                 # e.g. "muted earth tones"
  confidence: float             # 0–1, aggregated across sub-agents
  examples: string[]            # 2–3 pin URLs that best illustrate this feature

UserPreferences
  sizes: string[]
  price_min: float
  price_max: float
  brand_allowlist: string[]
  brand_blocklist: string[]

Listing
  id: string                    # Vinted listing ID
  title: string
  price: float
  brand: string
  size: string
  image_urls: string[]
  vinted_url: string
  score: float                  # set by Results Evaluator
  reasoning: string             # one sentence from evaluator
  feedback: "liked" | "disliked" | null
```

---

## Directory Structure

```
stylematch/
  frontend/                   # Next.js app
    app/
      page.tsx                # Landing page (app description + Google sign-in)
      setup/page.tsx          # Setup screen (board selector + prefs) — auth-gated
      results/page.tsx        # Results screen — auth-gated
      profile/page.tsx        # StyleProfile debug view — auth-gated
      api/auth/[...nextauth]/ # NextAuth.js route handler
    components/
    middleware.ts             # Redirects unauthenticated users to /
  backend/                    # FastAPI
    agents/
      style_analyst.py        # Agent 1 + sub-agent coordinator
      query_translator.py     # Agent 2
      results_evaluator.py    # Agent 3
      learning_loop.py        # Agent 4
    sources/
      base.py                 # SearchSource interface
      vinted.py               # vinted-api-wrapper implementation
      apify.py                # Apify fallback implementation
    routers/
      pipeline.py             # POST /pipeline/run
      feedback.py             # POST /feedback
      boards.py               # GET /boards (Pinterest)
      auth.py                 # Session validation middleware (JWT)
    lib/
      pinterest.py            # OAuth + boards/pins client
      context.py              # style_context.md read/write
      models.py               # Pydantic models
  data/
    style_context.md          # Living correction log (gitignored)
  CLAUDE.md
  ARCHITECTURE.md
  learning.md                 # Mistakes made during development
```

---

## Phase 2 (Planned)

Reverse pipeline: Vinted likes/purchases → aesthetic inference → Pinterest board creation.

Shares the Style Analyst agent (input-agnostic: receives images + behavioral signals, returns StyleProfile regardless of source). The Style Analyst is designed for this from day one — it does not assume Pinterest as input.

New in Phase 2: a content-search layer to find editorial/lookbook images to pin (the Pinterest write API requires a real source URL; generated images are not sufficient).