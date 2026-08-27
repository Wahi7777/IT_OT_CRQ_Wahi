"""Combined IT/OT CRQ launcher.

The launcher is deliberately an orchestration layer. It does not blend the
organisation-level IT methodology with the facility-level OT methodology.
"""

from .router import run_combined

__version__ = "1.0.0"
__all__ = ["run_combined"]
