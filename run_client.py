#!/usr/bin/env python3
"""Demo: Start a PyFleet client agent."""

import sys
import os
import time
import random
import logging
import json
import urllib.request
import urllib.error

# Add paths for imports
_here = os.path.dirname(os.path.abspath(__file__))
_root = os.path.abspath(os.path.join(_here, "..", "..", ".."))
sys.path.insert(0, os.path.dirname(_here))  # for pyfleet
sys.path.insert(0, _root)  # for fleetspeak

from absl import app, flags

FLAGS = flags.FLAGS
flags.DEFINE_string('server', 'localhost:9999', 'Server address')
flags.DEFINE_string('name', None, 'Agent name')
flags.DEFINE_string('token', None, 'Enrollment token')
flags.DEFINE_string('dashboard', None, 'Dashboard URL (default: derive from server)')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%H:%M:%S'
)


# Broadcast polling helper
_seen_broadcasts = set()

def poll_broadcasts(client_id: str, dashboard_url: str):
    """Poll dashboard for pending broadcasts."""
    global _seen_broadcasts
    try:
        url = f"{dashboard_url}/api/broadcasts/pending/{client_id}"
        with urllib.request.urlopen(url, timeout=5) as resp:
            broadcasts = json.loads(resp.read().decode())
        
        for b in broadcasts:
            bid = b.get('id', '')
            if bid in _seen_broadcasts:
                continue
            
            _seen_broadcasts.add(bid)
            msg_type = b.get('message_type', '?')
            data = b.get('data', '')
            print(f"\n  [!] BROADCAST RECEIVED: {msg_type}")
            if data:
                print(f"      Data: {data[:100]}")
    except urllib.error.URLError:
        pass
    except Exception as e:
        logging.debug(f"Broadcast poll error: {e}")


def main(argv):
    from pyfleet import FleetClient
    
    name = FLAGS.name or str(random.randint(1000, 9999))
    
    # Derive dashboard URL from server address
    if FLAGS.dashboard:
        dashboard_url = FLAGS.dashboard
    else:
        host = FLAGS.server.split(":")[0]
        dashboard_url = f"http://{host}:5000"
    
    print("=" * 50)
    print(f"  PyFleet Client ({name})")
    print("=" * 50)
    
    client = FleetClient(
        server_address=FLAGS.server,
        agent_version="1.0.0",
        tags=[f"agent-{name}"],
    )
    
    try:
        client.start()
        print(f"\n  Connected as {client.client_id[:20]}...")
        print(f"  Dashboard: {dashboard_url}")
        print("  Press Ctrl+C to stop\n")
        
        count = 0
        while True:
            time.sleep(random.uniform(5, 10))
            count += 1
            
            # Poll for broadcasts
            poll_broadcasts(client.client_id, dashboard_url)
            
            data = {
                "cpu": random.uniform(10, 90),
                "memory": random.uniform(20, 80),
                "count": count,
            }
            if client.send_json("status", data):
                print(f"  [>] Sent status #{count}")
    
    except KeyboardInterrupt:
        print("\n  Stopping...")
    finally:
        client.stop()
        print(f"  Stats: {client.stats()}")


if __name__ == "__main__":
    app.run(main)

