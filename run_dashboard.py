#!/usr/bin/env python3
"""
PyFleet Dashboard - Start server with web dashboard.

Usage:
    python3 run_dashboard.py

Opens dashboard at http://localhost:5000
Fleet server runs on port 9999
"""

import sys
import os
import time
import logging
import webbrowser

# Add paths for imports
_here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_here))

from absl import app

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%H:%M:%S'
)

# Suppress Flask logging
logging.getLogger('werkzeug').setLevel(logging.WARNING)


def main(argv):
    from pyfleet import FleetServer
    from pyfleet.dashboard import DashboardServer
    
    print()
    print("╔══════════════════════════════════════════════════╗")
    print("║              PyFleet Dashboard                   ║")
    print("╠══════════════════════════════════════════════════╣")
    print("║  Fleet Server:  0.0.0.0:9999  (gRPC)            ║")
    print("║  Dashboard:     http://localhost:5000           ║")
    print("╚══════════════════════════════════════════════════╝")
    print()
    
    # Start Fleet Server
    fleet = FleetServer(listen_address="0.0.0.0:9999")
    fleet.start()
    print("  ✓ Fleet server started on port 9999")
    
    # Start Dashboard
    dashboard = DashboardServer(fleet, port=5000)
    dashboard.start()
    print("  ✓ Dashboard started on port 5000")
    
    # Open browser
    time.sleep(1)
    print()
    print("  Opening dashboard in browser...")
    webbrowser.open("http://localhost:5000")
    
    print()
    print("  Press Ctrl+C to stop")
    print()
    
    try:
        while True:
            time.sleep(30)
            stats = fleet.clients.stats()
            print(f"  [stats] {stats['total']} agents | {stats['online']} online | {stats['degraded']} degraded | {stats['offline']} offline")
    except KeyboardInterrupt:
        print()
        print("  Stopping...")
        fleet.stop()
        dashboard.stop()
        print("  Done.")


if __name__ == "__main__":
    app.run(main)
