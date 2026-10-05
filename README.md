# Feroz Job Agent

A personal AI-assisted job application agent built incrementally with Python.

## Current status: Phase 2 complete

```text
Discovery → Normalization → Deduplication → Rule-based filtering
```

Phase 1 uses `python-jobspy==1.2.0` to discover **.NET Developer** jobs in
**Chennai** from **Naukri**, requesting **10 results** from the last **168 hours**.
It saves results to `data/jobs.csv`.

Phase 2 reads that CSV offline and saves accepted jobs to `data/filtered_jobs.csv`.
AI matching is **not implemented yet**. There is no automated submission, browser
automation, email integration, database, or dashboard.

## Setup and usage

Use Python 3.12 (developed with 3.12.3). From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m src.job_discovery.cli
python -m src.job_processing.cli
```

Discovery prints criteria, job count, and available details. Raised errors cause a
nonzero exit without creating fake jobs. JobSpy may itself log portal failures and
return an empty result: check its logs, since zero results does not prove no jobs
exist. Processing needs the input file; a missing file causes a logged error and a
nonzero exit. An empty CSV is handled as zero jobs.

Both commands overwrite their respective output CSV, including empty results.
All runtime CSV files remain ignored by Git.

## Processing rules

- Whitespace is trimmed/collapsed and missing text becomes an empty string.
  Human-readable capitalization is preserved; internal casefolded fields support
  matching without appearing in the final CSV. Other source columns are retained.
- Deduplication preserves the first occurrence using a valid HTTP(S) job URL.
  URL scheme/host are case-insensitive, fragments are removed, and path/query are
  preserved. Without a usable URL, normalized title/company/location form the
  fallback key. Incomplete fallback keys are kept rather than guessed duplicates.
  Different valid URLs remain separate postings.
- Title matching uses keyword boundaries. Targets include .NET, Dot Net, dotnet,
  C#, ASP.NET, backend, software engineer/developer, full stack and Web API roles.
  Unrelated title keywords (Java, PHP, Android, iOS, SAP, mainframe, sales,
  marketing, recruiter, data entry) reject a role. Descriptions do not trigger
  those exclusions. Generic software roles may therefore remain for Phase 3.
- Preferred locations are Chennai and Remote. Multi-city listings containing
  Chennai are eligible; an explicit `is_remote` flag also qualifies for Remote.
  Missing locations are retained as uncertain. Other stated locations are rejected.
- The candidate experience target is 4 years. Structured `experience_range` takes
  precedence. Ranges such as `3-5 years`, `3 to 6 years`, and `3-6 Yrs` are inclusive;
  `4+ years`, `minimum 3 years`, and single numbers such as `5 years experience`
  are treated as minimum requirements. Description parsing only considers one
  explicit overall label such as `Experience required: 3-5 years`. Ambiguous,
  reversed, conflicting, or unparseable requirements are kept. Arbitrary skill
  tenure mentions are not used to reject jobs.

Configure target keywords, excluded title keywords, preferred locations and
candidate experience through `FilterConfig` in `src/job_processing/models.py`.

`process_jobs` returns accepted jobs, all rows with `processing_reason`, and counts.
Each row has one reason: duplicate, unrelated title, location, experience, or
accepted, in that priority order. This makes counts add up to the raw total.
The CLI prints statistics and a preview; only accepted jobs go into the final CSV.

## Structure and tests

`src/job_discovery/` isolates search configuration, JobSpy and discovery output.
`src/job_processing/` separates configuration/results, normalization,
deduplication, filtering/experience parsing, pipeline and CSV CLI.

```bash
python -m unittest discover -s tests -v
```

Tests use built-in unittest, mock JobSpy, and never contact job websites.

## Roadmap

Next: **Phase 3: candidate profile + resume/JD AI match scoring** after deterministic
filtering. Later milestones include application tracking, resume tailoring and
application assistance. These features are not implemented.
