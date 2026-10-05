# eleicoes-data

Automatic snapshots of the official TSE (Tribunal Superior Eleitoral) results for the
**2026 Brazilian presidential election, 1st round** —
[election 6257 / cargo 1 (Presidente) / Brasil](https://resultados.tse.jus.br/oficial/app/index.html#/eleicao/6257/uf/br/cargo/1/vis/nominal/resultados).

## How it works

- `.github/workflows/scrape-tse.yml` runs **every minute** (`cron: "* * * * *"`, plus manual
  `workflow_dispatch`) and executes the scraper, committing each new snapshot back to the repo.
  > Note: GitHub Actions' effective minimum scheduled interval is ~5 minutes depending on
  > infrastructure load; the cron above requests the maximum allowed frequency. Scheduled
  > workflows only run from the repository's **default branch**.
- `scripts/scrape_tse.py` downloads the public JSON behind the results page
  (`https://resultados.tse.jus.br/oficial/ele2026/6257/dados/br/br-c0001-e006257-u.json`,
  EA20 "resultado unificado" layout), wraps it with scrape metadata, and writes it to
  `data/presidente_br_YYYYmmdd_HHMMSSZ.json` — a **unique timestamped filename per run**, so
  snapshots never overwrite each other.
- Pure Python standard library: no dependencies to install.

## Output format

Each file in `data/` is a JSON object:

```jsonc
{
  "metadata": {
    "source": "Tribunal Superior Eleitoral (TSE) - Resultados Oficial",
    "page_url": "...index.html#/eleicao/6257/uf/br/cargo/1/vis/nominal/resultados",
    "data_url": ".../br-c0001-e006257-u.json",
    "election_id": "6257",
    "cargo": "Presidente",
    "tse_file_generated_at": "04/10/2026 20:51:35",
    "tse_last_updated_at": "04/10/2026 20:51:28",
    "scraped_at_utc": "2026-10-04T23:51:36Z",
    "scraped_at_brasilia": "2026-10-04T20:51:36-03:00",
    "source_bytes": 24691
  },
  "data": { /* full, unmodified TSE payload: candidates, parties,
               sections, electorate, valid/blank/null votes, ... */ }
}
```

## Running locally

```bash
python scripts/scrape_tse.py                     # writes to ./data
python scripts/scrape_tse.py --output-dir out    # custom output directory
```

Configurable via env vars: `TSE_DATA_URL`, `TSE_PAGE_URL`, `OUTPUT_DIR`,
`SCRAPE_TIMEOUT`, `SCRAPE_RETRIES`, `SCRAPE_BACKOFF`.

## Tests

Offline end-to-end tests (local mock server + a real captured TSE payload):

```bash
python tests/test_scrape_tse.py
```

## Disclaimer

This project only reads the public files published by the TSE. It has no affiliation with
the Tribunal Superior Eleitoral; the official results are at <https://resultados.tse.jus.br>.
