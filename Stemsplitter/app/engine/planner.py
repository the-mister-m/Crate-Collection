"""WAVE A — planner.

Groups nodes by (file, model, shifts, overlap, segment) so demucs runs
exactly once per unique combination, per HOW THE RUN WORKS in
docs/00-locked-spec.md: shifts/overlap/segment are baked into the
separation pass itself, so nodes only share a pass when file, model,
and all three quality settings match. Every node sharing a pass is a
cheap sum over the same result — this is the entire performance story.

Nodes that share file+model but differ on any of shifts/overlap/
segment get their own separate job/pass — the engine automatically
does two separate runs in that case, rather than silently dropping
one node's settings.
"""

from __future__ import annotations

from .types import Job


def plan(run_config: dict) -> list[Job]:
    """Build the list of demucs jobs for a run config dict.

    Every node applies to every file in run_config["files"]. Jobs are
    keyed by (file, model, shifts, overlap, segment); a job's node_ids
    lists every node that consumes its output.
    """
    device = run_config["device"]
    jobs_n = run_config["jobs"]
    files = run_config["files"]
    nodes = run_config["nodes"]

    jobs_by_key: dict[tuple[str, str, int, float, int | None], Job] = {}
    order: list[tuple[str, str, int, float, int | None]] = []

    for file_path in files:
        for node in nodes:
            key = (file_path, node["model"], node["shifts"], node["overlap"], node["segment"])
            if key not in jobs_by_key:
                jobs_by_key[key] = Job(
                    file=file_path,
                    model=node["model"],
                    device=device,
                    jobs=jobs_n,
                    shifts=node["shifts"],
                    overlap=node["overlap"],
                    segment=node["segment"],
                    node_ids=[],
                )
                order.append(key)
            jobs_by_key[key].node_ids.append(node["id"])

    return [jobs_by_key[key] for key in order]
