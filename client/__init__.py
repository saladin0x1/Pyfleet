"""
PyFleet Client Module

Auto-enrolling fleet agent with:
- Automatic enrollment
- Heartbeat sending
- Reconnection handling
"""

from pyfleet.client.fleet_client import FleetClient

__all__ = ["FleetClient"]
