# SentiBoard frontend

Next.js 15 (App Router) + TypeScript + Tailwind. Visual language follows `DESIGN.md` ("Editorial Analytical": Newsreader + Inter, ivory canvas, ink navy, cobalt for actions, muted sentiment colours).

## Setup

1. Copy `.env.example` to `.env.local` and set `API_BASE_URL` to the FastAPI origin (default `http://localhost:8000`).
2. `npm install`
3. `npm run dev` and open http://localhost:3000

## How it talks to the backend

- Login/register post to `/api/auth/*`. Those route handlers call FastAPI and store the returned JWT in an HttpOnly, SameSite=Lax cookie. `/api/auth/logout` clears it.
- Every other call goes to `/api/backend/<path>` (`app/api/backend/[...path]/route.ts`), which forwards to `API_BASE_URL/<path>` with `Authorization: Bearer <token>`. JSON, multipart (CSV upload) and file downloads (CSV export) pass through unchanged. A 401 clears the cookie and the client sends the user to `/login`.
- `middleware.ts` redirects signed-out visitors to `/login?next=…` (About, Login and Register are public).
- Typed client: `lib/api.ts`; response types mirror `Backend/app/schemas` in `lib/types.ts`.

## Screens

| Route | Screen | Backend |
|---|---|---|
| `/analyze` | Text tab: single text → model result card(s); "Compare models" runs the second registered model | `POST /analyze` |
| `/analyze?tab=reddit` | Keyword, sample size (10–500), time window | `POST /queries/keyword` |
| `/analyze?tab=csv` | Drop zone → column mapping → preview → pre-flight checks (≤ 5 MB, ≤ 5000 rows) | `POST /queries/csv` |
| `/history` | Paginated list with status badges and search; refreshes while jobs run | `GET /queries` |
| `/queries/[id]` | Polls every 2 s while running; then summary, split, trend line, top words, example posts, posts table, CSV export | `GET /queries/{id}`, `/dashboard`, `/posts`, `/export` |
| `/about` | How SentiBoard works | – |

Routes from the plan that the API does not have yet (keyword/CSV jobs, dashboard, posts, export) show an "not available on the API yet" notice instead of an error, so the UI works against the current backend branch and lights up as endpoints land.
