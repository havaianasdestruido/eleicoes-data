#!/usr/bin/env python3
"""Tests for the interactive Jupyter Notebooks in test/.

Executes the notebooks in-place (when nbclient/nbformat are installed) and
verifies that all code cells succeed and that rendered graph images
(`image/png`) remain embedded inside each `.ipynb` file on disk after the
test run (never cleaned or stripped).

Run:  python tests/test_notebooks.py
"""

from __future__ import annotations

import base64
import json
import unittest
from pathlib import Path

try:
    import nbformat
    from nbclient import NotebookClient
except ImportError:  # pragma: no cover
    nbformat = None
    NotebookClient = None

REPO_ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_DIR = REPO_ROOT / "test"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"

EXPECTED_NOTEBOOKS = [
    "01_candidate_results_overview.ipynb",
    "02_turnout_sections_and_vote_types.ipynb",
    "03_counting_progression_and_late_votes.ipynb",
    "04_parties_coalitions_and_second_round_scenarios.ipynb",
    "05_scraper_timeline_and_telemetry.ipynb",
]


class NotebookTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Execute all notebooks in test/ in-place and persist embedded outputs."""
        cls.notebook_paths = sorted(NOTEBOOK_DIR.glob("*.ipynb"))
        if nbformat is not None and NotebookClient is not None:
            for nb_path in cls.notebook_paths:
                nb = nbformat.read(nb_path, as_version=4)
                client = NotebookClient(
                    nb,
                    timeout=180,
                    kernel_name="python3",
                    resources={"metadata": {"path": str(NOTEBOOK_DIR)}},
                )
                client.execute()
                # Persist executed outputs directly into the .ipynb file;
                # intentionally do NOT clean or strip outputs after test run.
                with nb_path.open("w", encoding="utf-8") as fh:
                    nbformat.write(nb, fh)

    def test_expected_notebooks_exist(self):
        existing = [p.name for p in self.notebook_paths]
        self.assertGreaterEqual(len(existing), 5, "expected multiple notebooks in test/")
        for expected in EXPECTED_NOTEBOOKS:
            self.assertIn(expected, existing, f"missing notebook {expected} in test/")

    def test_notebooks_have_executed_cells_and_no_errors(self):
        for nb_path in self.notebook_paths:
            with self.subTest(notebook=nb_path.name):
                raw = json.loads(nb_path.read_text(encoding="utf-8"))
                code_cells = [c for c in raw.get("cells", []) if c.get("cell_type") == "code"]
                self.assertGreaterEqual(len(code_cells), 4, f"{nb_path.name} should have multiple code cells")

                for idx, cell in enumerate(code_cells):
                    self.assertIsNotNone(
                        cell.get("execution_count"),
                        f"{nb_path.name} code cell #{idx} was not executed",
                    )
                    for out in cell.get("outputs", []):
                        self.assertNotEqual(
                            out.get("output_type"),
                            "error",
                            f"{nb_path.name} cell #{idx} produced an error: {out.get('evalue')}",
                        )

    def test_notebooks_persist_embedded_png_graphs(self):
        for nb_path in self.notebook_paths:
            with self.subTest(notebook=nb_path.name):
                raw = json.loads(nb_path.read_text(encoding="utf-8"))
                png_outputs = []
                for cell in raw.get("cells", []):
                    if cell.get("cell_type") != "code":
                        continue
                    for out in cell.get("outputs", []):
                        img_b64 = out.get("data", {}).get("image/png")
                        if img_b64:
                            if isinstance(img_b64, list):
                                img_b64 = "".join(img_b64)
                            png_bytes = base64.b64decode(img_b64)
                            self.assertTrue(
                                png_bytes.startswith(PNG_MAGIC),
                                f"invalid PNG header in {nb_path.name}",
                            )
                            self.assertGreater(
                                len(png_bytes),
                                10_000,
                                f"embedded PNG in {nb_path.name} is unexpectedly small",
                            )
                            png_outputs.append(len(png_bytes))

                self.assertGreaterEqual(
                    len(png_outputs),
                    3,
                    f"expected at least 3 embedded graph images in {nb_path.name}",
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
