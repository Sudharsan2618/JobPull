# JobPull — simple 3-source job pull

Standalone, no company/industry/experience/location logic. Scrape → title filter → store → view.

## Scope (hard-coded in `config.py`)
- **Titles:** Gen AI Engineer, AI Engineer, Python Developer, Artificial Intelligence
- **Locations:** Chennai, Bangalore
- **Time:** last 24 hours
- **Sources:** LinkedIn + Indeed (JobSpy), Naukri (Firecrawl)
- **Database:** `job-pull-simple` (same MongoDB cluster as BE, separate DB), collection `jobs`

## Interpreter
Uses the Python 3.13 that already has the deps installed:
```
C:\Users\WELCOME\AppData\Local\Programs\Python\Python313\python.exe
```

## Pipeline (5 stages, `run.py`)
```
1. DISCOVER  parallel per-source thread pools   listings only, no descriptions
2. DEDUPE    in-memory, by platform job id      collapses semantic-search overlap
3. FILTER    titles only                        drop non-matches before spending
4. ENRICH    parallel                           full descriptions for UNIQUE +
                                                 ACCEPTED jobs only
5. STORE     streaming upsert                    idempotent, writes as it goes
```

- **Concurrency** (`pool.py` + `config.WORKERS`): bounded `ThreadPoolExecutor` per source — I/O-bound blocking libs, so threads beat asyncio. Defaults `linkedin:2, indeed:3, naukri:2`. **Naukri is hard-capped at 2** = Firecrawl free-plan concurrent-browser limit; Naukri discovery and enrichment run in separate stages so never more than 2 browsers at once.
- **Dedupe by job id** (`store.py`): key priority = `source+external_id` (LinkedIn `li-<id>`, Indeed `in-<jk>`, Naukri `nk-<id>` from URL) → `source+job_url` → fingerprint. The same posting under different search terms collapses to one, within a run and across runs (upsert).
- **JobSpy** (`sources/jobspy_source.py`): `discover()` = listings only (`linkedin_fetch_description=False`, `country_indeed="India"`); `enrich_linkedin()` = full JD per unique job via LinkedIn's public guest endpoint. Indeed descriptions come with the listing.
- **Naukri** (`sources/naukri_source.py`): `discover()` = Firecrawl JSON on `...jobAge=1`, paginated via `interact()` (URL-suffix fallback); `enrich()` = one Firecrawl scrape per unique job.
- **Title filter** (`title_filter.py`): accept-list built from the 4 titles + synonyms; small reject-list guards false positives. Only filter in the module.

## Run
```
cd JobPull
# all three sources
C:\...\Python313\python.exe run.py
# one or more sources
C:\...\Python313\python.exe run.py linkedin indeed
C:\...\Python313\python.exe run.py naukri
```

## View stored jobs + descriptions
```
C:\...\Python313\python.exe view.py                 # accepted, one line each
C:\...\Python313\python.exe view.py --all            # include rejected
C:\...\Python313\python.exe view.py --source naukri  # by source
C:\...\Python313\python.exe view.py --full           # full descriptions
C:\...\Python313\python.exe view.py --title python   # title substring
```

## Test
```
# no network / no cost
C:\...\Python313\python.exe tests/test_title_filter.py
C:\...\Python313\python.exe tests/test_dedupe.py
# small live smoke of the full pipeline (2 overlapping titles, capped enrichment)
C:\...\Python313\python.exe tests/smoke_live.py
```

## Tuning
All in `config.py`: `WORKERS` (per-source concurrency), `ENRICH_DESCRIPTIONS`,
`MAX_ENRICH_PER_SOURCE` (None = enrich all unique accepted), `NAUKRI_MAX_PAGES`,
`RESULTS_PER_SEARCH`.
