"""
Common types and utilities shared between server and client.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional, Set, List
import json
import os


class ClientStatus(Enum):
    """Client connection status."""
    ONLINE = "online"
    OFFLINE = "offline"
    DEGRADED = "degraded"
    ENROLLING = "enrolling"


class Priority(Enum):
    """Message priority levels (matches protobuf Message.Priority)."""
    MEDIUM = 0
    LOW = 1
    HIGH = 2


@dataclass
class Address:
    """
    Identifies the source or destination of a message.
    Matches: fleetspeak.common.Address
    """
    client_id: bytes = b""  # 8-byte client identifier (empty for server)
    service_name: str = ""  # Service name (e.g., "pyfleet", "system")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "client_id": self.client_id.hex() if self.client_id else "",
            "service_name": self.service_name,
        }
    
    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Address":
        client_id = bytes.fromhex(d.get("client_id", "")) if d.get("client_id") else b""
        return cls(client_id=client_id, service_name=d.get("service_name", ""))


@dataclass
class ValidationInfo:
    """
    Tags for message validation.
    Matches: fleetspeak.common.ValidationInfo
    """
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class MessageResult:
    """
    Result of message processing.
    Matches: fleetspeak.common.MessageResult
    """
    processed_time: Optional[datetime] = None
    failed: bool = False
    failed_reason: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "processed_time": self.processed_time.isoformat() if self.processed_time else None,
            "failed": self.failed,
            "failed_reason": self.failed_reason,
        }


@dataclass
class AnnotationEntry:
    """Single annotation entry."""
    key: str = ""
    value: str = ""


@dataclass
class Annotations:
    """
    Arbitrary key-value metadata.
    Matches: fleetspeak.common.Annotations
    """
    entries: List["AnnotationEntry"] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, str]:
        return {e.key: e.value for e in self.entries}
    
    def add(self, key: str, value: str) -> None:
        self.entries.append(AnnotationEntry(key=key, value=value))
    
    def get(self, key: str, default: str = "") -> str:
        for e in self.entries:
            if e.key == key:
                return e.value
        return default


@dataclass
class Label:
    """
    Service labels for client classification.
    Matches: fleetspeak.common.Label
    """
    service_name: str = ""  # Service that applied the label
    label: str = ""         # Label value (e.g., "windows", "high-priority")
    
    def to_dict(self) -> Dict[str, str]:
        return {"service_name": self.service_name, "label": self.label}


@dataclass
class ClientInfo:
    """Information about a connected client."""
    client_id: str
    hostname: str = ""
    os_type: str = ""
    os_version: str = ""
    agent_version: str = ""
    ip_address: str = ""
    tags: Set[str] = field(default_factory=set)
    
    status: ClientStatus = ClientStatus.ENROLLING
    enrolled_at: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    last_heartbeat: Optional[datetime] = None
    
    message_count: int = 0
    error_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "client_id": self.client_id,
            "hostname": self.hostname,
            "os_type": self.os_type,
            "os_version": self.os_version,
            "agent_version": self.agent_version,
            "ip_address": self.ip_address,
            "tags": list(self.tags),
            "status": self.status.value,
            "enrolled_at": self.enrolled_at.isoformat() if self.enrolled_at else None,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "message_count": self.message_count,
        }


@dataclass
class Message:
    """Simple message format for communication."""
    type: str
    source_id: str = ""
    destination_id: str = ""
    data: bytes = b""
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def to_json(self) -> bytes:
        return json.dumps({
            "type": self.type,
            "source_id": self.source_id,
            "destination_id": self.destination_id,
            "data": self.data.decode() if self.data else "",
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }).encode()
    
    @classmethod
    def from_json(cls, data: bytes) -> "Message":
        d = json.loads(data.decode())
        return cls(
            type=d.get("type", ""),
            source_id=d.get("source_id", ""),
            destination_id=d.get("destination_id", ""),
            data=d.get("data", "").encode(),
            timestamp=datetime.fromisoformat(d["timestamp"]) if d.get("timestamp") else None,
        )


@dataclass 
class Command:
    """Command to be sent to a client."""
    command_id: str
    command_type: str
    payload: bytes = b""
    target_id: str = ""
    created_at: Optional[datetime] = None
    
    def __post_init__(self):
        if not self.command_id:
            self.command_id = os.urandom(16).hex()
        if self.created_at is None:
            self.created_at = datetime.now()
