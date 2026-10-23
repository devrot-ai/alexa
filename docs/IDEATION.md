# FreshKeep — Opportunity Analysis (Phase 1–3)

*Build, Ship, Shape: Amazon Developer Hackathon 2026 · Prepared 2026-09-12*

Verified against the official page (amazonappdev2026.devpost.com):

| Fact | Value |
|---|---|
| Deadline | **Oct 23 2026, 12:00 PM PDT** (3:00 PM EDT) = **Oct 24 2026, 00:30 IST** (Asia/Kolkata) |
| Prize pool | $138,000 cash + AWS credits ≈ $190K combined value |
| Alexa+ 1st place | $25,000 cash + $15,000 AWS credits + 1:1 with Amazon Developer team |
| Alexa+ track requirements | Self-hosted MCP server (spec **2025-11-25+**, Streamable HTTP) **or** Agent Skill **or** simulated Alexa+ experience in a web app |
| Mini-challenges | AWS Builder; Open Source. Friction log = up to **+10% judging bonus** |
| Judging | Tech Implementation · Design · Potential Impact · Quality of the Idea |
| Submission | text description, public GitHub repo w/ OSS license, demo video **< 3 min** (English), product feedback for every tool used, tracks declared |

---

## 1. Concept generation (12 concepts across domains)

| # | Concept | Track | Target user | Problem (freq × severity) | Why existing solutions fail | Amazon fit | Wow demo moment |
|---|---------|-------|-------------|---------------------------|-----------------------------|------------|-----------------|
| 1 | **FreshKeep** — Alexa+ gets persistent kitchen memory: tracks what you bought, warns before food spoils, turns expiring items into a rescue meal + shopping list | Alexa+ | Households that cook (esp. families, busy professionals) | Food waste: daily occurrence, ~$1,500/yr per US family wasted; 30–40% of food supply wasted (USDA). High freq, medium-high severity, universal | Pantry apps (NoWaste, Pantry Check) need *typed manual entry* at the worst moment (hands full, groceries out). Nobody maintains them. No voice-first, agent-grade memory exists | Kitchen = natural Alexa room; shopping lists are already an Alexa primitive; MCP gives Alexa+ persistent structured memory | "Alexa, what needs rescuing?" → 3 expiring items → concrete dinner plan from what you own → missing 2 ingredients auto-added to shopping list |
| 2 | CareLoop — medication adherence + family caregiver alerts | Alexa+ | Adult children caring for aging parents | High severity, daily | Pill dispensers are dumb; no closed loop between senior's voice device and caregiver | Strong | "Alexa, did Mom take her pills?" |
| 3 | Arrival Guardian — Ring-based "got home safe" digest for caregivers | Ring | Families / caretakers (Ring priority: caretaking) | Medium freq, high anxiety | Raw event streams, no summarization or escalation logic | Good | "Ring saw Priya got home at 4:12; here's your day digest" |
| 4 | Family Standup — Bee recordings → shared family task board | Bee | Busy households | Weekly | Notes apps don't listen; Bee data unused at home level | Good | Spoken plan → auto-assigned chores |
| 5 | DevRecap — Bee standup recordings → PR/changelog digest | Bee | Engineering teams (Bee priority: dev experience) | Weekly | Meeting notes rot | Medium | standup → changelog |
| 6 | Family Hub TV — calendar/chores/meal dashboard | Fire TV | Families | Daily low-grade | Phone calendars aren't shared, glanceable, or hands-free | Medium | Living-room family dashboard |
| 7 | PhysioCoach — Fire TV rehab exercises w/ camera rep counting | Fire TV | Post-injury patients | 3×/week | Paper sheets, zero feedback | Weak-medium (CV + camera privacy) | Live rep counter |
| 8 | ReadyRadar — household emergency-preparedness briefings | Fire TV + Alexa | Households in risk zones | Seasonal, high severity | Static checklists nobody updates | Medium | Storm-mode briefing |
| 9 | PorchPilot — Ring package-delivery concierge | Ring | Online shoppers | Weekly | Ring app shows clips, no orchestration | Good | "Package secure; porch clear" digest |
| 10 | EnergyShift — peak-hour energy coaching | Alexa+ | Cost-conscious households | Daily | Utility apps are passive | Medium | "Run dishwasher after 9pm, save ₹40" |
| 11 | StoryBridge — long-distance family storytelling skill | Alexa+ | Grandparents/grandkids | Weekly | Calls feel like interrogations | Medium | Guided memory exchange |
| 12 | NightOwl — walk-to-door camera escort for solo arrivals | Ring | People arriving home late | Medium freq | Nothing exists | Weak (privacy minefield) | Camera-lit safe walk-up |

## 2. Weighted decision matrix

Weights: user value **.18** · platform fit **.16** · technical feasibility **.18** · demo strength **.14** · originality **.12** · judging differentiation **.10** · scalability **.06** · safety/low-risk **.06** (10 = minimal risk)

| Concept | UV | PF | TF | DS | OR | JD | SC | RS | **Weighted Σ** |
|---|---|---|---|---|---|---|---|---|---|
| **1. FreshKeep** | 8 | 9 | 9 | 9 | 8 | 8 | 8 | 9 | **8.54** ✅ |
| 2. CareLoop | 9 | 9 | 6 | 7 | 7 | 7 | 8 | 4 | 7.38 |
| 3. Arrival Guardian | 8 | 8 | 5 | 6 | 7 | 6 | 7 | 5 | 6.62 |
| 4. Family Standup (Bee) | 7 | 8 | 3 | 7 | 8 | 7 | 7 | 7 | 6.56 |
| 9. PorchPilot | 7 | 8 | 5 | 6 | 6 | 5 | 6 | 6 | 6.22 |
| 8. ReadyRadar | 6 | 6 | 7 | 6 | 6 | 5 | 5 | 7 | 6.08 |
| 11. StoryBridge | 5 | 7 | 8 | 6 | 5 | 4 | 5 | 8 | 6.08 |
| 6. Family Hub TV | 6 | 7 | 7 | 6 | 4 | 4 | 6 | 8 | 6.02 |
| 10. EnergyShift | 7 | 7 | 4 | 5 | 6 | 5 | 7 | 7 | 5.86 |
| 7. PhysioCoach | 7 | 7 | 3 | 7 | 6 | 6 | 6 | 4 | 5.82 |
| 5. DevRecap (Bee) | 6 | 7 | 3 | 6 | 7 | 6 | 6 | 7 | 5.80 |
| 12. NightOwl | 6 | 7 | 4 | 6 | 6 | 5 | 5 | 3 | 5.46 |

## 3. Decision

**Selected: FreshKeep (8.54).** Rejection notes for the finalists:

- **CareLoop (7.38)** — highest raw user value, but health/medication data raises safety and liability risk: a missed-dose false negative is genuinely harmful, the demo needs disclaimers that blunt the wow moment, and judges score "safe, reliable" harshly in health domains.
- **Bee concepts (6.6/5.8)** — rules require the demo to show *real Bee device data*; we don't own a Bee. Disqualified on feasibility, not merit.
- **Ring concepts (6.6/6.2/5.5)** — caretaking is a priority category, but demos depend on simulated camera/doorbell events around sensitive home data; harder to make a judge *feel* value in 60 s, and privacy review friction is real.
- **Fire TV concepts (6.0/6.0/5.8)** — feasible, but the Family Hub idea is crowded (weak originality), PhysioCoach needs reliable computer vision we can't validate here, and none exploit AWS/Alexa+ depth the way FreshKeep does.

**Why FreshKeep wins:**
1. **Platform-native, not bolted on.** The kitchen is Alexa's strongest room; shopping lists and timers are already Alexa primitives. FreshKeep adds the one thing Alexa+ MCP uniquely enables: *persistent, structured, household-shared memory* plus tool use.
2. **Verifiable tech depth in 60 s.** A judge hears one sentence → sees the exact MCP tool call with JSON schema → sees state change in DynamoDB/local store → sees a write-back action (shopping list). Full agent loop, visible.
3. **Low-risk domain.** No health, legal, financial, or safety-critical claims; no camera data; consent and delete-data are still implemented and demoed.
4. **Deterministic core.** The rescue planner is a rules engine — the demo never depends on an LLM not hallucinating. Bedrock enhances language, never controls actions.
5. **Credible impact math.** USDA: 30–40% of food supply wasted; average US family wastes ≈$1,500/yr. The app reports money saved per household — a measurable outcome judges can quote.

## 4. Track & mini-challenges

- **Primary track: Alexa+** — implemented as *all three permitted paths*: (a) a **self-hosted MCP server** (spec 2026-07-28 via official SDK ≥ required 2025-11-25, Streamable HTTP), (b) an **Agent Skill** definition (`skill/SKILL.md`), and (c) a **simulated Alexa+ experience** web app that acts as a real MCP client.
- **Mini-challenge: AWS Builder** — Bedrock (optional natural-language planner) + DynamoDB adapter + structured CloudWatch-style logs, all documented.
- **Mini-challenge: Open Source** — MIT license, public-ready repo.
- **Friction log** maintained for the +10% bonus (`docs/FRICTION_LOG.md`), real entries only.

## 5. Product specification (Phase 3)

| Field | Definition |
|---|---|
| **Name** | FreshKeep |
| **One-liner** | *FreshKeep gives Alexa+ a memory for your kitchen — it knows what you bought, warns you before food spoils, and turns expiring ingredients into tonight's dinner.* |
| **Persona** | Ananya, 34, product manager in Kolkata, cooks 4×/week for a family of four, throws away wilted greens and forgotten leftovers every week and hates it. |
| **Main problem** | Food gets bought, forgotten, and thrown away because no household memory exists that costs zero effort to maintain. |
| **Primary journey** | Say what you bought → FreshKeep tracks freshness → "What needs rescuing?" → rescue meal plan from what you own → missing ingredients appended to shopping list → mark cooked/thrown → weekly waste report shows money saved. |
| **Wow moment (60 s)** | *"Alexa, ask FreshKeep what needs rescuing"* → 3 at-risk items with days-left → a concrete rescue recipe using exactly those items → *"Add what I'm missing"* → 2 ingredients appear on the shopping list. |
| **Core feature** | Voice-first food tracking + rescue queue + rescue-meal planner with shopping-list write-back. |
| **Supporting features** | (1) `mark_used` / `mark_thrown` lifecycle + waste report with $ saved; (2) consent gate, audit log, and one-command data deletion; (3) judge mode showing live MCP tool-call traces. |
| **Measurable outcome** | Demo household: 0 items thrown away during demo week; ≥$X of food "rescued"; waste report shows week-over-week waste ↓. |
| **Limitations** | No receipt/barcode scanning (v1); single household per server instance; recipe corpus is a curated rule set, not a generative search engine; no Alexa account linkage in hackathon build (shopping list is local + export); no production auth beyond demo bearer token. |
| **Future expansion** | Receipt photo ingestion (Amazon Textract/Rekognition), Alexa Lists API write-back, multi-household + Cognito, Fire TV kitchen dashboard, Ring "groceries arrived" trigger, seasonal pricing of rescue meals. |

**Beginning-middle-end:** (1) user says what they bought → (2) system confirms with parsed structured data, asking nothing unless ambiguous → (3) MCP tools persist + compute freshness → (4) user asks what to rescue and gets an actionable plan → (5) user can add missing items to the shopping list, mark items used/thrown, view the waste report, or delete everything.
