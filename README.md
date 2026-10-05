# Feroz Job Agent

A personal AI-assisted job application agent built incrementally with Python.

## Current status: Phase 1 — Job Discovery

Phase 1 discovers jobs using `python-jobspy` and exports the returned results to
`data/jobs.csv`. The default search is **.NET Developer**, **Chennai**, **Naukri**,
up to **10 results** posted within the last **168 hours (7 days)**.

This phase only performs job discovery. AI matching, resume tailoring, application
tracking, automated submission, browser automation, email integrations, databases,
and a dashboard are not implemented.

## Setup and usage

Use Python 3.12 (developed with 3.12.3). From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m src.job_discovery.cli
```

The CLI prints the search criteria, job count, and available job details. It saves
returned results to `data/jobs.csv` without a DataFrame index. Each completed search
overwrites that file, including an empty result. CSV files are ignored by Git.
Raised search errors are logged and cause a nonzero exit without exporting fake
results. JobSpy may itself log portal/network failures and return an empty result;
check the logs when no jobs are returned. An empty result is not proof that no jobs
exist. External availability and portal restrictions can affect discovery.

## Structure and tests

`models.py` holds the search configuration, `service.py` isolates JobSpy and CSV
export, and `cli.py` handles command-line output. Change `JobSearchConfig` defaults
or pass a configuration to `discover_jobs` for another search.

Run offline unit tests with the virtual environment activated:

```bash
python -m unittest discover -s tests -v
```

Tests mock JobSpy and never contact real job websites.

## Future milestones

Next: **Phase 2: normalize, deduplicate, and filter discovered jobs**.
Later phases will add AI job matching, application tracking, resume tailoring,
and application assistance.
