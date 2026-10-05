#!/usr/bin/env python3
"""Offline tests for scripts/scrape_tse.py.

Spins up a local HTTP server serving the real TSE payload captured in
tests/fixtures/ and verifies end-to-end behavior without touching the network.

Run:  python tests/test_scrape_tse.py        (uses unittest, no dependencies)
"""

from __future__ import annotations

import functools
import json
import re
import sys
import tempfile
import threading
import unittest
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import scrape_tse  # noqa: E402

FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures"
FIXTURE_FILE = FIXTURE_DIR / "br-c0001-e006257-u.json"
FILENAME_RE = re.compile(r"^presidente_br_\d{8}_\d{6}Z\.json$")


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):  # keep test output clean
        pass


class ScraperTestCase(unittest.TestCase):
    server: ThreadingHTTPServer
    server_thread: threading.Thread
    base_url: str

    @classmethod
    def setUpClass(cls):
        handler = functools.partial(QuietHandler, directory=str(FIXTURE_DIR))
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def run_scraper(self, tmpdir: str, url: str | None = None) -> int:
        url = url if url is not None else f"{self.base_url}/br-c0001-e006257-u.json"
        return scrape_tse.main(["--url", url, "--output-dir", tmpdir,
                                "--retries", "2", "--backoff", "0.1", "--timeout", "5"])

    def test_happy_path_writes_full_snapshot(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self.assertEqual(self.run_scraper(tmpdir), 0)
            files = list(Path(tmpdir).iterdir())
            self.assertEqual(len(files), 1, "expected exactly one snapshot file")
            self.assertRegex(files[0].name, FILENAME_RE)

            document = json.loads(files[0].read_text(encoding="utf-8"))
            fixture = json.loads(FIXTURE_FILE.read_text(encoding="utf-8"))
            self.assertEqual(document["data"], fixture, "snapshot must contain all of the source data")

            meta = document["metadata"]
            self.assertEqual(meta["election_id"], "6257")
            self.assertEqual(meta["cargo"], "Presidente")
            self.assertTrue(meta["data_url"].startswith(self.base_url))
            self.assertEqual(meta["tse_file_generated_at"], "04/10/2026 20:51:35")
            for key in ("page_url", "scraped_at_utc", "scraped_at_brasilia", "source_bytes"):
                self.assertIn(key, meta)
                self.assertIsNotNone(meta[key])

    def test_runs_never_overwrite(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self.assertEqual(self.run_scraper(tmpdir), 0)
            self.assertEqual(self.run_scraper(tmpdir), 0)
            self.assertEqual(self.run_scraper(tmpdir), 0)
            names = sorted(p.name for p in Path(tmpdir).iterdir())
            self.assertEqual(len(names), 3, "each run must create a new file")
            self.assertEqual(len(set(names)), 3, "filenames must be unique")
            for name in names:
                self.assertRegex(name, r"^presidente_br_\d{8}_\d{6}Z(-\d+)?\.json$")

    def test_bad_url_fails_without_writing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with self.assertRaises(SystemExit):
                self.run_scraper(tmpdir, url=f"{self.base_url}/does-not-exist.json")
            self.assertEqual(list(Path(tmpdir).iterdir()), [], "no file should be written on failure")

    def test_invalid_json_fails_without_writing(self):
        (FIXTURE_DIR / "broken.json").write_text("{ not json", encoding="utf-8")
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                with self.assertRaises(SystemExit):
                    self.run_scraper(tmpdir, url=f"{self.base_url}/broken.json")
                self.assertEqual(list(Path(tmpdir).iterdir()), [])
        finally:
            (FIXTURE_DIR / "broken.json").unlink()

    def test_validate_rejects_wrong_election(self):
        with self.assertRaises(SystemExit):
            scrape_tse.validate_payload({"ele": "9999", "carg": [], "s": {}, "e": {}, "v": {}})

    def test_candidate_rows_sorted_by_votes(self):
        fixture = json.loads(FIXTURE_FILE.read_text(encoding="utf-8"))
        rows = scrape_tse.candidate_rows(fixture)
        self.assertEqual(len(rows), 12, "fixture has 12 presidential candidates")
        votes = [r["vap"] for r in rows]
        self.assertEqual(votes, sorted(votes, reverse=True))
        self.assertEqual(rows[0]["nmu"], "FLAVIO BOLSONARO")
        self.assertEqual(rows[0]["vap"], 53867670)


if __name__ == "__main__":
    unittest.main(verbosity=2)
