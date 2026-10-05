#!/usr/bin/env python3
"""Scrape official TSE (Tribunal Superior Eleitoral) election results.

Target page (Angular SPA):
    https://resultados.tse.jus.br/oficial/app/index.html#/eleicao/6257/uf/br/cargo/1/vis/nominal/resultados
    -> Eleição Ordinária Federal 2026, 1º turno, cargo 1 (Presidente), UF = br (Brasil)

The page is rendered client-side; the underlying public JSON file it loads is:
    https://resultados.tse.jus.br/oficial/ele2026/6257/dados/br/br-c0001-e006257-u.json
    (layout EA20, "resultado unificado", election 6257 per /oficial/comum/config/ele-c.json)

Each run downloads the full payload and writes a timestamped snapshot to the
output directory (default ./data) so consecutive runs never overwrite files:

    data/presidente_br_YYYYmmdd_HHMMSSZ.json   (UTC timestamp in the name)

All configuration can be overridden with CLI flags or environment variables,
which is also how the offline test suite injects a local mock server.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

try:
    from zoneinfo import ZoneInfo
except ImportError:  # Python < 3.9
    ZoneInfo = None

DEFAULT_DATA_URL = (
    "https://resultados.tse.jus.br/oficial/ele2026/6257/"
    "dados/br/br-c0001-e006257-u.json"
)
DEFAULT_PAGE_URL = (
    "https://resultados.tse.jus.br/oficial/app/index.html"
    "#/eleicao/6257/uf/br/cargo/1/vis/nominal/resultados"
)
DEFAULT_OUTPUT_DIR = "data"
EXPECTED_ELECTION_ID = "6257"
USER_AGENT = (
    "Mozilla/5.0 (compatible; eleicoes-data-scraper/1.0; "
    "+https://github.com/havaianasdestruido/eleicoes-data)"
)


def fetch_payload(url: str, timeout: float, retries: int, backoff: float) -> tuple[dict, int]:
    """Download `url` and return (parsed JSON, raw byte count).

    Retries with linear backoff on network errors, non-200 statuses, or
    malformed JSON. Raises SystemExit after all attempts are exhausted.
    """
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        request = urllib.request.Request(
            url,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json, */*;q=0.8"},
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                status = getattr(response, "status", 200)
                if status != 200:
                    raise RuntimeError(f"unexpected HTTP status {status}")
                raw = response.read()
            return json.loads(raw.decode("utf-8-sig")), len(raw)
        except (
            urllib.error.URLError,
            TimeoutError,
            OSError,
            json.JSONDecodeError,
            RuntimeError,
        ) as exc:
            last_error = exc
            print(f"[fetch] attempt {attempt}/{retries} failed: {exc}", file=sys.stderr)
            if attempt < retries:
                time.sleep(backoff * attempt)
    raise SystemExit(f"ERROR: could not fetch {url} after {retries} attempts: {last_error}")


def validate_payload(payload: dict) -> None:
    """Sanity-check that the payload looks like the expected TSE results file."""
    if not isinstance(payload, dict):
        raise SystemExit("ERROR: payload is not a JSON object")
    election = str(payload.get("ele", ""))
    if election != EXPECTED_ELECTION_ID:
        raise SystemExit(
            f"ERROR: unexpected election id {election!r} (expected {EXPECTED_ELECTION_ID!r})"
        )
    missing = [key for key in ("carg", "s", "e", "v") if key not in payload]
    if missing:
        raise SystemExit(f"ERROR: payload is missing expected keys: {missing}")


def unique_path(directory: Path, stem: str, suffix: str) -> Path:
    """Return a path inside `directory` that does not exist yet (never overwrites)."""
    candidate = directory / f"{stem}{suffix}"
    counter = 1
    while candidate.exists():
        candidate = directory / f"{stem}-{counter}{suffix}"
        counter += 1
    return candidate


def candidate_rows(payload: dict) -> list[dict]:
    """Flatten agr -> par -> cand into (votes, name, party) tuples for logging."""
    rows = []
    for cargo in payload.get("carg", []):
        for agregacao in cargo.get("agr", []):
            for partido in agregacao.get("par", []):
                for cand in partido.get("cand", []):
                    rows.append(
                        {
                            "seq": cand.get("seq"),
                            "nmu": cand.get("nmu"),
                            "sg": partido.get("sg"),
                            "vap": int(cand.get("vap", 0) or 0),
                            "pvap": cand.get("pvap"),
                        }
                    )
    rows.sort(key=lambda r: r["vap"], reverse=True)
    return rows


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--url", default=os.environ.get("TSE_DATA_URL", DEFAULT_DATA_URL),
                        help="URL of the TSE results JSON (env: TSE_DATA_URL)")
    parser.add_argument("--page-url", default=os.environ.get("TSE_PAGE_URL", DEFAULT_PAGE_URL),
                        help="Human-facing results page URL, stored in metadata (env: TSE_PAGE_URL)")
    parser.add_argument("--output-dir", default=os.environ.get("OUTPUT_DIR", DEFAULT_OUTPUT_DIR),
                        help="Directory for timestamped JSON snapshots (env: OUTPUT_DIR)")
    parser.add_argument("--timeout", type=float, default=float(os.environ.get("SCRAPE_TIMEOUT", "30")),
                        help="HTTP timeout in seconds (env: SCRAPE_TIMEOUT)")
    parser.add_argument("--retries", type=int, default=int(os.environ.get("SCRAPE_RETRIES", "4")),
                        help="Number of fetch attempts (env: SCRAPE_RETRIES)")
    parser.add_argument("--backoff", type=float, default=float(os.environ.get("SCRAPE_BACKOFF", "2")),
                        help="Base backoff in seconds between attempts (env: SCRAPE_BACKOFF)")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    scraped_at_utc = datetime.now(timezone.utc)
    payload, raw_bytes = fetch_payload(args.url, args.timeout, args.retries, args.backoff)
    validate_payload(payload)

    if ZoneInfo is not None:
        scraped_at_brasilia = scraped_at_utc.astimezone(ZoneInfo("America/Sao_Paulo")).isoformat(
            timespec="seconds"
        )
    else:  # pragma: no cover
        scraped_at_brasilia = None

    stamp = scraped_at_utc.strftime("%Y%m%d_%H%M%SZ")
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = unique_path(output_dir, f"presidente_br_{stamp}", ".json")

    document = {
        "metadata": {
            "source": "Tribunal Superior Eleitoral (TSE) - Resultados Oficial",
            "page_url": args.page_url,
            "data_url": args.url,
            "election_id": payload.get("ele"),
            "election_turn": payload.get("t"),
            "cargo": (payload.get("carg") or [{}])[0].get("nmn"),
            "abrangencia": payload.get("cdabr"),
            "tse_file_generated_at": f"{payload.get('dg')} {payload.get('hg')}",
            "tse_last_updated_at": f"{payload.get('dt')} {payload.get('ht')}",
            "scraped_at_utc": scraped_at_utc.isoformat(timespec="seconds").replace("+00:00", "Z"),
            "scraped_at_brasilia": scraped_at_brasilia,
            "source_bytes": raw_bytes,
        },
        "data": payload,
    }

    with output_path.open("w", encoding="utf-8") as fh:
        json.dump(document, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    secoes = payload.get("s", {})
    votos = payload.get("v", {})
    ranking = candidate_rows(payload)
    leader = ranking[0] if ranking else {}
    print(f"OK: snapshot written to {output_path}")
    print(f"    TSE generated: {document['metadata']['tse_file_generated_at']}"
          f" | secoes totalizadas: {secoes.get('st')}/{secoes.get('ts')} ({secoes.get('pst')}%)")
    print(f"    votos validos: {votos.get('vv')} | brancos: {votos.get('vb')} | nulos: {votos.get('tvn')}")
    print(f"    líder: {leader.get('nmu')} ({leader.get('sg')}) - {leader.get('vap')} votos ({leader.get('pvap')}%)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
