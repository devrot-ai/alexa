# Deploying the "try it out" instance on Render (free tier)

Verified before writing this: `render.yaml` parses, the exact container CMD
(both processes) runs, and the app honors platform-injected `PORT`.

## Prerequisites
- Repo pushed to GitHub (see `docs/PUBLISH.md`), **public**.
- A free account on https://render.com (sign in with GitHub).

## Steps

1. **Dashboard → New → Web Service** → connect your GitHub account →
   select the `freshkeep` repo.
2. Render auto-detects `render.yaml` at the repo root and pre-fills:
   - Runtime: **Docker** (uses `./Dockerfile`)
   - Plan: **Free**
   - Health check path: `/healthz`
   - Env var: `FRESHKEEP_REQUIRE_CONSENT=1`
   If it asks instead of pre-filling, set exactly those values manually
   (Dockerfile path `./Dockerfile`).
3. Click **Create Web Service** (or "Apply" for Blueprint mode).
4. Watch the build logs: pip installs deps, image builds, then you'll see
   `FreshKeep MCP server starting on http://0.0.0.0:8811/mcp` and
   `FreshKeep simulator on http://0.0.0.0:<PORT>`.
5. Health check passes → service goes **Live**.

## Your try-it-out URL

`https://freshkeep.onrender.com` (name-dependent — copy from the Render header).

Paste it into the Devpost submission "try it out" field, and add this note in
the description: *"The hosted demo runs the same MCP server + client as the
repo; after ~15 min idle the free instance sleeps, so the first load may take
~30 s — after that it's instant."*

## Smoke-test the deployed instance

```bash
curl https://freshkeep.onrender.com/healthz
# {"ok":true,"invoker":"mcp-streamable-http http://127.0.0.1:8811/mcp",...}
```
Then in the browser: consent → **Seed demo kitchen** → "What needs rescuing?"
→ judge panel should show MCP traces.

## Free-tier behaviors (know them before judging)

- Instance sleeps after ~15 min idle; first request cold-starts (~30–60 s).
  Ping `/healthz` once before your demo video / judge session.
- The JSON store resets when the instance redeploys/sleeps (ephemeral disk).
  That's fine — judges use **Seed demo kitchen**. For persistent state, add
  the DynamoDB env vars from `render.yaml` comments + IAM keys
  (`docs/AWS_SETUP.md`), which also strengthens the AWS Builder entry.
- Free tier = 750 hours/month; one service is comfortably within it.

## If the deploy fails

| Symptom | Fix |
|---|---|
| "Could not find Dockerfile" | Set Root Directory blank, Dockerfile path `./Dockerfile` |
| Health check failing | Check logs for the two process banners; confirm `PORT` is not pinned to 8800 anywhere |
| 502 on first load | Cold start — retry after 60 s |
| MCP unreachable banner in UI | MCP process didn't start; check log line for :8811 |
