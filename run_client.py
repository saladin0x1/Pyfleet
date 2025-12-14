#!/usr/bin/env python3
"""Demo: Start a PyFleet client agent."""

import sys
import os
import time
import random
import logging

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

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%H:%M:%S'
)

def main(argv):
    from pyfleet import FleetClient
    
    name = FLAGS.name or str(random.randint(1000, 9999))
    
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
        print("  Press Ctrl+C to stop\n")
        
        count = 0
        while True:
            time.sleep(random.uniform(5, 10))
            count += 1
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
