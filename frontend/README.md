# Epidemiological Intelligence -- Frontend

Next.js (App Router) + TypeScript + Tailwind CSS. See `AGENTS.md` for
Next.js 16-specific behavior notes.

## Running locally

```bash
npm install
cp .env.example .env.local   # optional: only needed to hit the real FastAPI backend
npm run dev
```

Open http://localhost:3000. `NEXT_PUBLIC_API_URL` (default
`http://localhost:8080`) points `services/api.ts` at the FastAPI
service in `ai/`. Only `/`, `/health` and `/chat` exist there today --
everything else in this app reads from `mocks/` via the `services/*Service.ts`
functions. Each of those has a `TODO: backend endpoint required` comment
pointing at the real GCS/BigQuery logic it will eventually call.

**The Agente IA page will fail to reach a locally-running FastAPI
instance from the browser** until CORS is configured there (no
`CORSMiddleware` in `ai/src/epidemiological_agent/api/app.py`) -- this
is a known, documented limitation, not a bug in this app.

## Validation

```bash
npm run lint
npm run build
```

Both pass as of this writing; 5 routes prerender as static.
