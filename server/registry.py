"""
Client Registry - tracks all connected clients.
"""

import threading
from datetime import datetime
from typing import Callable, Dict, List, Optional

from pyfleet.common import ClientInfo, ClientStatus


class ClientRegistry:
    """Thread-safe registry of connected clients."""
    
    def __init__(
        self,
        heartbeat_timeout: float = 60.0,
        offline_timeout: float = 300.0,
    ):
        self._clients: Dict[str, ClientInfo] = {}
        self._lock = threading.RLock()
        self._heartbeat_timeout = heartbeat_timeout
        self._offline_timeout = offline_timeout
        
        self._on_enroll: List[Callable] = []
        self._on_status_change: List[Callable] = []
    
    def register(self, client_id: str, **kwargs) -> ClientInfo:
        """Register or update a client."""
        with self._lock:
            now = datetime.now()
            
            if client_id in self._clients:
                client = self._clients[client_id]
                for key, value in kwargs.items():
                    if hasattr(client, key):
                        setattr(client, key, value)
                client.last_seen = now
            else:
                client = ClientInfo(
                    client_id=client_id,
                    enrolled_at=now,
                    last_seen=now,
                    status=ClientStatus.ONLINE,
                    **kwargs
                )
                self._clients[client_id] = client
                self._trigger_enroll(client)
            
            return client
    
    def heartbeat(self, client_id: str) -> Optional[ClientInfo]:
        """Update client heartbeat."""
        with self._lock:
            if client_id in self._clients:
                client = self._clients[client_id]
                old_status = client.status
                client.last_heartbeat = datetime.now()
                client.last_seen = client.last_heartbeat
                
                if client.status != ClientStatus.ONLINE:
                    client.status = ClientStatus.ONLINE
                    self._trigger_status_change(client, old_status, ClientStatus.ONLINE)
                
                return client
        return None
    
    def get(self, client_id: str) -> Optional[ClientInfo]:
        """Get client by ID."""
        with self._lock:
            return self._clients.get(client_id)
    
    def get_all(self) -> List[ClientInfo]:
        """Get all clients."""
        with self._lock:
            return list(self._clients.values())
    
    def get_by_status(self, status: ClientStatus) -> List[ClientInfo]:
        """Get clients by status."""
        with self._lock:
            return [c for c in self._clients.values() if c.status == status]
    
    def get_by_tag(self, tag: str) -> List[ClientInfo]:
        """Get clients with a tag."""
        with self._lock:
            return [c for c in self._clients.values() if tag in c.tags]
    
    def add_tag(self, client_id: str, tag: str) -> bool:
        """Add tag to client."""
        with self._lock:
            if client_id in self._clients:
                self._clients[client_id].tags.add(tag)
                return True
        return False
    
    def remove(self, client_id: str) -> bool:
        """Remove a client."""
        with self._lock:
            if client_id in self._clients:
                del self._clients[client_id]
                return True
        return False
    
    def check_timeouts(self) -> List[ClientInfo]:
        """Check for timed-out clients."""
        changed = []
        now = datetime.now()
        
        with self._lock:
            for client in self._clients.values():
                if client.last_heartbeat is None:
                    continue
                
                elapsed = (now - client.last_heartbeat).total_seconds()
                old_status = client.status
                
                if elapsed > self._offline_timeout:
                    if client.status != ClientStatus.OFFLINE:
                        client.status = ClientStatus.OFFLINE
                        changed.append(client)
                        self._trigger_status_change(client, old_status, ClientStatus.OFFLINE)
                elif elapsed > self._heartbeat_timeout:
                    if client.status != ClientStatus.DEGRADED:
                        client.status = ClientStatus.DEGRADED
                        changed.append(client)
                        self._trigger_status_change(client, old_status, ClientStatus.DEGRADED)
        
        return changed
    
    def stats(self) -> Dict[str, int]:
        """Get registry stats."""
        with self._lock:
            stats = {s.value: 0 for s in ClientStatus}
            for c in self._clients.values():
                stats[c.status.value] += 1
            stats["total"] = len(self._clients)
            return stats
    
    def on_enroll(self, callback: Callable) -> None:
        """Register enrollment callback."""
        self._on_enroll.append(callback)
    
    def on_status_change(self, callback: Callable) -> None:
        """Register status change callback."""
        self._on_status_change.append(callback)
    
    def _trigger_enroll(self, client: ClientInfo) -> None:
        for cb in self._on_enroll:
            try:
                cb(client)
            except Exception:
                pass
    
    def _trigger_status_change(self, client: ClientInfo, old: ClientStatus, new: ClientStatus) -> None:
        for cb in self._on_status_change:
            try:
                cb(client, old, new)
            except Exception:
                pass
