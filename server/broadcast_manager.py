"""
Broadcast Manager - In-memory broadcast storage and management.
"""

import os
import threading
from datetime import datetime
from typing import Dict, List, Optional

from pyfleet.common import Address, Label
from pyfleet.common.broadcast import Broadcast


class BroadcastManager:
    """
    Manages broadcasts for mass-messaging to clients.
    
    Broadcasts are stored in-memory and matched against client labels.
    """
    
    def __init__(self):
        self._broadcasts: Dict[str, Broadcast] = {}
        self._lock = threading.RLock()
    
    def create(
        self,
        message_type: str,
        data: bytes = b"",
        required_labels: Optional[List[Label]] = None,
        expiration_time: Optional[datetime] = None,
        source_service: str = "pyfleet",
    ) -> Broadcast:
        """Create a new broadcast."""
        broadcast_id = os.urandom(16)
        
        broadcast = Broadcast(
            broadcast_id=broadcast_id,
            source=Address(service_name=source_service),
            message_type=message_type,
            required_labels=required_labels or [],
            expiration_time=expiration_time,
            data=data,
        )
        
        with self._lock:
            self._broadcasts[broadcast_id.hex()] = broadcast
        
        return broadcast
    
    def get(self, broadcast_id: str) -> Optional[Broadcast]:
        """Get a broadcast by ID."""
        with self._lock:
            return self._broadcasts.get(broadcast_id)
    
    def get_active(self) -> List[Broadcast]:
        """Get all active (non-expired) broadcasts."""
        with self._lock:
            active = []
            expired_ids = []
            
            for bid, broadcast in self._broadcasts.items():
                if broadcast.is_expired():
                    expired_ids.append(bid)
                else:
                    active.append(broadcast)
            
            # Clean up expired
            for bid in expired_ids:
                del self._broadcasts[bid]
            
            return active
    
    def delete(self, broadcast_id: str) -> bool:
        """Delete a broadcast."""
        with self._lock:
            if broadcast_id in self._broadcasts:
                del self._broadcasts[broadcast_id]
                return True
            return False
    
    def get_for_client(self, client_labels: List[Label]) -> List[Broadcast]:
        """Get broadcasts matching a client's labels."""
        matching = []
        for broadcast in self.get_active():
            if broadcast.matches_labels(client_labels):
                matching.append(broadcast)
        return matching
    
    def stats(self) -> Dict[str, int]:
        """Get broadcast statistics."""
        with self._lock:
            return {
                "total": len(self._broadcasts),
                "active": len([b for b in self._broadcasts.values() if not b.is_expired()]),
            }
