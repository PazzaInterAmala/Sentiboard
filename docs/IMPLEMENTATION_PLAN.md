# SentiBoard – Implementation Plan

Working document: what we build, how it is structured, and in what order.
The product requirements live in [the functional spec](SentiBoard%20–%20App%20Workflow%20&%20Functional%20Spec.pdf);
this file turns them into concrete technical decisions and tasks. When a decision here changes, update this file in the same PR.

Related diagrams:
- [ER diagram](ER_Diagram_SentiBoard.png)
- [Use case diagram](SentiBoard_use_case.drawio.png)
- UI design: [Figma](https://www.figma.com/design/K4WiPtvj4P8CCat8cgw9jM/Untitled?node-id=0-1) and PNG exports in [design/](design/) – see §8.5

Legend: **[decided]** – agreed, build it this way. **[proposed]** – default we go with unless someone objects; see [Open questions](#12-open-questions).

---

## 1. Current status

| Area | State |
|---|---|
| Spec, ER diagram, use case diagram | done |
| UI design (Figma, by Roshan) | first version done, used as reference |
| Repo structure (`Backend/`, `Frontend/`, `ML/`) | placeholder folders only |
| Backend | not started |
| Frontend | not started |
| ML | not started |
| Deployment | not started |

---

## 2. Scope

**MVP (week 6):** register/login, analyze single text, keyword search on Reddit, CSV upload, query history, dashboard, CSV export, DistilBERT + baseline models.

**Nice to have:** compare models in the Text tab, admin `/models` page, dashboard filters (subreddit, date range).

Out of scope: languages other than English, real-time streaming, other sources than Reddit and CSV, password reset, email verification.

---

## 3. Tech stack

| Layer | Choice | Notes |
|---|---|---|
| Backend | Python 3.12, FastAPI, Uvicorn | **[decided]** FastAPI |
| ORM / migrations | SQLAlchemy 2.x + Alembic | **[proposed]** |
| Validation | Pydantic v2 (comes with FastAPI) | |
| Auth | JWT (PyJWT), bcrypt password hashing | **[proposed]** |
| Background jobs | FastAPI `BackgroundTasks` | **[proposed]** enough for MVP; jobs die on restart, see §6.3 |
| Reddit client | PRAW | **[proposed]** |
| DB | PostgreSQL 16 | **[decided]** Render |
| ML | PyTorch (CPU) + Hugging Face `transformers` for DistilBERT; scikit-learn for baseline | **[decided]** models, **[proposed]** libs |
| Frontend | Next.js (App Router) + TypeScript, Chart.js via `react-chartjs-2` | **[decided]** Next.js + Chart.js |
| Styling | Tailwind CSS | **[proposed]** |
| Tests | pytest (backend/ML), Playwright optional for frontend | |
| Hosting | Vercel (frontend), Render (backend + Postgres) | **[decided]** |

---

## 4. Repository layout

Keep the three top-level folders that already exist.

```
Sentiboard/
├── Backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, CORS, routers, startup (load models)
│   │   ├── config.py            # settings from env vars (pydantic-settings)
│   │   ├── db.py                # engine, session dependency
│   │   ├── models/              # SQLAlchemy models, one file per table
│   │   ├── schemas/             # Pydantic request/response models
│   │   ├── routers/             # auth.py, analyze.py, queries.py, models.py
│   │   ├── services/
│   │   │   ├── auth.py          # hashing, JWT, get_current_user
│   │   │   ├── reddit.py        # fetch_posts(keyword, limit, time_range)
│   │   │   ├── csv_import.py    # parse + validate uploaded CSV
│   │   │   ├── jobs.py          # run_keyword_job, run_csv_job
│   │   │   └── dashboard.py     # split, per-day, top words
│   │   └── ml/                  # thin adapter around ML/sentiboard_ml (see §7)
│   ├── alembic/                 # migrations
│   ├── tests/
│   ├── requirements.txt
│   └── .env.example
├── ML/
│   ├── sentiboard_ml/           # importable package used by the backend
│   │   ├── preprocess.py        # clean_text()
│   │   ├── predictor.py         # Predictor interface + implementations
│   │   ├── baseline.py
│   │   └── distilbert.py
│   ├── notebooks/               # EDA, experiments (not imported anywhere)
│   ├── train_baseline.py
│   ├── train_distilbert.py
│   ├── evaluate.py              # writes metrics JSON used to fill `models` table
│   └── requirements.txt
├── Frontend/
│   ├── src/app/                 # routes (see §8)
│   ├── src/components/
│   ├── src/lib/api.ts           # typed API client
│   ├── package.json
│   └── .env.example
└── docs/
```

Model weights are **not** committed to git (see §7.4). `.gitignore` currently only covers Python; add `node_modules/`, `.next/`, `ML/artifacts/`, `*.pt`, `*.safetensors`, `*.joblib` when the folders are created.

---

## 5. Database

Based on the ER diagram, with changes marked **[proposed]**.

### 5.1 Enums

| Enum | Values |
|---|---|
| `query_type` | `text`, `keyword`, `csv` |
| `query_status` | `pending`, `processing`, `done`, `failed` |
| `post_source` | `reddit`, `csv`, `manual` |
| `sentiment_label` | `negative`, `neutral`, `positive` |
| `user_role` **[proposed]** | `user`, `admin` |

### 5.2 Tables

**users**
| Column | Type | Notes |
|---|---|---|
| user_id | serial PK | |
| username | varchar(50) unique not null | |
| email | varchar(255) unique not null | stored lowercase |
| password_hash | varchar(255) not null | bcrypt |
| role | user_role not null default `user` | **[proposed]** needed for admin `/models` |
| created_at | timestamptz not null default now() | |

**search_queries**
| Column | Type | Notes |
|---|---|---|
| query_id | serial PK | |
| user_id | FK → users not null | |
| type | query_type not null | single text is also a query (type `text`), so it shows in History |
| keyword | varchar(100) | for `keyword`; for `text` – first 100 chars of the text |
| file_name | varchar(255) | for `csv` |
| params | jsonb | **[proposed]** `{limit, time_range}` or `{text_column}` |
| model_id | FK → models | **[proposed]** model used; dashboard reads predictions of this model only |
| status | query_status not null default `pending` | |
| error_message | text | **[proposed]** filled when `failed` |
| post_count | integer | set when job finishes |
| created_at | timestamptz not null default now() | |
| finished_at | timestamptz | |

**posts**
| Column | Type | Notes |
|---|---|---|
| post_id | serial PK | |
| external_id | varchar(50) | Reddit id (`t3_…`); null for csv/manual |
| source | post_source not null | |
| text | text not null | Reddit: `title + "\n\n" + selftext` |
| clean_text | text | output of `clean_text()` |
| author, subreddit | varchar(100) | Reddit only |
| url | varchar(500) | Reddit only |
| score | integer | Reddit upvotes |
| post_date | timestamptz | Reddit `created_utc`; csv: optional date column |
| created_at | timestamptz not null default now() | |

Constraint **[proposed]**: `UNIQUE (source, external_id)` instead of unique `external_id` alone (nulls are allowed multiple times in Postgres).

**query_posts** – `(query_id, post_id)` composite PK, both FK, `ON DELETE CASCADE`.

**predictions**
| Column | Type | Notes |
|---|---|---|
| prediction_id | serial PK | |
| post_id | FK → posts not null | |
| model_id | FK → models not null | |
| sentiment | sentiment_label not null | |
| confidence | numeric(5,4) not null | = max probability |
| prob_positive / prob_neutral / prob_negative | numeric(5,4) not null | **[proposed]** not null, both models return all 3 |
| created_at | timestamptz not null default now() | |

Constraint **[proposed]**: `UNIQUE (post_id, model_id)` – a post is predicted once per model; a repeated Reddit post is not re-predicted and is not double-counted.

**models**
| Column | Type | Notes |
|---|---|---|
| model_id | serial PK | |
| name | varchar(50) not null | `baseline`, `distilbert` |
| version | varchar(20) not null | e.g. `1.0` |
| accuracy, f1_score | numeric(5,4) | macro F1 on the test split |
| trained_at | timestamptz | |
| is_active | boolean not null default false | |

Constraints: `UNIQUE (name, version)`; **[proposed]** partial unique index `ON models (is_active) WHERE is_active` – at most one active model.

### 5.3 Indexes
- `search_queries (user_id, created_at desc)` – History page.
- `query_posts (post_id)` – reverse lookups.
- `predictions (post_id, model_id)` – covered by the unique constraint.

### 5.4 Migrations and seed
- Alembic is the only way to change the schema. First migration creates everything above.
- Seed script inserts the two rows into `models` from the metrics JSON produced by `ML/evaluate.py`, with `distilbert` active.

---

## 6. Backend

### 6.1 Auth
- `POST /auth/register` → hash password, create user, return user + token.
- `POST /auth/login` → verify, return token.
- JWT, HS256, payload `{sub: user_id, role, exp}`, lifetime 24 h, no refresh token in MVP.
- Every other endpoint uses dependency `get_current_user`; admin endpoints use `require_admin`.
- A user can only read their own queries; other ids return `404` (not `403`, to avoid leaking existence).

### 6.2 API contract

All bodies JSON unless noted. Header `Authorization: Bearer <token>` everywhere except register/login.
Error format for all errors: `{"detail": "human readable message"}` (FastAPI default).

| Method | Path | Request | Response |
|---|---|---|---|
| POST | `/auth/register` | `{username, email, password}` | `201 {user: User, token}` |
| POST | `/auth/login` | `{email, password}` | `{token}` |
| GET | `/auth/me` | – | `User` |
| POST | `/analyze` | `{text, compare: bool}` | `{query_id, results: [Prediction]}` (1 item, or 2 if compare) |
| POST | `/queries/keyword` | `{keyword, limit, time_range}` | `202 {query_id, status: "pending"}` |
| POST | `/queries/csv` | multipart: `file`, `text_column`, optional `date_column` | `202 {query_id, status: "pending"}` |
| GET | `/queries` | `?page&page_size` | `{items: [Query], total}` |
| GET | `/queries/{id}` | – | `Query` |
| GET | `/queries/{id}/dashboard` | – | `Dashboard` |
| GET | `/queries/{id}/posts` | `?page&page_size&label` | `{items: [PostWithPrediction], total}` |
| GET | `/queries/{id}/export` | – | `text/csv` file |
| GET | `/models` *(nice to have)* | – | `[Model]` (admin) |
| POST | `/models/{id}/activate` *(nice to have)* | – | `Model` (admin) |

Shapes:

```jsonc
// User
{ "user_id": 1, "username": "kirill", "email": "k@x.com", "role": "user", "created_at": "..." }

// Prediction
{ "model": "distilbert", "label": "negative", "confidence": 0.87,
  "probabilities": { "negative": 0.87, "neutral": 0.10, "positive": 0.03 } }

// Query
{ "query_id": 12, "type": "keyword", "keyword": "iPhone 17", "file_name": null,
  "params": { "limit": 100, "time_range": "week" },
  "status": "done", "post_count": 97, "error_message": null,
  "positive_share": 0.41,            // null unless done; shown in History badge
  "created_at": "...", "finished_at": "..." }

// Dashboard
{ "query": Query,
  "split":   { "positive": 0.41, "neutral": 0.33, "negative": 0.26 },
  "counts":  { "positive": 40,   "neutral": 32,   "negative": 25 },
  "per_day": [ { "date": "2026-10-20", "positive": 5, "neutral": 3, "negative": 2 } ],
  "top_words": { "positive": [ { "word": "camera", "count": 14 } ], "neutral": [...], "negative": [...] } }

// PostWithPrediction
{ "post_id": 5, "text": "...", "author": "...", "subreddit": "apple", "url": "...",
  "post_date": "...", "prediction": Prediction }
```

Input limits:
- `text`: 1–5000 chars.
- `keyword`: 1–100 chars; `limit`: 10–500, default 100; `time_range`: `day | week | month | year | all` (maps to PRAW `time_filter`).
- CSV: ≤ 5 MB, ≤ 5000 rows, UTF-8 (fallback latin-1), `text_column` must exist, empty rows skipped. Validation that can be done synchronously (size, header, column) returns `400` right away; per-row problems are skipped silently and counted.

### 6.3 Background jobs

```
POST /queries/keyword|csv
  └─ insert search_queries (status=pending, model_id=active model) → return 202 {query_id}
     └─ BackgroundTasks: run_*_job(query_id)
          status = processing
          1. get texts      (Reddit: fetch_posts / CSV: parsed rows)
          2. upsert posts   (reddit: ON CONFLICT (source, external_id) DO NOTHING, then select ids)
          3. insert query_posts
          4. for posts without a prediction for model_id:
                clean_text → predict in batches of 32 → insert predictions
          5. status = done, post_count, finished_at
        on any exception: status = failed, error_message = short message, log full traceback
```

- Each job opens its own DB session (not the request session).
- `0 posts found` is `done` with `post_count = 0`; the frontend shows the "no posts found" empty state.
- On backend startup, any query stuck in `pending`/`processing` is set to `failed` with `"Server restarted, please retry"` (BackgroundTasks die with the process).
- CSV file is parsed in the request handler and the rows are passed to the job in memory; the file itself is not stored. Export is generated from the DB.
- `/analyze` runs synchronously: creates a `text` query + `manual` post + prediction(s), status `done`.

### 6.4 Dashboard computations (`services/dashboard.py`)
All computed from predictions where `model_id = query.model_id`.
- **split / counts** – group by sentiment.
- **per_day** – group by `date(coalesce(post_date, created_at))`. If all posts fall on one day (typical for CSV without a date column) the frontend hides the line chart.
- **top_words** – tokens of `clean_text`, lowercase, drop stopwords (scikit-learn English list + `"http"`, `"amp"`, etc.), drop tokens shorter than 3 chars, drop the query keyword itself; top 10 per class. Computed on request; fine for ≤ 5000 posts.

### 6.5 Export
CSV columns: `text, label, confidence, prob_negative, prob_neutral, prob_positive, post_date, author, subreddit, url`. Filename: `sentiboard_<query_id>.csv`.

### 6.6 Configuration (env vars)
| Var | Example |
|---|---|
| `DATABASE_URL` | `postgresql+psycopg://…` |
| `JWT_SECRET` | random 32+ bytes |
| `JWT_EXPIRE_HOURS` | `24` |
| `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USER_AGENT` | from reddit.com/prefs/apps |
| `CORS_ORIGINS` | `http://localhost:3000,https://sentiboard.vercel.app` |
| `MODEL_DIR` | `/opt/models` |

Commit only `.env.example`; real `.env` is already in `.gitignore`.

---

## 7. ML

### 7.1 Task
3-class sentiment (negative / neutral / positive) on short English social-media text.

### 7.2 Data **[proposed]**
- Main: **TweetEval – sentiment** (Hugging Face `cardiffnlp/tweet_eval`, config `sentiment`): ~45k train / 2k val / 12k test, already 3 classes, social-media style.
- Optional sanity set: ~200 Reddit posts labeled by the team, to see how the model transfers from tweets to Reddit. Report it separately.

### 7.3 Models
| Model | Details | Target |
|---|---|---|
| baseline | TF-IDF (word 1–2 grams, min_df=2) + LogisticRegression (class_weight=balanced) | fast, explainable, macro F1 reference |
| distilbert | `distilbert-base-uncased` fine-tuned, max_len 128, 2–3 epochs, lr 2e-5 | main model, should beat baseline on macro F1 |

Metrics: accuracy and **macro F1** on the TweetEval test split → written to `ML/artifacts/<name>-<version>/metrics.json` and to the `models` table.

### 7.4 Artifacts
- `ML/artifacts/` is git-ignored.
- Baseline: single `model.joblib` (a few MB).
- DistilBERT: `save_pretrained` folder (~260 MB). Store on Hugging Face Hub (private repo) **[proposed]** and download at backend build/startup into `MODEL_DIR`.

### 7.5 Interface used by the backend

```python
# ML/sentiboard_ml/preprocess.py
def clean_text(text: str) -> str:
    """Lowercase, replace URLs with 'url', usernames/u/… with 'user',
    strip markdown and HTML entities, collapse whitespace. Emojis are kept."""

# ML/sentiboard_ml/predictor.py
LABELS = ("negative", "neutral", "positive")   # fixed order everywhere

@dataclass
class PredictionResult:
    label: str
    confidence: float
    probabilities: dict[str, float]   # keys = LABELS, sum ≈ 1

class Predictor(Protocol):
    name: str
    version: str
    def predict(self, texts: list[str]) -> list[PredictionResult]: ...

def load_predictor(name: str, path: str) -> Predictor: ...
```

- Both models are loaded once on backend startup and kept in a dict `{model_id: Predictor}`.
- `predict` takes already cleaned text; the backend calls `clean_text` first and stores the result in `posts.clean_text`.
- The same `clean_text` must be used for training and inference.
- DistilBERT inference: `torch.no_grad()`, batches of 32, `torch.set_num_threads` tuned for the Render instance.

---

## 8. Frontend

### 8.1 Routes
| Route | Page | Data |
|---|---|---|
| `/login`, `/register` | auth forms | `POST /auth/*` |
| `/` | Analyze: tabs Text / Keyword / CSV | `POST /analyze`, `/queries/keyword`, `/queries/csv` |
| `/history` | queries table | `GET /queries` |
| `/queries/[id]` | dashboard, or spinner while not `done` | `GET /queries/{id}` (poll 2 s), `/dashboard`, `/posts`, `/export` |
| `/models` *(nice to have)* | model table, activate button | `GET /models` |

All routes except login/register are wrapped in a layout with the sidebar (Analyze, History, Dashboard, Models – Models visible only for admin) and redirect to `/login` without a token.

### 8.2 Key components
`ResultCard` (badge green/grey/red + confidence + 3 bars), `SentimentPie`, `SentimentOverTime` (line), `TopWords` (3 lists or bar charts), `PostsTable` (paginated, label filter), `StatusBadge`, `EmptyState`, `ErrorState`.

### 8.3 Behaviour
- Token stored in `localStorage` **[proposed]** (simple; acceptable for a course project), sent by `lib/api.ts`. On `401` → clear token, go to `/login`.
- After starting a keyword/CSV job → navigate to `/queries/[id]`, which polls every 2 s until `done`/`failed`, then loads the dashboard.
- CSV tab reads the header row in the browser to fill the text-column dropdown before upload.
- Colours: positive green, neutral grey, negative red – same everywhere.
- Required empty/error states: no queries yet, query failed (show `error_message` + "Try again"), no posts found, backend unreachable.

### 8.4 Config
`NEXT_PUBLIC_API_URL` – backend base URL.

### 8.5 Design reference
[Figma](https://www.figma.com/design/K4WiPtvj4P8CCat8cgw9jM/Untitled?node-id=0-1) is the visual reference (style, layout, components), **not** a strict spec. Where it differs from this plan, this plan wins. Exports (1024–1280 px):

| File | Screen |
|---|---|
| [01_login.png](design/01_login.png) | Login |
| [02_register.png](design/02_register.png) | Register |
| [03_analyze_text.png](design/03_analyze_text.png) | Analyze → Text |
| [04_analyze_keyword.png](design/04_analyze_keyword.png) | Analyze → Reddit keyword |
| [05_analyze_csv_empty.png](design/05_analyze_csv_empty.png) | Analyze → CSV, no file yet |
| [06_analyze_csv_selected.png](design/06_analyze_csv_selected.png) | Analyze → CSV, file + column chosen |
| [07_dashboard.png](design/07_dashboard.png) | Dashboard |
| [08_history.png](design/08_history.png) | History |
| [09_about.png](design/09_about.png) | About (extra page, not in spec) |

Take from the design: colour palette, typography, sidebar layout, distribution bar, line chart, History list with status badges, CSV two-step flow.

Build differently from the design:
- Login/Register: no Google / SSO / "forgot password" / "remember device" in MVP; register form uses `username`, not "Full name". Drop the privacy marketing copy ("zero persistence…") – we do store history.
- Text tab: add the result card (§8.2) – not drawn in Figma.
- Dashboard "What people are saying": our model cannot summarise themes; show top 10 words per class + 2–3 most confident example posts per class instead. Line chart has 3 lines (incl. neutral), no event markers. Title = keyword or file name.
- Add screens not in Figma: processing/spinner state of `/queries/[id]`, posts table, empty and error states.
- Reddit field searches by keyword only (no `r/subreddit` syntax in MVP); time range options = `day | week | month | year | all`.
- CSV limit stays 5 MB, `.csv` only.

---

## 9. Deployment

Owner: Roshan; model artifacts on Hugging Face Hub: Kirill (see §10).

| Piece | Service | How |
|---|---|---|
| Frontend | **Vercel** | GitHub integration, root dir `Frontend/`. Auto-deploy from `main`, preview deploy for every PR. Env: `NEXT_PUBLIC_API_URL`. |
| Backend | **Render** Web Service, **Docker** runtime | `Backend/Dockerfile` (python:3.12-slim, CPU-only torch wheels). Start: `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT`. Auto-deploy from `main`. Health check: `GET /health`. |
| Infra as code | **`render.yaml`** (Render Blueprint) at repo root | Describes web service + Postgres + env vars, so the setup is reproducible and reviewed in PRs. |
| DB | **Render PostgreSQL** | `DATABASE_URL` linked into the backend by the blueprint. Free Postgres on Render is time-limited – check current terms; fallback: Neon free tier. |
| Model weights | **Hugging Face Hub** (private model repo) | ML pushes `baseline` + `distilbert` artifacts with a version tag; Docker build downloads them using `HF_TOKEN` (build secret) into `MODEL_DIR`. |
| CI | **GitHub Actions** | On PR: `ruff` + `pytest` (Backend, ML), `npm run lint` + `npm run build` (Frontend). Deploys themselves are done by Vercel/Render auto-deploy, not by Actions. |
| Secrets | Render env group, Vercel env vars, GitHub Actions secrets | Never in git; `.env.example` documents names. |

Environments: `local` (docker compose with Postgres) → `preview` (Vercel PR previews against production API) → `production`. A separate staging backend is not needed for the course.

**Memory risk:** PyTorch + DistilBERT need roughly 1 GB RAM. Render Free and Starter instances have 512 MB (Free also sleeps when idle, ~1 min cold start). Options, in order: (1) export DistilBERT to ONNX + dynamic int8 quantization and run with `onnxruntime` (~70–100 MB model, fits in 512 MB together with the app) – preferred, (2) paid Standard instance (2 GB), (3) run the model as a separate inference service on a Hugging Face Space (free CPU, 16 GB RAM) called by the backend over HTTP, (4) only baseline in production, DistilBERT locally for the demo. Decide by end of week 3 after measuring.

---

## 10. Work plan

### 10.1 Roles **[proposed]**

| Person | Owns | Folders |
|---|---|---|
| **Kirill** | **ML**: data, `clean_text`, baseline, DistilBERT, evaluation, `sentiboard_ml` package, ONNX export, publishing model artifacts to Hugging Face Hub. **ML in the backend**: `app/ml/` adapter (load models on startup, batch predict), seeding the `models` table, and the analytics in `services/dashboard.py` (split, per-day, top words, example posts). | `ML/`, `Backend/app/ml/`, `Backend/app/services/dashboard.py` |
| **Sirio** | **Backend core**: FastAPI app, DB models + Alembic, auth, `/analyze`, Reddit client, background jobs, CSV import, all endpoints incl. dashboard/posts/export routes, backend tests. | `Backend/` (rest) |
| **Roshan** | **Frontend**: Next.js app, all screens per §8 and the Figma reference, charts, polling, empty/error states, design updates. **Deployment + CI/CD**: Vercel, Render, Postgres, `Backend/Dockerfile`, `render.yaml`, GitHub Actions, secrets/env vars. Helps on backend where needed (e.g. CORS, health check, export endpoint). | `Frontend/`, `Backend/Dockerfile`, `render.yaml`, `.github/` |

Why this split: Roshan made the design and is comfortable with frontend, deployment and CI/CD, so they own everything the user sees and everything that ships. Backend core is the biggest part, so Sirio gets it in full. Kirill's ML training is front-loaded (weeks 1–3); in weeks 3–5 the focus moves to wiring the models into the backend and the dashboard analytics, which takes load off Sirio.

Contracts between people (change only together, in a PR reviewed by both sides):
- Kirill ↔ Sirio: `clean_text` / `Predictor` interface (§7.5) and `services/dashboard.py` function signatures.
- Sirio ↔ Roshan: API contract (§6.2) – Roshan mocks it until the real endpoints exist; env vars (§6.6).
- Kirill ↔ Roshan: where model artifacts live and how the Docker build downloads them (§7.4, §9); RAM budget.

Every PR is reviewed by one of the other two.

### 10.2 Timeline

Week numbers count from the spec date (week 1 = week of Oct 6, 2026). Adjust if the course calendar says otherwise.

| Week | Sirio – Backend core | Kirill – ML + ML in backend | Roshan – Frontend + Deploy/CI |
|---|---|---|---|
| 1–2 | project skeleton, config, DB models + first Alembic migration, auth endpoints, `/auth/me` | data loading + EDA, `clean_text`, baseline trained + metrics, `Predictor` interface with baseline | Next.js skeleton, layout + sidebar, login/register pages, API client with mocks; create Vercel/Render accounts, team access; GitHub Actions (lint + tests) |
| 3 | `/analyze`, Reddit service, keyword job, `/queries`, `/queries/{id}` | DistilBERT fine-tuning + evaluation; `app/ml/` adapter (load on startup, batch predict); measure RAM | Analyze page: Text tab with `ResultCard`, Keyword tab, polling page; local `docker compose` (backend + Postgres) |
| 4 | CSV upload + job, `/dashboard`, `/posts`, `/export` routes, startup recovery of stuck jobs | `services/dashboard.py` (split, per-day, top words, examples); seed `models` table; push artifacts to HF Hub; decide memory option (§9) with Roshan | History + Dashboard pages, CSV tab; Dockerfile + `render.yaml`, first deploy of backend + DB, Vercel project |
| 5 | tests for jobs and endpoints, fixes after first deploy | ONNX export if needed, Reddit sanity set evaluation, dashboard tests | empty/error states, polish, switch from mocks to production API; prod env vars, CORS, model download in build |
| 6 | bug fixes, end-to-end test on production | final metrics table for the report | bug fixes, deploy monitoring, demo scenario |
| if time | compare mode, `/models` endpoints | comparison metrics, model admin data | compare toggle, Models page, dashboard filters |

Dependencies to watch: Sirio's `/analyze` needs Kirill's baseline `Predictor` (end of week 2); Roshan's first deploy (week 4) needs Kirill's artifacts on HF Hub and Sirio's app starting cleanly.

### 10.3 MVP checklist

- [ ] Register, login, logout, protected routes
- [ ] Analyze single text → result card, saved to history
- [ ] Keyword search → background job → dashboard
- [ ] CSV upload → background job → dashboard + download
- [ ] History with status badges and Open
- [ ] Dashboard: 3 summary cards, split chart, sentiment over time, top 10 words per class, posts table
- [ ] Export CSV
- [ ] Baseline and DistilBERT trained, metrics in `models` table
- [ ] Empty and error states
- [ ] Deployed: Vercel + Render

---

## 11. Conventions
- Branches: `feature/<area>-<short-name>` (e.g. `feature/backend-auth`), PR into `main`, at least one review.
- Python: `ruff` for lint + format; type hints in `app/` and `sentiboard_ml/`.
- TypeScript: `eslint` + `prettier` from the Next.js template.
- API changes: update §6.2 in this file in the same PR.
- Secrets never in git; `.env.example` lists every variable.

---

## 12. Open questions
1. Accept the schema changes marked **[proposed]** in §5 (`role`, `params`, `model_id`, `error_message` on queries; `UNIQUE (source, external_id)`; `UNIQUE (post_id, model_id)`; single active model)? → then update the ER diagram.
2. Dataset: TweetEval sentiment OK, or does the course require a specific one?
3. Registering a new model version (use case diagram): admin UI, or a CLI/seed script only? Proposed: script only; UI just lists models and switches the active one.
4. CSV: support an optional date column so "sentiment over time" works for CSV?
5. Render plan / memory budget for DistilBERT (§9).
6. Roles in §10.1 – confirm with Sirio and Roshan.
