#!/usr/bin/env python3
"""Demo: Start a PyFleet server."""

import sys
import os
import time
import logging

# Add paths for imports
_here = os.path.dirname(os.path.abspath(__file__))
_root = os.path.abspath(os.path.join(_here, "..", "..", ".."))
sys.path.insert(0, os.path.dirname(_here))  # for pyfleet
sys.path.insert(0, _root)  # for fleetspeak

from absl import app

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%H:%M:%S'
)

def main(argv):
    from pyfleet import FleetServer, ClientStatus
    
    print("=" * 50)
    print("  PyFleet Server")
    print("=" * 50)
    
    server = FleetServer(listen_address="0.0.0.0:9999")
    
    @server.on_enroll
    def enrolled(client):
        print(f"\n  [+] New client: {client.hostname} ({client.client_id[:16]}...)")
    
    @server.on_status_change
    def status(client, old, new):
        print(f"  [~] {client.hostname}: {old.value} -> {new.value}")
    
    @server.on_message
    def message(msg, ctx, client):
        if msg.message_type not in ("heartbeat", "enrollment"):
            name = client.hostname if client else "?"
            print(f"  [<] {name}: {msg.message_type}")
    
    server.start()
    print(f"\n  Listening on 0.0.0.0:9999")
    print("  Press Ctrl+C to stop\n")
    
    try:
        while True:
            time.sleep(30)
            stats = server.clients.stats()
            print(f"  [i] Clients: {stats['total']} total, {stats['online']} online")
    except KeyboardInterrupt:
        print("\n  Stopping...")
        server.stop()


if __name__ == "__main__":
    app.run(main)
