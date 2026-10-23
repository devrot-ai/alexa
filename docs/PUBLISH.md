# Publishing the repo (you push — step by step)

## 1. Create the empty repo on GitHub

New repository → name: `freshkeep` (or `freshkeep-alexa-mcp`) → **Public** →
do NOT add README/license/.gitignore (they already exist here).

## 2. Push from this workspace

```bash
cd freshkeep
git init -b main
git add -A
git commit -m "FreshKeep: kitchen memory for Alexa+ (Build, Ship, Shape hackathon 2026)"
git remote add origin https://github.com/<YOUR_USERNAME>/freshkeep.git
git push -u origin main
```

Sanity check before pushing: `git status --ignored` should show `data/` and
`.env` ignored; verify no `.env` is staged (`git ls-files | grep -i env`
should only list `.env.example`).

## 3. GitHub About section (rules require the license visible at the top)

- Description: `FreshKeep gives Alexa+ a memory for your kitchen — track groceries by voice, rescue food before it expires, plan dinner from what's dying. Self-hosted MCP server for the Amazon Developer Hackathon 2026.`
- Topics: `alexa-plus`, `mcp`, `model-context-protocol`, `hackathon`, `aws`, `bedrock`, `food-waste`, `amazon-devpost-2026`
- License: GitHub auto-detects MIT from `LICENSE` — confirm the About card shows **MIT License**.

## 4. Before you submit on Devpost

- [ ] Repo is public and loads cleanly in a private browser window
- [ ] README quickstart works on a fresh machine (or note exact Python version: 3.11+; tested on 3.13)
- [ ] Demo video < 3:00, public, English, uploaded to YouTube/Vimeo
- [ ] `docs/SUBMISSION.md` text pasted into the description field
- [ ] Product feedback answer pasted from `docs/PRODUCT_FEEDBACK.md`
- [ ] Friction log: attach/paste `docs/FRICTION_LOG.md` (bonus points)
- [ ] Tracks: Alexa+ · Mini-challenges: AWS Builder + Open Source (with repo URL)
- [ ] Deadline check: **Oct 23 2026 12:00 PM PDT = Oct 24 2026 00:30 IST**
