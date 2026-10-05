# Job Agent

AI-assisted job discovery and matching for a personal job search.

## Status: Phase 3 implemented

```text
Job Boards → Job Discovery → Normalization → Deduplication → Rule Filtering
    → Candidate Profile + Resume → Gemini AI Matching → Streamlit Dashboard
```

Implemented: JobSpy discovery, normalization, deduplication, configurable
rule-based filtering, personal YAML profiles, PDF/TXT resume extraction,
validated AI scoring and a Streamlit UI. The existing CLI commands still work.

Not implemented: automatic applications, resume rewriting/tailoring generation,
cover letters, Gmail monitoring, interview scheduling, authentication, multi-user
support, databases or deployment. AI suggestions do not edit your resume.

## Setup

Use Python 3.12, from the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp config/profile.example.yaml profile.yaml
cp .env.example .env
```

Replace every example value with your actual experience and skills. Alternatively,
create your profile in the Profile page. Name, current role and nonnegative years
of experience are required. Lists include preferred locations, target roles,
primary/secondary skills, frameworks, databases, cloud tools, AI skills and
projects. Work history summary, education, notice period, compensation and
relocation preference are supported. Personal profiles are never written to the
committed example.

Set `GEMINI_API_KEY` and `GEMINI_MODEL` in `.env`. Use a model ID available to your
Google AI account that supports structured output. No model is silently chosen.
The adapter uses the official [Google Gen AI SDK](https://googleapis.github.io/python-genai/)
and [structured JSON output](https://ai.google.dev/gemini-api/docs/structured-output).
Environment variables take precedence over `.env`; restart Streamlit after edits.

Place a real PDF/TXT resume under `resume/`, or upload it on Settings. Uploads use
random filenames and a 10 MB limit. PDFs use pypdf text extraction; encrypted,
scanned/image-only, invalid and empty files fail clearly. OCR is not included.

```bash
streamlit run app/Home.py
```

Use locally for a single user; do not expose this unauthenticated personal app to
an untrusted network. No cloud deployment is configured.

## Web workflow

1. **Home**: raw/filtered counts, recommendation metrics and recent top matches.
2. **Discover Jobs**: configurable term, location, portals, count and age; defaults
   are .NET Developer / Chennai / Naukri / 10 results / 7 days. Discover uses the
   existing service; Process / Filter uses the existing processing pipeline.
3. **Filtered Jobs**: accepted jobs, company/location/keyword search and AI navigation.
4. **AI Matches**: setup checks, resume selection, 1–10 selected jobs (default 3),
   visible progress and ranked cards with subscores, strengths, gaps, risks and
   suggestions. Scoring happens only when Run AI Matching is pressed.
5. **Profile**: edit and save personal `profile.yaml`.
6. **Resume / Settings**: API key status (never the key), model hint, resume upload,
   selection and optional extracted-text preview.

Scoring transmits your profile, selected resume text and job details to Gemini and
consumes API quota. No AI calls occur during discovery/filtering or ordinary page
loads. Before scoring, review your profile and extraction preview for accuracy.
Missing descriptions produce a limited assessment with low confidence and an
insufficient-evidence note. Scores are model assessments, not verified hiring outcomes.

## Rules, scoring and persistence

Phase 2 cleans missing text and whitespace, preserves display capitalization and
uses casefolded matching keys. Duplicates preserve the first valid HTTP(S) URL;
without one, a complete title/company/location composite is used. Different URLs
remain distinct and incomplete fallback identities are kept.

Title rules include .NET/Dot Net/dotnet, C#, ASP.NET, backend, software
engineer/developer, full stack and Web API. Unrelated title keywords are excluded;
description mentions of optional technologies are not title exclusions. Chennai,
Remote and explicit remote flags qualify by default; missing locations remain
uncertain. Experience uses structured `experience_range` before explicitly
labelled overall description requirements. Ranges are inclusive; single-number
requirements are treated as minima. Uncertain/contradictory formats stay eligible.
`FilterConfig` controls keywords, locations and experience. The web processing
button uses saved profile experience and preferred locations when a profile exists;
otherwise Phase 2 defaults (4 years, Chennai/Remote) apply. Target roles/skills are
AI evidence; they do not replace the Phase 2 keyword configuration.

The model returns five integer scores (0–100), matched skills, missing required
skills, optional gaps, strengths, risks, reasoning, suggestions and high/medium/low
confidence. All fields/types/bounds are validated in Python; no `eval` is used.
Python derives recommendations from overall score:

| Score | Recommendation |
|---|---|
| 85–100 | strong_apply |
| 70–84 | apply |
| 55–69 | review |
| 0–54 | skip |

The provider is injected into `JobMatchService`. Only Gemini is implemented.
Transient network/HTTP 408, 429 and selected 5xx failures and malformed responses
have at most 3 attempts, with 0.5/1 second backoff. SDK retries are disabled to avoid
multiplying calls. Missing setup and permanent provider errors are not retried.
Individual scoring failures are reported and other selected jobs continue. Failed
jobs receive no fabricated score. UI errors avoid raw tracebacks; logs record
failure classes without prompts, resume contents, API keys or raw provider errors.

Filesystem persistence:

- `data/jobs.csv`: raw discovery
- `data/filtered_jobs.csv`: accepted jobs
- `data/scored_jobs.csv`: successfully scored selected jobs, descending score;
  list fields are JSON strings and original columns are retained
- `profile.yaml` and `resume/`: personal inputs

Each run overwrites its output, including empty results. Scored output represents
only the latest selected batch, not an accumulated history. New web discovery
invalidates old filtered/scored output; web processing/profile saves/resume uploads
invalidate old scores. Changing a profile requires reprocessing if locations or
experience changed. CLI/manual edits do not perform web output invalidation.
All these runtime files and `.env` remain Git ignored. Only placeholder examples
are committed. Zero discovery results may indicate a JobSpy portal failure; check
logs. Missing/empty files and missing AI setup show actionable UI guidance.

## Architecture and developer commands

`app/` contains presentation only. `src/job_discovery/` isolates JobSpy,
`src/job_processing/` owns deterministic processing, `src/job_matching/` owns
profile/resume loading, prompt/schema validation, provider adapter, matching and
ranking. `src/workflow.py` handles CSV workflow/metrics for presentation reuse.

```bash
python -m src.job_discovery.cli
python -m src.job_processing.cli
python -m unittest discover -s tests -v
```

Unit tests use unittest, fake providers and mocks; they never contact job boards
or Gemini and use only synthetic temporary profiles/resumes.

Next milestone only: **Phase 4 — application tracking, shortlist management, and
review workflow**.
