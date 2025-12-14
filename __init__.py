"""
PyFleet - Python Fleetspeak Server/Client Implementation

A standalone Python implementation inspired by Google's Fleetspeak,
built using the protobuf definitions from the official package.

Usage:
    from pyfleet.server import FleetServer
    from pyfleet.client import FleetClient
"""

__version__ = "0.1.0"
__author__ = "Your Team"

from pyfleet.server import FleetServer
from pyfleet.client import FleetClient
from pyfleet.common import Message, ClientStatus, ClientInfo

__all__ = [
    "FleetServer",
    "FleetClient",
    "Message",
    "ClientStatus",
    "ClientInfo",
]
