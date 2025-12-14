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
