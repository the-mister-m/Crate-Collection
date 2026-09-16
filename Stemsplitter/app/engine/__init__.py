"""Headless separation engine for Stem Splitter.

Consumes the run config dict (docs/00-locked-spec.md) and produces
mixed, encoded output files per node. No UI code, no UI imports.
See pipeline.run() for the entry point.
"""

from .pipeline import run
from .types import ErrorRecord, Job, JobResult, RunReport, WrittenFile

__all__ = ["run", "ErrorRecord", "Job", "JobResult", "RunReport", "WrittenFile"]
