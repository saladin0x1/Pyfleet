# PyFleet Project Summary

## Background

We started by exploring the official `fleetspeak` PyPI package (v0.1.18) to understand how it works and build high-level wrappers around it.

## Key Discovery

**The PyPI package has NO server implementation.**

After investigation, we confirmed:

- The `fleetspeak` PyPI package is a **connector library** for Google's GRR (Rapid Response) project
- The actual Fleetspeak server/client is written in **Go** (see github.com/google/fleetspeak)
- The Python package only provides:
  - `client_connector/` - For Python code running under the Go Fleetspeak daemon
  - `server_connector/` - For Python backends to connect TO the Go Fleetspeak server
  - `src/` - Protobuf definitions (message formats, gRPC interfaces)

**The Python package was never meant to be standalone - it's glue code for the Go infrastructure.**

## What the Protobufs Gave Us

The `*_pb2.py` and `*_pb2_grpc.py` files define:

| File | What It Contains |
|------|------------------|
| `common_pb2.py` | Message format (fields, types) |
| `grpcservice_pb2_grpc.py` | gRPC interface (`ProcessorServicer`, `ProcessorStub`) |
| `admin_pb2.py` | Admin operations (ListClients, etc.) |

These are essentially the **API contract** of the Go server - we used them to build our own Python implementation.

## Why We Built PyFleet

Since the PyPI package has no server, we built one:

1. **Standalone** - Works without Go infrastructure
2. **Multi-client** - Manages multiple agents like Kibana Fleet
3. **Modular** - Clean package structure for sharing
4. **Uses official protobufs** - Compatible message format

## What PyFleet Contains

```
pyfleet/
├── common/              # Shared types
│   └── __init__.py      # ClientStatus, ClientInfo, Message, Command
├── server/              # Server module
│   ├── registry.py      # ClientRegistry - tracks connected clients
│   └── fleet_server.py  # FleetServer - gRPC server with handlers
├── client/              # Client module
│   └── fleet_client.py  # FleetClient - auto-enrolling agent
├── run_server.py        # Demo server script
├── run_client.py        # Demo client script
└── README.md
```

## Features

### FleetServer
- Client enrollment and tracking
- Status management (online/offline/degraded)
- Heartbeat monitoring with configurable timeouts
- Decorator-based message handlers (`@server.on_message`)
- Command dispatch to individual or groups of clients
- Client tagging for group management

### FleetClient
- Auto-enrollment with system info (hostname, OS, version)
- Automatic heartbeat sending
- Reconnection handling
- Simple API (`send()`, `send_json()`)

## How to Run

```bash
# Terminal 1: Start server
python3 pyfleet/run_server.py

# Terminal 2: Start client
python3 pyfleet/run_client.py --name=agent1
```

## Usage Example

### Server
```python
from pyfleet import FleetServer, ClientStatus

server = FleetServer(listen_address="0.0.0.0:9999")

@server.on_enroll
def new_client(client):
    print(f"New: {client.hostname}")

@server.on_message
def message(msg, ctx, client):
    print(f"From {client.hostname}: {msg.message_type}")

server.start()
```

### Client
```python
from pyfleet import FleetClient

client = FleetClient(server_address="localhost:9999")
client.start()
client.send_json("status", {"cpu": 45.2})
client.wait()
```

## Dependencies

```
grpcio
absl-py
```

Plus the `fleetspeak` PyPI package for protobuf definitions.

## Next Steps

1. ✅ Copy to `~/pyfleet` (separate from fleetspeak download)
2. [ ] Create `setup.py` or `pyproject.toml` for pip install
3. [ ] Bundle the needed protobuf files (remove fleetspeak dependency)
4. [ ] Add TLS/authentication
5. [ ] Add message persistence
6. [ ] Publish to PyPI

## Key Takeaway

The official `fleetspeak` PyPI package is **not a fleet management system** - it's a connector for the Go-based Fleetspeak used by GRR. We built PyFleet as a **standalone Python alternative** using the same message format.
