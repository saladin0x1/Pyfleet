# Fleetspeak Protobuf Definitions Reference

> **Purpose**: Comprehensive documentation of all protobuf message types, enums, and gRPC services for future enhancements to PyFleet.
> 
> **Version**: fleetspeak v0.1.18 (Protobuf Python Version 5.29.0)

---

## Table of Contents

1. [Overview](#overview)
2. [Core Messages (fleetspeak.common)](#core-messages-fleetspeakcommon)
3. [System Messages (fleetspeak.system)](#system-messages-fleetspeaksystem)
4. [Client Messages](#client-messages)
5. [Server Admin API](#server-admin-api)
6. [gRPC Services](#grpc-services)
7. [Monitoring & Resources](#monitoring--resources)
8. [Configuration](#configuration)
9. [File Locations](#file-locations)
10. [Usage Examples](#usage-examples)

---

## Overview

Fleetspeak uses Protocol Buffers (protobuf) to define its communication contract between clients and servers. These definitions enable:

- **Type-safe serialization** - Messages are validated and efficiently encoded
- **Cross-language compatibility** - Go server, Python clients can interoperate
- **Schema evolution** - New fields can be added without breaking compatibility
- **gRPC integration** - Defines RPC service interfaces

### Architecture

```
┌─────────────────┐          ┌─────────────────┐
│   FleetClient   │  gRPC    │   FleetServer   │
│    (Python)     │◄────────►│    (Python/Go)  │
└─────────────────┘          └─────────────────┘
        │                            │
        └────────────────────────────┘
                     │
          common_pb2.Message
          (protobuf serialization)
```

---

## Core Messages (fleetspeak.common)

**File**: `fleetspeak/src/common/proto/fleetspeak/common_pb2.py`

### Message

The **central message type** used for all client-server communication.

```protobuf
message Message {
    bytes message_id = 1;              // Unique message identifier (32 bytes random)
    Address source = 2;                 // Message origin (client_id + service_name)
    bool is_blocklisted_source = 13;   // If source is on blocklist
    bytes source_message_id = 3;       // Related message ID (for responses)
    Address destination = 4;            // Message target (client_id + service_name)
    string message_type = 5;            // Message type identifier (e.g., "enrollment", "heartbeat")
    google.protobuf.Timestamp creation_time = 6;  // When message was created
    google.protobuf.Any data = 7;       // Payload (flexible type)
    ValidationInfo validation_info = 8; // Tags for validation
    MessageResult result = 9;           // Processing result
    Priority priority = 10;             // Message priority
    bool background = 11;               // Background processing flag
    Annotations annotations = 12;       // Key-value metadata
    
    enum Priority {
        MEDIUM = 0;
        LOW = 1;
        HIGH = 2;
    }
}
```

**Python Usage**:
```python
from fleetspeak.src.common.proto.fleetspeak import common_pb2

msg = common_pb2.Message()
msg.message_id = os.urandom(32)
msg.message_type = "status_report"
msg.source.service_name = "my_service"
msg.destination.client_id = b'\x01\x02...'
msg.priority = common_pb2.Message.Priority.HIGH

# Serialize
data = msg.SerializeToString()

# Deserialize  
parsed = common_pb2.Message()
parsed.ParseFromString(data)
```

---

### Address

Identifies the source or destination of a message.

```protobuf
message Address {
    bytes client_id = 1;      // 8-byte client identifier (empty for server)
    string service_name = 2;  // Service name (e.g., "pyfleet", "system")
}
```

**Python Usage**:
```python
addr = common_pb2.Address()
addr.client_id = bytes.fromhex("0102030405060708")
addr.service_name = "my_service"
```

---

### ValidationInfo

Tags for message validation.

```protobuf
message ValidationInfo {
    map<string, string> tags = 1;  // Key-value validation tags
}
```

---

### MessageResult

Result of message processing.

```protobuf
message MessageResult {
    google.protobuf.Timestamp processed_time = 2;  // When processed
    bool failed = 3;                                // Processing failed
    string failed_reason = 4;                       // Failure reason
}
```

---

### Annotations

Arbitrary key-value metadata.

```protobuf
message Annotations {
    repeated Entry entries = 1;
    
    message Entry {
        string key = 1;
        string value = 2;
    }
}
```

---

### Label

Service labels for client classification.

```protobuf
message Label {
    string service_name = 1;  // Service that applied the label
    string label = 2;         // Label value (e.g., "windows", "high-priority")
}
```

---

### Signature

Cryptographic signature for message authentication.

```protobuf
message Signature {
    repeated bytes certificate = 1;  // Certificate chain
    int32 algorithm = 2;             // Signature algorithm ID
    bytes signature = 3;             // Signature bytes
}
```

---

### WrappedContactData

Contact data with signatures for authentication.

```protobuf
message WrappedContactData {
    bytes contact_data = 1;         // Serialized ContactData
    repeated Signature signatures = 2;  // Authentication signatures
    repeated string client_labels = 3;  // Client labels
}
```

---

### ContactData

Data exchanged during client contact.

```protobuf
message ContactData {
    uint64 sequencing_nonce = 1;              // Sequence number for ordering
    repeated Message messages = 2;             // Messages to send
    google.protobuf.Timestamp client_clock = 3;  // Client's current time
    uint64 ack_index = 4;                      // Last acknowledged message index
    bool done_sending = 5;                     // No more messages in this contact
    map<string, uint64> AllowedMessages = 6;  // Per-service message limits
}
```

---

### EmptyMessage

Empty message for RPC responses.

```protobuf
message EmptyMessage {}
```

---

### CompressionAlgorithm (Enum)

```protobuf
enum CompressionAlgorithm {
    COMPRESSION_NONE = 0;
    COMPRESSION_DEFLATE = 1;
}
```

---

## System Messages (fleetspeak.system)

**File**: `fleetspeak/src/common/proto/fleetspeak/system_pb2.py`

### MessageAckData

Acknowledgment for received messages.

```protobuf
message MessageAckData {
    repeated bytes message_ids = 1;  // IDs of acknowledged messages
}
```

---

### MessageErrorData

Error notification for failed messages.

```protobuf
message MessageErrorData {
    bytes message_id = 1;  // Failed message ID
    string error = 2;      // Error description
}
```

---

### ClientInfoData

Client information sent during enrollment.

```protobuf
message ClientInfoData {
    repeated Label labels = 1;          // Client labels
    repeated ServiceID services = 2;    // Running services
    
    message ServiceID {
        string name = 1;       // Service name
        bytes signature = 2;   // Service binary signature
    }
}
```

---

### RemoveServiceData

Request to remove a service.

```protobuf
message RemoveServiceData {
    string name = 1;  // Service to remove
}
```

---

### ClientServiceConfig

Service configuration pushed to client.

```protobuf
message ClientServiceConfig {
    string name = 1;                           // Service name
    string factory = 2;                        // Service factory type
    google.protobuf.Any config = 3;            // Service-specific config
    repeated Label required_labels = 6;        // Required client labels
    google.protobuf.Timestamp signed_time = 7; // Config signing time
}
```

---

### ClientServiceConfigs

Multiple service configurations.

```protobuf
message ClientServiceConfigs {
    repeated ClientServiceConfig config = 1;
}
```

---

### SignedClientServiceConfig

Signed service configuration.

```protobuf
message SignedClientServiceConfig {
    bytes service_config = 1;  // Serialized ClientServiceConfig
    bytes signature = 2;       // Config signature
}
```

---

### RevokedCertificateList

List of revoked certificates.

```protobuf
message RevokedCertificateList {
    repeated bytes serials = 1;  // Revoked certificate serial numbers
}
```

---

### DieRequest

Request to terminate client.

```protobuf
message DieRequest {
    bool force = 1;  // Force termination
}
```

---

### RestartServiceRequest

Request to restart a service.

```protobuf
message RestartServiceRequest {
    string name = 1;  // Service to restart
}
```

---

## Client Messages

### Channel (fleetspeak.channel)

**File**: `fleetspeak/src/client/channel/proto/fleetspeak_channel/channel_pb2.py`

#### StartupData

Sent by daemon service on startup.

```protobuf
message StartupData {
    int64 pid = 1;      // Process ID
    string version = 2;  // Client version
}
```

---

### Client API (fleetspeak.client)

**File**: `fleetspeak/src/client/proto/fleetspeak_client/api_pb2.py`

#### ByteBlob

Simple byte container.

```protobuf
message ByteBlob {
    bytes data = 1;
}
```

#### APIMessage

API-level message wrapper.

```protobuf
message APIMessage {
    string type = 1;            // Message type
    google.protobuf.Any data = 2;  // Payload
}
```

---

### Client Configuration (fleetspeak.client)

**File**: `fleetspeak/src/client/proto/fleetspeak_client/client_pb2.py`

#### CommunicatorConfig

Client communication settings.

```protobuf
message CommunicatorConfig {
    int32 max_poll_delay_seconds = 2;       // Max delay between polls
    int32 max_buffer_delay_seconds = 3;     // Max delay before flushing buffer
    int32 min_failure_delay_seconds = 4;    // Min delay after failure
    int32 failure_suicide_time_seconds = 5; // Kill client after this many seconds of failure
    CompressionAlgorithm compression = 6;   // Compression algorithm
    bool prefer_http2 = 7;                  // Prefer HTTP/2 over HTTP/1.1
}
```

#### ClientState

Persistent client state.

```protobuf
message ClientState {
    bytes client_key = 1;                    // Client private key
    uint64 sequencing_nonce = 7;             // Current sequence number
    repeated bytes revoked_cert_serials = 8; // Revoked certificate serials
}
```

---

### Daemon Service Config (fleetspeak.daemonservice)

**File**: `fleetspeak/src/client/daemonservice/proto/fleetspeak_daemonservice/config_pb2.py`

#### Config

Configuration for daemon-managed services.

```protobuf
message Config {
    repeated string argv = 1;                           // Command line arguments
    google.protobuf.Duration inactivity_timeout = 2;    // Kill after inactivity
    bool lazy_start = 3;                                // Start on first message
    bool disable_resource_monitoring = 4;               // Disable resource tracking
    int32 resource_monitoring_sample_size = 5;          // Sample size for monitoring
    google.protobuf.Duration resource_monitoring_sample_period = 12;  // Sample period
    int64 memory_limit = 7;                             // Memory limit in bytes
    bool monitor_heartbeats = 8;                        // Monitor for heartbeats
    google.protobuf.Duration heartbeat_unresponsive_grace_period = 13;  // Grace period
    google.protobuf.Duration heartbeat_unresponsive_kill_period = 14;   // Kill period
    StdParams std_params = 11;                          // Stdout/stderr handling
    
    message StdParams {
        string service_name = 1;     // Service name for logging
        int32 flush_bytes = 2;       // Flush after bytes
        int32 flush_time_seconds = 3; // Flush after seconds
    }
}
```

---

### Stdin Service (fleetspeak.stdinservice)

**File**: `fleetspeak/src/client/stdinservice/proto/fleetspeak_stdinservice/messages_pb2.py`

#### InputMessage

Input to send to a process.

```protobuf
message InputMessage {
    bytes input = 1;          // Stdin data
    repeated string args = 2; // Command arguments
}
```

#### OutputMessage

Output from a process.

```protobuf
message OutputMessage {
    bytes stdout = 1;                        // Stdout data
    bytes stderr = 2;                        // Stderr data
    google.protobuf.Timestamp timestamp = 4; // Output time
}
```

---

## Server Admin API

**File**: `fleetspeak/src/server/proto/fleetspeak_server/admin_pb2.py`

### Client

Server-side client representation.

```protobuf
message Client {
    bytes client_id = 1;                              // Client identifier
    repeated Label labels = 2;                        // Client labels
    google.protobuf.Timestamp last_contact_time = 3;  // Last contact time
    string last_contact_address = 4;                  // Last known IP address
    string last_contact_streaming_to = 7;             // Streaming endpoint
    google.protobuf.Timestamp last_clock = 5;         // Client's last reported time
    bool blacklisted = 6;                             // Client is blacklisted
}
```

---

### ClientContact

Record of a client contact.

```protobuf
message ClientContact {
    fixed64 sent_nonce = 1;      // Nonce sent to client
    fixed64 received_nonce = 2;  // Nonce received from client
    string observed_address = 3; // Observed IP address
    google.protobuf.Timestamp timestamp = 4;  // Contact time
}
```

---

### Broadcast

Mass message to multiple clients.

```protobuf
message Broadcast {
    bytes broadcast_id = 1;                           // Broadcast identifier
    Address source = 2;                               // Source service
    string message_type = 3;                          // Message type
    repeated Label required_labels = 4;               // Target client labels
    google.protobuf.Timestamp expiration_time = 5;    // Expiration time
    google.protobuf.Any data = 6;                     // Payload
}
```

---

### Request/Response Messages

| Message | Purpose |
|---------|---------|
| `ListClientsRequest` | Request to list clients (`client_ids: bytes[]`) |
| `ListClientsResponse` | Response with clients (`clients: Client[]`) |
| `StreamClientIdsRequest` | Stream client IDs (`include_blacklisted`, `last_contact_after`) |
| `StreamClientIdsResponse` | Streaming response (`client_id: bytes`) |
| `CreateBroadcastRequest` | Create broadcast (`broadcast`, `limit`) |
| `ListActiveBroadcastsRequest` | List broadcasts (`service_name`) |
| `ListActiveBroadcastsResponse` | Response (`broadcasts[]`) |
| `GetMessageStatusRequest` | Get message status (`message_id`) |
| `GetMessageStatusResponse` | Response (`creation_time`, `result`) |
| `DeletePendingMessagesRequest` | Delete pending (`client_ids[]`) |
| `GetPendingMessagesRequest` | Get pending (`client_ids[]`, `offset`, `limit`, `want_data`) |
| `GetPendingMessagesResponse` | Response (`messages[]`) |
| `GetPendingMessageCountRequest` | Count pending (`client_ids[]`) |
| `GetPendingMessageCountResponse` | Response (`count`) |
| `StoreFileRequest` | Store file (`service_name`, `file_name`, `data`) |
| `ListClientContactsRequest` | List contacts (`client_id`) |
| `ListClientContactsResponse` | Response (`contacts[]`) |
| `StreamClientContactsRequest` | Stream contacts (`client_id`) |
| `StreamClientContactsResponse` | Streaming response (`contact`) |
| `BlacklistClientRequest` | Blacklist client (`client_id`) |
| `FetchClientResourceUsageRecordsRequest` | Get resource usage (`client_id`, `start_timestamp`, `end_timestamp`) |
| `FetchClientResourceUsageRecordsResponse` | Response (`records[]`) |

---

## gRPC Services

### Processor Service (fleetspeak.grpcservice)

**File**: `fleetspeak/src/server/grpcservice/proto/fleetspeak_grpcservice/grpcservice_pb2_grpc.py`

The primary service interface for message processing.

```protobuf
service Processor {
    // Process accepts a message and processes it
    rpc Process(fleetspeak.Message) returns (fleetspeak.EmptyMessage);
}
```

**Python Implementation**:
```python
from fleetspeak.src.server.grpcservice.proto.fleetspeak_grpcservice import grpcservice_pb2_grpc
from fleetspeak.src.common.proto.fleetspeak import common_pb2

class MyServicer(grpcservice_pb2_grpc.ProcessorServicer):
    def Process(self, request, context):
        # request is a common_pb2.Message
        print(f"Received: {request.message_type}")
        return common_pb2.EmptyMessage()

# Register with gRPC server
grpcservice_pb2_grpc.add_ProcessorServicer_to_server(MyServicer(), server)
```

---

### Admin Service (fleetspeak.server.Admin)

**File**: `fleetspeak/src/server/proto/fleetspeak_server/admin_pb2_grpc.py`

Comprehensive admin API for fleet management.

```protobuf
service Admin {
    // Broadcast management
    rpc CreateBroadcast(CreateBroadcastRequest) returns (EmptyMessage);
    rpc ListActiveBroadcasts(ListActiveBroadcastsRequest) returns (ListActiveBroadcastsResponse);
    
    // Client management
    rpc ListClients(ListClientsRequest) returns (ListClientsResponse);
    rpc StreamClientIds(StreamClientIdsRequest) returns (stream StreamClientIdsResponse);
    rpc ListClientContacts(ListClientContactsRequest) returns (ListClientContactsResponse);
    rpc StreamClientContacts(StreamClientContactsRequest) returns (stream StreamClientContactsResponse);
    rpc BlacklistClient(BlacklistClientRequest) returns (EmptyMessage);
    
    // Message management
    rpc GetMessageStatus(GetMessageStatusRequest) returns (GetMessageStatusResponse);
    rpc InsertMessage(Message) returns (EmptyMessage);
    rpc DeletePendingMessages(DeletePendingMessagesRequest) returns (EmptyMessage);
    rpc GetPendingMessages(GetPendingMessagesRequest) returns (GetPendingMessagesResponse);
    rpc GetPendingMessageCount(GetPendingMessageCountRequest) returns (GetPendingMessageCountResponse);
    
    // File management
    rpc StoreFile(StoreFileRequest) returns (EmptyMessage);
    
    // Utilities
    rpc KeepAlive(EmptyMessage) returns (EmptyMessage);
    
    // Resource monitoring
    rpc FetchClientResourceUsageRecords(FetchClientResourceUsageRecordsRequest) 
        returns (FetchClientResourceUsageRecordsResponse);
}
```

**Python Usage**:
```python
from fleetspeak.src.server.proto.fleetspeak_server import admin_pb2, admin_pb2_grpc
import grpc

channel = grpc.insecure_channel('localhost:8080')
stub = admin_pb2_grpc.AdminStub(channel)

# List clients
response = stub.ListClients(admin_pb2.ListClientsRequest())
for client in response.clients:
    print(f"Client: {client.client_id.hex()}")

# Insert message
msg = common_pb2.Message()
msg.destination.client_id = b'\x01\x02...'
msg.message_type = "command"
stub.InsertMessage(msg)
```

---

## Monitoring & Resources

### ClientResourceUsageRecord (fleetspeak.server)

**File**: `fleetspeak/src/server/proto/fleetspeak_server/resource_pb2.py`

```protobuf
message ClientResourceUsageRecord {
    string scope = 1;                                   // Resource scope
    int64 pid = 2;                                      // Process ID
    google.protobuf.Timestamp process_start_time = 3;  // Process start time
    google.protobuf.Timestamp client_timestamp = 4;    // Client-reported time
    google.protobuf.Timestamp server_timestamp = 5;    // Server-recorded time
    bool process_terminated = 12;                       // Process ended
    float mean_user_cpu_rate = 6;                       // Average user CPU usage
    float max_user_cpu_rate = 7;                        // Peak user CPU usage
    float mean_system_cpu_rate = 8;                     // Average system CPU usage
    float max_system_cpu_rate = 9;                      // Peak system CPU usage
    int32 mean_resident_memory_mib = 10;                // Average memory (MiB)
    int32 max_resident_memory_mib = 11;                 // Peak memory (MiB)
    int32 mean_num_fds = 13;                            // Average file descriptors
    int32 max_num_fds = 14;                             // Peak file descriptors
}
```

---

### AggregatedResourceUsage (fleetspeak.monitoring)

**File**: `fleetspeak/src/common/proto/fleetspeak_monitoring/resource_pb2.py`

```protobuf
message AggregatedResourceUsage {
    double mean_user_cpu_rate = 1;
    double max_user_cpu_rate = 2;
    double mean_system_cpu_rate = 3;
    double max_system_cpu_rate = 4;
    double mean_resident_memory = 5;
    int64 max_resident_memory = 6;
    int32 max_num_fds = 7;
    double mean_num_fds = 8;
}
```

---

### ResourceUsageData (fleetspeak.monitoring)

```protobuf
message ResourceUsageData {
    string scope = 1;
    int64 pid = 2;
    string version = 8;
    google.protobuf.Timestamp process_start_time = 3;
    google.protobuf.Timestamp data_timestamp = 4;
    AggregatedResourceUsage resource_usage = 5;
    string debug_status = 6;
    bool process_terminated = 7;
}
```

---

### KillNotification (fleetspeak.monitoring)

```protobuf
message KillNotification {
    string service = 1;
    int64 pid = 2;
    string version = 3;
    google.protobuf.Timestamp process_start_time = 4;
    google.protobuf.Timestamp killed_when = 5;
    Reason reason = 6;
    
    enum Reason {
        UNSPECIFIED = 0;
        HEARTBEAT_FAILURE = 1;
        MEMORY_EXCEEDED = 2;
    }
}
```

---

## Configuration

### ServiceConfig (fleetspeak.server)

**File**: `fleetspeak/src/server/proto/fleetspeak_server/services_pb2.py`

```protobuf
message ServiceConfig {
    string name = 1;              // Service name
    string factory = 2;           // Factory type (e.g., "GRPC")
    uint32 max_parallelism = 3;   // Max concurrent handlers
    google.protobuf.Any config = 4;  // Service-specific config
}
```

---

### Config (fleetspeak.config)

**File**: `fleetspeak/src/config/proto/fleetspeak_config/config_pb2.py`

```protobuf
message Config {
    string configuration_name = 1;                       // Config name
    fleetspeak.components.Config components_config = 2;  // Components config
    string trusted_cert_file = 3;                        // CA certificate file
    string trusted_cert_key_file = 4;                    // CA key file
    string server_cert_file = 5;                         // Server certificate file
    string server_cert_key_file = 6;                     // Server key file
    string server_component_configuration_file = 7;      // Server components config
    repeated string public_host_port = 8;                // Public endpoints
    string linux_client_configuration_file = 9;          // Linux client config
    string darwin_client_configuration_file = 10;        // macOS client config
    string windows_client_configuration_file = 11;       // Windows client config
    string server_name = 12;                             // Server name
}
```

---

## File Locations

| Category | File Path |
|----------|-----------|
| **Core** | |
| Common | `fleetspeak/src/common/proto/fleetspeak/common_pb2.py` |
| System | `fleetspeak/src/common/proto/fleetspeak/system_pb2.py` |
| Monitoring | `fleetspeak/src/common/proto/fleetspeak_monitoring/resource_pb2.py` |
| **Client** | |
| Client Config | `fleetspeak/src/client/proto/fleetspeak_client/client_pb2.py` |
| Client API | `fleetspeak/src/client/proto/fleetspeak_client/api_pb2.py` |
| Channel | `fleetspeak/src/client/channel/proto/fleetspeak_channel/channel_pb2.py` |
| Daemon Service | `fleetspeak/src/client/daemonservice/proto/fleetspeak_daemonservice/config_pb2.py` |
| Stdin Service | `fleetspeak/src/client/stdinservice/proto/fleetspeak_stdinservice/messages_pb2.py` |
| Socket Service | `fleetspeak/src/client/socketservice/proto/fleetspeak_socketservice/config_pb2.py` |
| Generic Client | `fleetspeak/src/client/generic/proto/fleetspeak_client_generic/config_pb2.py` |
| **Server** | |
| Admin | `fleetspeak/src/server/proto/fleetspeak_server/admin_pb2.py` |
| Admin gRPC | `fleetspeak/src/server/proto/fleetspeak_server/admin_pb2_grpc.py` |
| Services | `fleetspeak/src/server/proto/fleetspeak_server/services_pb2.py` |
| Broadcasts | `fleetspeak/src/server/proto/fleetspeak_server/broadcasts_pb2.py` |
| Resource | `fleetspeak/src/server/proto/fleetspeak_server/resource_pb2.py` |
| Server Config | `fleetspeak/src/server/proto/fleetspeak_server/server_pb2.py` |
| gRPC Service | `fleetspeak/src/server/grpcservice/proto/fleetspeak_grpcservice/grpcservice_pb2.py` |
| gRPC Service Stub | `fleetspeak/src/server/grpcservice/proto/fleetspeak_grpcservice/grpcservice_pb2_grpc.py` |
| **Config** | |
| Main Config | `fleetspeak/src/config/proto/fleetspeak_config/config_pb2.py` |
| Components | `fleetspeak/src/server/components/proto/fleetspeak_components/config_pb2.py` |
| **Testing** | |
| FRR | `fleetspeak/src/inttesting/frr/proto/fleetspeak_frr/frr_pb2.py` |

---

## Usage Examples

### Creating and Sending a Message

```python
from fleetspeak.src.common.proto.fleetspeak import common_pb2
from google.protobuf import any_pb2
import json
import os

# Create a message
msg = common_pb2.Message()
msg.message_id = os.urandom(32)
msg.message_type = "status_update"

# Set source (client sending)
msg.source.service_name = "my_agent"

# Set destination (server receiving)
msg.destination.service_name = "pyfleet"

# Pack JSON data into Any field
payload = any_pb2.Any()
payload.Pack(common_pb2.ByteBlob(data=json.dumps({"cpu": 45.2}).encode()))
msg.data.CopyFrom(payload)

# Set priority
msg.priority = common_pb2.Message.Priority.HIGH

# Serialize to bytes
wire_data = msg.SerializeToString()
```

### Implementing a gRPC Servicer

```python
from fleetspeak.src.server.grpcservice.proto.fleetspeak_grpcservice import grpcservice_pb2_grpc
from fleetspeak.src.common.proto.fleetspeak import common_pb2
import grpc
from concurrent import futures

class FleetServicer(grpcservice_pb2_grpc.ProcessorServicer):
    def Process(self, request: common_pb2.Message, context):
        client_id = request.source.client_id.hex()
        msg_type = request.message_type
        
        if msg_type == "enrollment":
            print(f"New client enrolled: {client_id}")
        elif msg_type == "heartbeat":
            print(f"Heartbeat from: {client_id}")
        else:
            print(f"Message from {client_id}: {msg_type}")
        
        return common_pb2.EmptyMessage()

# Start server
server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
grpcservice_pb2_grpc.add_ProcessorServicer_to_server(FleetServicer(), server)
server.add_insecure_port('[::]:9999')
server.start()
```

### Using the Admin API

```python
from fleetspeak.src.server.proto.fleetspeak_server import admin_pb2, admin_pb2_grpc
import grpc

# Connect to server
channel = grpc.insecure_channel('localhost:8080')
stub = admin_pb2_grpc.AdminStub(channel)

# List all clients
response = stub.ListClients(admin_pb2.ListClientsRequest())
for client in response.clients:
    print(f"Client: {client.client_id.hex()}")
    print(f"  Last contact: {client.last_contact_time}")
    print(f"  Address: {client.last_contact_address}")
    print(f"  Labels: {[l.label for l in client.labels]}")

# Get pending message count
count_response = stub.GetPendingMessageCount(
    admin_pb2.GetPendingMessageCountRequest(client_ids=[b'\x01\x02...'])
)
print(f"Pending messages: {count_response.count}")

# Blacklist a client
stub.BlacklistClient(admin_pb2.BlacklistClientRequest(client_id=b'\x01\x02...'))
```

---

## Future Enhancement Opportunities

Based on the protobuf definitions, here are potential enhancement areas for PyFleet:

### 1. **Broadcast Support**
Implement `CreateBroadcast` and `ListActiveBroadcasts` for mass messaging.

### 2. **Resource Monitoring**
Add resource tracking using `ResourceUsageData` and `AggregatedResourceUsage`.

### 3. **Service Management**
Implement `ClientServiceConfig` for dynamic service deployment.

### 4. **Message Persistence**
Use `GetPendingMessages` and `DeletePendingMessages` for message queuing.

### 5. **Certificate Management**
Leverage `Signature`, `RevokedCertificateList` for TLS/mTLS.

### 6. **Daemon Service Integration**
Support `Config` from `daemonservice` for process management.

### 7. **Streaming APIs**
Implement `StreamClientIds` and `StreamClientContacts` for real-time updates.

---

*Generated: 2024 | Based on fleetspeak PyPI package v0.1.18*
