# SentiBoard frontend

Next.js App Router frontend for the SentiBoard sentiment analysis dashboard.

## Setup

1. Copy `.env.example` to `.env.local` and set `API_BASE_URL` to the FastAPI origin and the auth route paths supported by the backend.
2. Install dependencies with `npm install`.
3. Run `npm run dev` and open `http://localhost:3000`.

The login and registration forms submit to same-origin Next.js route handlers. Those handlers forward JSON to FastAPI and persist the returned `token` (or `access_token`) in an HttpOnly, SameSite=Lax cookie. Configure the cookie lifetime with `AUTH_COOKIE_MAX_AGE_SECONDS`; production deployments set the Secure flag automatically.

Client validation defaults can be adjusted with the `NEXT_PUBLIC_*` settings shown in `.env.example`. These checks improve feedback, but the backend must enforce its own validation and password policy.

The dashboard, analyze, history, and about routes are starter templates. They are not yet connected to their data endpoints.
