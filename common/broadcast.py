"""
Broadcast types for PyFleet.
Matches: fleetspeak.server.admin broadcast-related protobuf definitions.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from pyfleet.common import Address, Label


@dataclass
class Broadcast:
    """
    Mass message to multiple clients.
    Matches: fleetspeak.server.admin.Broadcast
    """
    broadcast_id: bytes = b""
    source: Optional[Address] = None
    message_type: str = ""
    required_labels: List[Label] = field(default_factory=list)
    expiration_time: Optional[datetime] = None
    data: bytes = b""
    
    def __post_init__(self):
        if self.source is None:
            self.source = Address()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "broadcast_id": self.broadcast_id.hex() if self.broadcast_id else "",
            "source": self.source.to_dict() if self.source else None,
            "message_type": self.message_type,
            "required_labels": [lbl.to_dict() for lbl in self.required_labels],
            "expiration_time": self.expiration_time.isoformat() if self.expiration_time else None,
            "data": self.data.hex() if self.data else "",
        }
    
    def is_expired(self) -> bool:
        """Check if broadcast has expired."""
        if self.expiration_time is None:
            return False
        return datetime.now() > self.expiration_time
    
    def matches_labels(self, client_labels: List[Label]) -> bool:
        """Check if client labels match required labels."""
        if not self.required_labels:
            return True  # No label requirements means all clients match
        
        client_label_set = {(l.service_name, l.label) for l in client_labels}
        for required in self.required_labels:
            if (required.service_name, required.label) not in client_label_set:
                return False
        return True


@dataclass
class CreateBroadcastRequest:
    """Request to create a broadcast."""
    broadcast: Optional[Broadcast] = None
    limit: int = 0  # Max number of clients
    
    def __post_init__(self):
        if self.broadcast is None:
            self.broadcast = Broadcast()


@dataclass
class ListActiveBroadcastsRequest:
    """Request to list active broadcasts."""
    service_name: str = ""


@dataclass
class ListActiveBroadcastsResponse:
    """Response with active broadcasts."""
    broadcasts: List[Broadcast] = field(default_factory=list)
