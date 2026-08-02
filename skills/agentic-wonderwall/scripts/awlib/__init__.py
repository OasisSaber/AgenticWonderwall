"""/aw executor package: deterministic file operations for AW adoption.

This package implements the deterministic executor layer of the /aw unified
entrypoint. The Skill layer understands and orchestrates; this layer performs
inspect / plan-adopt / apply-adopt / verify with machine-checkable results.

Only the Python standard library is used.
"""

from .util import SCHEMA_VERSION, AwError, PathSafetyError

__all__ = ["SCHEMA_VERSION", "AwError", "PathSafetyError"]
