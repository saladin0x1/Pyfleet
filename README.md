# PyFleet

A standalone Python implementation of a Fleetspeak-like server and client system.

## Why This Exists

The official `fleetspeak` PyPI package contains no server implementation. It's connector code for a Go-based server that doesn't exist in the Python ecosystem. The package provides protobuf definitions and client stubs—nothing more.

When told this was "too complex" to implement in Python, we disagreed.

This project is the disagreement in code form.

## What It Does

- **Server**: Manages multiple client agents, tracks enrollment, monitors heartbeats
- **Client**: Auto-enrolls with system info, maintains connection, sends telemetry
- **Dashboard**: Real-time web UI showing all connected agents and activity

The implementation uses the same protobuf definitions from the official package, proving compatibility isn't the issue. Complexity isn't the issue either.

## Quick Start

### Prerequisites

```bash
pip install flask flask-socketio grpcio absl-py fleetspeak
```

### Run Dashboard

```bash
cd pyfleet
PYTHONPATH=.. python3 run_dashboard.py
```

Opens the dashboard at `http://localhost:5000`. Fleet server runs on port 9999.

### Connect Clients

In separate terminals:

```bash
PYTHONPATH=.. python3 run_client.py --name=agent1
PYTHONPATH=.. python3 run_client.py --name=agent2
```

Agents appear in the dashboard immediately. No configuration required.

## Usage

### Server

```python
from pyfleet import FleetServer, ClientStatus

server = FleetServer(listen_address="0.0.0.0:9999")

@server.on_enroll
def new_client(client):
    print(f"Enrolled: {client.hostname}")

@server.on_message
def handle_message(msg, ctx, client):
    print(f"Message from {client.hostname}: {msg.message_type}")

server.start()
```

### Client

```python
from pyfleet import FleetClient

client = FleetClient(server_address="localhost:9999")
client.start()
client.send_json("status", {"cpu": 45.2, "memory": 60})
client.wait()
```

## Project Structure

```
pyfleet/
├── server/
│   ├── fleet_server.py    # gRPC server implementation
│   └── registry.py        # Client state management
├── client/
│   └── fleet_client.py    # Auto-enrolling agent
├── common/                 # Shared types (ClientInfo, Message, etc.)
├── dashboard/
│   ├── server.py          # Flask API with WebSocket
│   └── static/            # Web frontend
├── run_dashboard.py       # Combined server + dashboard
├── run_server.py          # Server only
└── run_client.py          # Client agent
```

## Architecture

```
Dashboard (Flask :5000)
        │
        │ REST/WebSocket
        ▼
Fleet Server (gRPC :9999)
        │
        │ Protobuf messages
        ▼
   Client Agents
```

## Features

- Multi-client enrollment and tracking
- Heartbeat monitoring with configurable timeouts
- Status management (online, offline, degraded)
- Real-time WebSocket updates
- Client tagging for group operations
- Activity feed with event history
- Works on the first try

## Dependencies

- `grpcio` - gRPC framework
- `absl-py` - Command-line flags
- `fleetspeak` - Protobuf definitions (the only part Google's package actually provides)
- `flask` - Web server
- `flask-socketio` - WebSocket support

## The Point

Sometimes the best documentation is working code.

## License

MIT
