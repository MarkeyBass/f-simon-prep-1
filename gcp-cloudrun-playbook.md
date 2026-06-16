# GCP Cloud Run — Assignment Playbook

Keep this open during the real thing. The assignment isn't testing whether you can
code — Adar knows you can. It's testing whether you can ship a clean service to GCP
under time pressure **without the deploy eating your hour.** So make deploy boring.

---

## The one rule: deploy a stub FIRST

In the first ~20 minutes, get an empty `/health` service live on Cloud Run before
you write any features. Once the URL responds, deployment risk is dead and you build
calm. Never leave the first deploy for the end.

---
## Set-up session env vars for the project info and for adding IAM Policies to Project** — roles/cloudbuild.builds.builder:

```bash
PROJECT_ID=fast-simon-proj-1
PROJECT_NUM=277249488513
SA=${PROJECT_NUM}-compute@developer.gserviceaccount.com
```

## One-time setup (do this NOW, in practice — not during the test)

```bash
gcloud auth login
gcloud config set project $PROJECT_ID

gcloud auth application-default set-quota-project $PROJECT_ID

gcloud config set project $PROJECT_ID

gcloud services enable run.googleapis.com cloudbuild.googleapis.com
```

**Add IAM Policies to Project** — roles/cloudbuild.builds.builder:
```bash
PROJECT_ID=<PROJECT_ID>
PROJECT_NUM=<PROJECT_NUM>
SA=${PROJECT_NUM}-compute@developer.gserviceaccount.com
```

# the one role that bundles what source-deploy builds need
```bash
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA}" \
  --role="roles/cloudbuild.builds.builder"
```

Pick a region near you — `europe-west1` (your old App Engine apps were europe-west).

## Deploy (one command, with a Dockerfile present)

```bash
gcloud run deploy fastsimon-practice \
  --source . \
  --region europe-west1 \
  --allow-unauthenticated
```

## The url returned:
```bash
https://fastsimon-practice-277249488513.europe-west1.run.app
```

`--source .` hands the folder to Cloud Build. With a Dockerfile present it builds that
(predictable for FastAPI). Without one, it uses buildpacks — for FastAPI those need a
`Procfile` (`web: uvicorn main:app --host 0.0.0.0 --port $PORT`), so the Dockerfile path
is the safer bet. You get a live `https://...run.app` URL back. Smoke-test it:

```bash
curl https://YOUR-URL.run.app/health
```

## Run + test locally

```bash
pip install -r requirements.txt
uvicorn main:app --reload --port 8080
pytest
```

---

## 90-minute battle plan

| Time | Do |
|------|----|
| 0–10 min | Read the spec. Sketch endpoints + data model on paper. `git init`, commit a skeleton. |
| 10–25 min | Deploy the `/health` stub to Cloud Run. Confirm the live URL. **Risk killed.** |
| 25–70 min | Build features with Claude Code. **Review every diff. Commit incrementally.** |
| 70–80 min | Tests, error handling (404/400), tidy. |
| 80–90 min | Final deploy. Smoke-test the live URL. Write the README design-notes section. |

Commit small and often — a clean git history is itself a signal. Not one "final" blob.

---

## "The code needs to be good" — the checklist they'll judge on

- **Structure** — clear separation; for anything bigger than one file, split routes / models / logic.
- **Types + validation** — type hints everywhere, Pydantic models for every request body.
- **Error handling** — explicit `HTTPException` with right status codes; no bare crashes.
- **A health check** — `/health`. Also your first-deploy stub.
- **Tests** — even 4–5 with `TestClient` puts you ahead of most candidates.
- **README** — what it does, how to run, how to deploy, and a short **design-notes / tradeoffs** section.
- **Hygiene** — `.gitignore` (no venv, no creds), **no secrets in code** (env vars / Secret Manager), meaningful commits.

## The thing that closes Adar's stated gap

He said your one gap is scale and high-volume data flows. So **say it in the README**, in
two lines, without being asked:

> "This service is stateless, so it scales horizontally on Cloud Run. For real catalog
> volume I'd back it with Firestore (or Cloud SQL) plus a cache, page all list endpoints,
> and watch p95 latency and cost together — the lazy fix is more instances, but that just
> moves a latency problem onto the cost line."

That single paragraph tells him you think about exactly the thing he flagged. It turns the
gap into a non-issue.

---

## Practice reps before the assignment (each ends in a LIVE url)

1. **Warm-up** — hello FastAPI → Cloud Run. Goal: nail `gcloud run deploy`. ~20 min.
2. **Gap-killer** — the included `main.py`: ingest a product batch, query with filters +
   pagination. Swap the in-memory store for **Firestore** to prove persistence + scale.
3. **Domain flex** — the `/similar` + `/search` endpoints. Mention out loud that real
   similarity = vector search over embeddings — the engine you already built in Confy.

Do rep 1 at least twice until the deploy is muscle memory. That's the whole game.
