# Official-rule compliance checklist

Source of truth: https://amazonappdev2026.devpost.com/ (verified 2026-09-12).
**Re-verify every item before submitting.**

## Dates (both time zones, per builder requirement)

| Event | Pacific (PDT) | US Eastern (EDT) | Builder local (IST, Asia/Kolkata) |
|---|---|---|---|
| Submission deadline | **Fri Oct 23 2026, 12:00 PM** | Fri Oct 23 2026, 3:00 PM | **Sat Oct 24 2026, 12:30 AM (00:30)** |
| Buffer target (internal) | Wed Oct 21, 12:00 PM | Wed Oct 21, 3:00 PM | Thu Oct 22, 12:30 AM |

## Track requirement — Alexa+

| Requirement | Status | Evidence |
|---|---|---|
| Self-hosted MCP server, spec 2025-11-25+, Streamable HTTP | ✅ | `freshkeep/mcpserver.py`; SDK 2.2.0 advertises protocol 2026-07-28; raw `initialize` probe in README |
| Repo actually calls the track technology in code (import/entry point/config) | ✅ | `from mcp.server.mcpserver import MCPServer`, `server.run(transport="streamable-http")`, client imports in `mcpclient.py` |
| Simulated-experience path allowed; repo includes simulation source | ✅ | `freshkeep/simulator/` (FastAPI + single-file UI) |
| Agent Skill option | ✅ | `skill/SKILL.md` (format to be re-verified vs latest Alexa+ docs) |

## Submission materials

| Requirement | Status |
|---|---|
| Text description of what it does & how it works | ✅ draft: `docs/SUBMISSION.md` |
| Public GitHub repo w/ all source + instructions | 🔧 to publish (needs your confirmation — publishing is an external action) |
| Open-source license visible at top of repo | ✅ MIT in `LICENSE`; set in GitHub About section at publish time |
| Demo video **< 3 min**, public, English, YouTube/Vimeo | 🔧 script ready (`docs/DEMO.md`); recording is a human step |
| Product feedback for every tool used (incl. AWS) | ✅ `docs/PRODUCT_FEEDBACK.md` |
| Tracks & mini-challenges declared | ✅ Alexa+ primary; AWS Builder + Open Source mini |
| Pre-existing-code statement | ✅ N/A — project started during the window |
| Friction log (optional, up to +10% bonus) | ✅ `docs/FRICTION_LOG.md` (real entries only) |
| No third-party trademarks / copyrighted music in video | ✅ noted in recording plan |

## Mini-challenge requirements

| Challenge | Requirement | Status |
|---|---|---|
| AWS Builder | AWS services used with documented integrations | ✅ Bedrock router (`bedrock.py`) + DynamoDB store (`storage.py`), documented in README + ARCHITECTURE; honestly labeled which paths were live-verified |
| Open Source | New OSS project with license during window | ✅ MIT, fresh project |

## Judging criteria coverage

| Criterion | Where we score |
|---|---|
| Tech Implementation | Real MCP server+client on the wire; 29 tests incl. wire loop; schema-validated optional Bedrock; DynamoDB seam |
| Design | TV-distance-readable single-screen UX, consent modal, states (empty/loading/success/error), judge mode, mic + text fallback, keyboard-operable |
| Potential Impact | $1,500/yr household waste (USDA); in-app measurable rescued-vs-wasted; credible expansion path |
| Quality of the Idea | First agent-grade kitchen memory for Alexa+; platform-native (kitchen = Alexa's room; lists = Alexa primitive); deterministic safety story |

## Eligibility & housekeeping

- [ ] Participant above age of majority, non-excluded country (builder confirms)
- [ ] Registered on Devpost before deadline
- [ ] No paid cloud resources created without confirmation (none created in this workspace)
- [ ] Video uploaded public; repo public; links tested in a private browser window
- [ ] Submission entered under correct track + both mini-challenges
