# Continuous integration

The workflow lives in [`.github/workflows/ci.yml`](../.github/workflows/ci.yml). It runs on every push to `main` and every pull request that targets `main`.

**It only checks code.** It does not deploy, publish images, upload build artifacts or read repository secrets. The `GITHUB_TOKEN` is read-only (`permissions: contents: read`), and a newer push to the same branch or PR cancels the older run.

## What it checks

Two jobs run in parallel. A job fails if any of its steps fail, except the one step marked informational.

### `frontend` (working directory `frontend/`, Node 24, npm)

| Step | Command |
|---|---|
| Install | `npm ci` (npm cache keyed on `package-lock.json`) |
| Lint | `npm run lint` (ESLint, `eslint-config-next`) |
| Types | `npm run typecheck` (`next typegen && tsc --noEmit`) |
| Tests | `npm test` (Vitest) |
| Build | `npm run build` (Next.js production build) |

There is no format check because no frontend formatter (such as Prettier) is configured. `API_INTERNAL_URL` is set to an address where nothing is listening. That works because every route renders on demand, so the build never calls the API.

### `backend` (working directory `backend/`, Python 3.12, uv)

| Step | Command |
|---|---|
| Install | `uv sync --frozen` (fails if `uv.lock` is out of date; uv cache keyed on `uv.lock`) |
| Format | `uv run ruff format --check .` |
| Lint | `uv run ruff check .` |
| Types | `uv run mypy app`, **informational** (see below) |
| Test database | `CREATE DATABASE propcheck_ci_test` |
| Migrations | `uv run alembic upgrade head` on the CI database |
| Drift check | `uv run alembic check` (fails if the models changed without a migration) |
| Tests | `uv run pytest` |

#### Database

The job starts a throwaway `postgres:16-alpine` **service container** that exists only for that run. Its user, password and database names are CI-only values written in the workflow (`propcheck_ci`). They are not secrets and match nothing in any real environment.

- `DATABASE_URL` → `propcheck_ci`. Migrations are applied here with the Alembic CLI.
- `TEST_DATABASE_URL` → `propcheck_ci_test`. `tests/conftest.py` drops and rebuilds this schema from the migrations, then runs each test inside a transaction that is rolled back.

Both URLs use `postgresql+asyncpg`, which is the app's async driver (SQLAlchemy `AsyncSession`). No sync driver is installed or used. Nothing is seeded (`app.seed` is never run in CI), and no CI job can reach a production database.

`backend/scripts/e2e_journey.py` needs a running, seeded stack, so it is not part of CI.

#### mypy is informational for now

mypy is configured in `pyproject.toml` but currently reports about 46 errors. Most are SQLModel typing false positives: `id: int | None` passed where `int` is expected, and plain `bool` where SQLAlchemy expects a column expression. The step runs with `continue-on-error: true`, so its output appears in the log but does not fail the job. Once those errors are fixed (with `assert obj.id is not None`, or `sqlmodel.col(...)` around columns), delete the `continue-on-error` line so type errors block merges.

## Run the same checks locally

Start the dev database first: `docker compose up -d db`. It listens on port 5434 and creates `propcheck_test` the first time its volume is initialised.

```bash
# Frontend
cd frontend
npm ci
npm run lint
npm run typecheck
npm test
npm run build

# Backend
cd backend
uv sync --frozen
uv run ruff format --check .
uv run ruff check .
uv run mypy app                  # informational, see above
uv run alembic upgrade head      # your local dev database (DATABASE_URL)
uv run alembic check
uv run pytest                    # uses TEST_DATABASE_URL (propcheck_test); its schema is wiped each run
```

`uv run pytest` drops and recreates the schema of whatever `TEST_DATABASE_URL` points to. Never point it at a database you care about.

To fix formatting or lint problems automatically, run `uv run ruff format .` and `uv run ruff check --fix .`, or `npx eslint --fix` in `frontend/`.

## Viewing a failed run

1. Open the repository on GitHub and go to the **Actions** tab (or click the red ✗ next to a commit or on the PR's **Checks** tab).
2. Pick the **CI** run, then the failing job (`frontend` or `backend`).
3. Expand the step with the red ✗ to read its log. Use the search box at the top right of the log to find `error` or `FAILED`.
4. To rerun a flaky job, use **Re-run jobs → Re-run failed jobs**. Turning on **debug logging** adds runner diagnostics.

With the GitHub CLI: `gh run list --workflow CI`, `gh run view <id> --log-failed`, `gh run rerun <id> --failed`.

## Adding or changing CI environment variables safely

- **Non-secret, test-only values** (feature flags, dummy URLs, the CI database credentials) go straight into the job's `env:` block in `ci.yml`. Use obviously fake values such as `ci-only-...`.
- **Real secrets** should rarely be needed in CI, because tests use the simulated payment provider and local storage. If one is ever needed, add it under **Settings → Secrets and variables → Actions → New repository secret**. Reference it only in the step that needs it (`env: FOO: ${{ secrets.FOO }}`), never in `run:` text, and never `echo` it. GitHub masks secrets in logs, but derived values (base64, substrings) are not masked.
- Pull requests from forks do not receive secrets. Do not work around this with `pull_request_target`, which would run untrusted PR code with secrets.
- Never put production credentials (database URLs, Paystack live keys, Cloudinary keys, JWT secrets) in CI. The app refuses non-test Paystack keys at startup anyway.
- Never commit `.env` files. They are git-ignored. Only `.env.example`, with placeholder values, belongs in the repository.
- Do not add `actions/upload-artifact` steps for storage directories, uploads or database dumps. They can contain identity documents and other private files.

## Deployment

There is none in CI. Deployment is manual; see [DEPLOYMENT.md](DEPLOYMENT.md). Any future deploy workflow should be a separate file, use protected GitHub environments with required reviewers, and never run on `pull_request`.
