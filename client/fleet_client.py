"""
FleetClient - Auto-enrolling fleet agent.
"""

import json
import logging
import platform
import socket
import threading
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

import grpc

from fleetspeak.src.common.proto.fleetspeak import common_pb2
from fleetspeak.src.server.grpcservice.proto.fleetspeak_grpcservice import grpcservice_pb2_grpc

logger = logging.getLogger(__name__)


class FleetClient:
    """
    Auto-enrolling fleet agent.
    
    Example:
        client = FleetClient(server_address="localhost:9999")
        
        @client.on_command
        def cmd(command_type, payload):
            print(f"Command: {command_type}")
        
        client.start()
        client.send_json("status", {"cpu": 45})
        client.wait()
    """
    
    def __init__(
        self,
        server_address: str = "localhost:9999",
        client_id: Optional[str] = None,
        agent_version: str = "1.0.0",
        heartbeat_interval: float = 15.0,  # 15s heartbeat
        tags: Optional[List[str]] = None,
    ):
        self.server_address = server_address
        self.client_id = client_id or self._generate_id()
        self.agent_version = agent_version
        self.heartbeat_interval = heartbeat_interval
        self.tags = tags or []
        
        self._channel: Optional[grpc.Channel] = None
        self._stub = None
        self._connected = False
        self._enrolled = False
        self._running = False
        
        self._heartbeat_thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        
        self._command_handlers: List[Callable] = []
        
        self._stats = {
            "sent": 0,
            "failed": 0,
            "heartbeats": 0,
        }
    
    def _generate_id(self) -> str:
        hostname = socket.gethostname()
        mac = uuid.getnode()
        return f"{hostname}-{mac}"[:32]
    
    def _system_info(self) -> Dict[str, Any]:
        # Get container's own IP
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
        except:
            ip = "unknown"
        
        return {
            "hostname": socket.gethostname(),
            "os_type": platform.system(),
            "os_version": platform.version(),
            "agent_version": self.agent_version,
            "ip_address": ip,
            "tags": self.tags,
        }
    
    def on_command(self, handler: Callable) -> Callable:
        """Decorator for command handlers."""
        self._command_handlers.append(handler)
        return handler
    
    def connect(self) -> bool:
        """Connect to server."""
        try:
            self._channel = grpc.insecure_channel(self.server_address)
            self._stub = grpcservice_pb2_grpc.ProcessorStub(self._channel)
            grpc.channel_ready_future(self._channel).result(timeout=10)
            self._connected = True
            logger.info(f"Connected to {self.server_address}")
            return True
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            self._connected = False
            return False
    
    def disconnect(self) -> None:
        """Disconnect from server."""
        if self._channel:
            self._channel.close()
        self._connected = False
        self._enrolled = False
    
    def enroll(self) -> bool:
        """Enroll with server."""
        if not self._connected and not self.connect():
            return False
        
        try:
            msg = common_pb2.Message(
                message_type="enrollment",
                destination=common_pb2.Address(service_name="pyfleet"),
                source=common_pb2.Address(client_id=self.client_id.encode()),
            )
            msg.data.value = json.dumps(self._system_info()).encode()
            
            self._stub.Process(msg, timeout=30)
            self._enrolled = True
            logger.info(f"Enrolled as {self.client_id}")
            return True
        except Exception as e:
            logger.error(f"Enrollment failed: {e}")
            return False
    
    def send(self, message_type: str, data: bytes = b"") -> bool:
        """Send message to server."""
        if not self._connected:
            return False
        
        try:
            msg = common_pb2.Message(
                message_type=message_type,
                destination=common_pb2.Address(service_name="pyfleet"),
                source=common_pb2.Address(client_id=self.client_id.encode()),
            )
            msg.data.value = data
            
            self._stub.Process(msg, timeout=30)
            self._stats["sent"] += 1
            return True
        except Exception as e:
            logger.error(f"Send failed: {e}")
            self._stats["failed"] += 1
            self._connected = False
            return False
    
    def send_json(self, message_type: str, data: Dict[str, Any]) -> bool:
        """Send JSON data."""
        return self.send(message_type, json.dumps(data).encode())
    
    def _heartbeat(self) -> bool:
        try:
            msg = common_pb2.Message(
                message_type="heartbeat",
                source=common_pb2.Address(client_id=self.client_id.encode()),
            )
            self._stub.Process(msg, timeout=5)
            self._stats["heartbeats"] += 1
            return True
        except Exception:
            self._connected = False
            return False
    
    def _heartbeat_loop(self) -> None:
        reconnect_delay = 5
        while not self._stop.is_set():
            if not self._connected:
                if self.connect() and self.enroll():
                    reconnect_delay = 5
                else:
                    self._stop.wait(reconnect_delay)
                    reconnect_delay = min(reconnect_delay * 2, 60)
                    continue
            
            self._heartbeat()
            self._stop.wait(self.heartbeat_interval)
    
    def start(self) -> "FleetClient":
        """Start the client."""
        if self._running:
            raise RuntimeError("Already running")
        
        if not self.connect():
            raise ConnectionError("Cannot connect")
        
        if not self.enroll():
            raise ConnectionError("Cannot enroll")
        
        self._stop.clear()
        self._heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self._heartbeat_thread.start()
        
        self._running = True
        logger.info(f"Client started: {self.client_id}")
        return self
    
    def stop(self) -> None:
        """Stop the client."""
        self._stop.set()
        if self._heartbeat_thread:
            self._heartbeat_thread.join(timeout=5)
        self.disconnect()
        self._running = False
        logger.info("Client stopped")
    
    def wait(self, timeout: Optional[float] = None) -> None:
        """Wait for client to stop."""
        if self._heartbeat_thread:
            self._heartbeat_thread.join(timeout=timeout)
    
    def stats(self) -> Dict[str, Any]:
        """Get client stats."""
        return {
            "client_id": self.client_id,
            "connected": self._connected,
            "enrolled": self._enrolled,
            **self._stats,
        }
    
    @property
    def connected(self) -> bool:
        return self._connected
    
    @property
    def enrolled(self) -> bool:
        return self._enrolled
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, *args):
        self.stop()
