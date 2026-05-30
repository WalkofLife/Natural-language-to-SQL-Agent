# NL2SQL Databricks Deployment Tracker

## How we work
- You make every change. I explain what, why, and how — then you do it.
- Each phase starts with a git branch. Each task is a commit. PRs close phases.
- This mirrors how real teams work — so you can talk through it in interviews.

## Status Legend
- [ ] Not started
- [~] In progress
- [x] Done

---

## Git Setup (do this once before anything else)

- [ ] Initialize repo on GitHub (create a new repo, push existing code)
- [ ] Set up `.gitignore` — confirm `mlartifacts/`, `__pycache__/`, `.env`, `*.db`, `data/vector_store/` are excluded
- [ ] Decide on branching strategy: `main` = stable, feature branches per phase
- [ ] Write your first commit message with a proper format: `type(scope): message` (e.g. `fix(workflow): add missing return state in sql_check`)

**Branch naming convention for this project:**
```
cleanup/fix-sql-check
cleanup/fix-safety-prompt
deploy/phase-1-mlflow-databricks
deploy/phase-2-data-assets
... and so on
```

---

## Phase 0 — Code Cleanup
> Branch: `cleanup/code-fixes` — one commit per bug fix

**Bugs to fix (each = one commit):**

- [X] `sql_check()` does not return `state` — silent bug, graph loses all state changes from this node
- [X] `pre_safety_check` — `safety_prompt` uses `{translated_input}` as a plain string, not an f-string — the actual user input is never checked
- [X] `context_check` — verify `context_prompt` f-string interpolates correctly
- [X] `generate()` — confirm vector store key name matches what the prompt template expects
- [X] Parameterize `REMOTE_SERVER_URI` — move it to `.env` so it doesn't need to change in code per environment - deferred to Phase 1
- [X] Remove dead commented-out logging code in `workflow.py` (lines 15–21)

**Git practice for this phase:**
```
git checkout -b cleanup/code-fixes
# fix one bug
git add <file>
git commit -m "fix(workflow): add missing return state in sql_check"
# fix next bug
git commit -m "fix(workflow): correct f-string in safety_prompt"
# ... when all fixes done
git checkout main
git merge cleanup/code-fixes
git push origin main
```

---

## Phase 1 — Connect MLflow to Databricks
> Branch: `deploy/phase-1-mlflow`

- [ ] Create Databricks workspace (Community Edition)
- [ ] Generate personal access token in Databricks UI
- [ ] Add `DATABRICKS_HOST` and `DATABRICKS_TOKEN` to `.env`
- [ ] Update `REMOTE_SERVER_URI` in `definitions.py` to `"databricks"`
- [ ] Re-run `log_model.py` to register model in Unity Catalog
- [ ] Set `@champion` alias in Databricks UI under Models
- [ ] Verify `main.py` loads model correctly from Unity Catalog

---

## Phase 2 — Move Data Assets to Databricks
> Branch: `deploy/phase-2-data-assets`

- [ ] Create Unity Catalog Volume for the project
- [ ] Upload `index.faiss` and `index.pkl` to the Volume using Databricks CLI
- [ ] Update `vector_store.py` to load from Volume path first, fall back to local
- [ ] Migrate SQLite to Delta table (one-time notebook)
- [ ] Update `database.py` to query Delta table via `databricks-sql-connector`
- [ ] Store `OPENAI_API_KEY` in Databricks Secret Scope
- [ ] Update code to fetch key via `dbutils.secrets.get(scope="nl2sql", key="openai_api_key")`

---

## Phase 3 — Refactor Model Interface for Serving
> Branch: `deploy/phase-3-model-interface`

Current `predict()` returns a graph app object — not serializable as REST JSON.
Must change to: input = `{"question": "..."}`, output = `{"sql": "...", "results": [...]}`.

- [ ] Move DB + vector store loading into `load_context()` (runs once at startup)
- [ ] Rewrite `predict()` to accept a question, run the full graph, return structured result
- [ ] Re-run `log_model.py` to register new version
- [ ] Promote to `@champion` alias
- [ ] Test locally end-to-end with new interface

---

## Phase 4 — Databricks Model Serving Endpoint
> Branch: `deploy/phase-4-model-serving`

- [ ] Create serving endpoint in Databricks UI (point to `@champion`)
- [ ] Configure compute size and env vars (OpenAI key from Secret Scope)
- [ ] Test endpoint using built-in Databricks query UI
- [ ] Confirm endpoint URL and response shape

---

## Phase 5 — FastAPI on Databricks Apps
> Branch: `deploy/phase-5-databricks-apps`

- [ ] Update `nl2sql_service.py` to call the serving endpoint URL over HTTP
- [ ] Write `app.yaml` (Databricks Apps entry point + env vars config)
- [ ] Deploy: `databricks apps deploy nl2sql-app --source-code-path .`
- [ ] Test end-to-end: HTTP request → FastAPI → Model Serving → response

---

## Phase 6 — GitHub Actions CI/CD
> Branch: `cicd/github-actions`

This makes your project behave like a real engineering repo. Interviewers ask about this.

- [ ] Write `.github/workflows/lint.yml` — runs `flake8` on every push
- [ ] Write `.github/workflows/test.yml` — runs `pytest` on every push to `main`
- [ ] Write `.github/workflows/deploy.yml` — on merge to `main`, re-registers model in Databricks using Databricks CLI in CI
- [ ] Add branch protection rule on `main` — require CI to pass before merge
- [ ] Test the full flow: push a change → CI runs → deploy triggers

---

## Phase 7 — Monitoring and Evaluation
> Branch: `deploy/phase-7-monitoring`

- [ ] Create Databricks Workflow to run `evaluate.py` on a schedule (daily)
- [ ] Enable Lakehouse Monitoring on the Model Serving inference table
- [ ] Build a simple dashboard using endpoint system tables (latency, error rate, volume)
- [ ] Set alert: notify if `execution_success_rate` drops below 0.8
