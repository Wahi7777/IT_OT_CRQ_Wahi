"""Combined IT/OT CRQ package."""

from .versions import PLATFORM_VERSION

__version__ = PLATFORM_VERSION
# Historical workbook/router identifiers. They are intentionally not aliases
# for the platform release and must not be cosmetically rewritten.
COMBINED_MODEL_VERSION = "1.0.0"
ROUTER_VERSION = "1.0.0"
