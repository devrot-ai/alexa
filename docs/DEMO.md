# FreshKeep — 3-minute demo script

**Setup before recording:** both servers running, browser on
`http://localhost:8800`, judge panel visible, consent granted, demo seeded
(judge-panel → *Reset demo*). Mic works; typing fallback ready. Record at
1080p, single take, voice-over recorded separately if cleaner.

---

### 0:00–0:15 — The problem (hook)

> "The average family throws away fifteen hundred dollars of food a year —
> not because they don't care, but because no one remembers what's in the
> fridge. Typing it into an app with full grocery bags never happens.
> This is FreshKeep: we give Alexa+ a *memory for your kitchen*."

### 0:15–0:35 — The natural request

*(Cursor in the simulated Alexa+ box; speak or type — show both work.)*

> "Alexa, tell FreshKeep: *we just bought spinach, 500 grams of yogurt, and
> chicken breast that expires in 2 days.*"

*(Point at judge panel)* "Watch the right panel: that's a real MCP
`tools/call` — `track_food` — with structured arguments, over Streamable
HTTP. Alexa+ now *knows* my kitchen."

### 0:35–1:15 — The core Amazon-powered interaction

> "Alexa, ask FreshKeep: *what needs rescuing?*"

*(Rescue queue card renders: 4 items, days-left badges, $ at risk.)*

> "Four items at risk, most urgent first — and note the money figure:
> that's the value of food about to become trash."

### 1:15–1:50 — Meaningful action / orchestration

> "*Plan a rescue meal.*"

*(Recipe card renders.)*

> "FreshKeep picks a meal that uses exactly the at-risk items — deterministic,
> so it never hallucinates a recipe — and it notices I'm missing bread."

> "*Add bread to the shopping list.*"

*(Shopping-list card updates.)*

> "One sentence later, my shopping list already knows what the rescue meal needs."

### 1:50–2:20 — Result & measurable benefit

> "*Show my waste report.*"

> "Rescued versus wasted, in estimated dollars. For the demo household:
> zero waste this week, about ten dollars rescued. Scale that across a year
> and this is the $1,500 problem, shrinking."

### 2:20–2:40 — Privacy, consent, safety

*(Click 'Delete my data' chip, or type it.)*

> "Trust is designed in: nothing is stored before consent, and deletion is
> two-step — *delete my data*, then I must confirm explicitly. Even a
> prompt-injection attempt can't reach the delete tool; it isn't
> model-callable. The audit log records tool names — never what I said."

*(Confirm deletion; show emptied state.)*

### 2:40–3:00 — Why native to Amazon, why it scales

> "This is native to Amazon's ecosystem: an Alexa+ self-hosted MCP server is
> the official extension mechanism, the kitchen is Alexa's strongest room,
> and shopping lists are already an Alexa primitive. Swap one environment
> variable and the same server runs on DynamoDB; the optional Bedrock router
> handles messy phrasing with schema-validated tool calls and a deterministic
> fallback. FreshKeep is the memory layer your kitchen has never had."

---

## Exact demo inputs (copy-paste safe)

| Step | Utterance |
|---|---|
| 1 | `We just bought spinach, 500 g of greek yogurt, and chicken breast that expires in 2 days` |
| 2 | `What needs rescuing?` |
| 3 | `Plan a rescue meal` |
| 4 | `Add bread to the shopping list` |
| 5 | `Show my waste report` |
| 6 | `Delete my data` → `yes, delete everything` |

## Backup paths (if something fails live)

| Failure | Backup |
|---|---|
| Mic fails | Type everything — typing is a first-class path |
| Bedrock latency/error | Already automatic: trace shows `deterministic-fallback`; mention it as a feature |
| MCP server down | Simulator shows a friendly unreachable message; restart with `python -m freshkeep.mcpserver` |
| State got corrupted | Judge panel → **Reset demo** (one click) |
| Preview host blocked | Run locally: `python -m freshkeep.mcpserver` + `python -m freshkeep.simulator.app`, open `localhost:8800` |

## Screen-recording plan

1. OBS/QuickTime, 1080p30, window capture of the browser (full window so judge panel is visible).
2. Dry-run twice; third take is the recording.
3. Voice-over from the script above; keep under 2:55 total.
4. Upload public to YouTube; English; no third-party trademarks or music.
