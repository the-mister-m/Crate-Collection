"""Minimal regression test for planner.py's grouping key.

Closes one specific gap: two nodes that share (file, model) but differ
on shifts must now land in separate jobs, not be silently collapsed
into one job that uses only the first node's settings. See HOW THE RUN
WORKS in docs/00-locked-spec.md and the grouping-key note at the top
of planner.py.

Stdlib only (unittest) — no new test-runner dependency added.
Run with: python -m unittest app.engine.test_planner -v
"""

from __future__ import annotations

import unittest

from .planner import plan


class SharedModelDifferingShiftsTest(unittest.TestCase):
    def test_two_nodes_same_file_same_model_different_shifts_get_separate_jobs(self) -> None:
        run_config = {
            "device": "cpu",
            "jobs": 1,
            "files": ["/tmp/song.wav"],
            "nodes": [
                {
                    "id": "node-a",
                    "model": "htdemucs",
                    "stems": {"drums": True, "bass": False, "vocals": False, "other": False},
                    "shifts": 0,
                    "overlap": 0.25,
                    "segment": None,
                },
                {
                    "id": "node-b",
                    "model": "htdemucs",
                    "stems": {"drums": False, "bass": True, "vocals": False, "other": False},
                    "shifts": 2,
                    "overlap": 0.25,
                    "segment": None,
                },
            ],
        }

        jobs = plan(run_config)

        self.assertEqual(len(jobs), 2, "differing shifts on a shared file+model must split into 2 jobs")

        node_ids_per_job = [job.node_ids for job in jobs]
        self.assertIn(["node-a"], node_ids_per_job)
        self.assertIn(["node-b"], node_ids_per_job)


if __name__ == "__main__":
    unittest.main()
