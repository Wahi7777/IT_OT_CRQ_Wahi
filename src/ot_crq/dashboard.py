"""Presentation adapter for the combined IT/OT workbook.

The governed OT v1.7 calculation engine imports these hooks after it has written
all native calculation/result sheets. In the combined product the common
00-series dashboards are workbook-formula driven, so no separate native OT
dashboard writer is required. These hooks intentionally do not alter model
inputs, calculations, simulations, or result tables.
"""

def build_payload(**kwargs):
    return kwargs


def write_executive_dashboard(workbook, payload):
    return None
