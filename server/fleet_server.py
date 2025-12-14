"""
FleetServer - Multi-client management server.
"""

import json
import logging
import threading
import hashlib
from concurrent import futures
from datetime import datetime
from typing import Callable, Dict, List, Optional

import grpc

from pyfleet.common import ClientInfo, ClientStatus, Command
from pyfleet.server.registry import ClientRegistry

# Import from fleetspeak package (protobuf definitions)
from fleetspeak.src.common.proto.fleetspeak import common_pb2
from fleetspeak.src.server.grpcservice.proto.fleetspeak_grpcservice import grpcservice_pb2_grpc

logger = logging.getLogger(__name__)


class _Servicer(grpcservice_pb2_grpc.ProcessorServicer):
    """Internal gRPC servicer."""
    
    def __init__(self, server: "FleetServer"):
        super().__init__()
        self._server = server
    
    def Process(self, request: common_pb2.Message, context: grpc.ServicerContext):
        try:
            # Get client ID
            client_id = request.source.client_id.hex() if request.source.client_id else None
            if not client_id:
                peer = context.peer()
                client_id = hashlib.sha256(peer.encode()).hexdigest()[:16] if peer else "unknown"
            
            # Handle message types
            if request.message_type == "enrollment":
                self._handle_enrollment(client_id, request, context)
            elif request.message_type == "heartbeat":
                self._server.clients.heartbeat(client_id)
            else:
                self._server.clients.heartbeat(client_id)
                client = self._server.clients.get(client_id)
                if client:
                    client.message_count += 1
                self._server._dispatch(request, context, client)
        
        except Exception as e:
            logger.exception(f"Error: {e}")
        
        return common_pb2.EmptyMessage()
    
    def _handle_enrollment(self, client_id: str, request, context):
        try:
            data = json.loads(request.data.value.decode()) if request.data.value else {}
            # Prefer client-reported IP, fallback to peer IP
            peer = context.peer() or ""
            peer_ip = peer.split(":")[-2] if ":" in peer else ""
            ip = data.get("ip_address") or peer_ip
            
            self._server.clients.register(
                client_id=client_id,
                hostname=data.get("hostname", ""),
                os_type=data.get("os_type", ""),
                os_version=data.get("os_version", ""),
                agent_version=data.get("agent_version", ""),
                ip_address=ip,
            )
            logger.info(f"Enrolled: {client_id}")
        except Exception as e:
            logger.exception(f"Enrollment error: {e}")


class FleetServer:
    """
    Multi-client fleet management server.
    
    Example:
        server = FleetServer(listen_address="0.0.0.0:9999")
        
        @server.on_enroll
        def enrolled(client):
            print(f"New: {client.hostname}")
        
        @server.on_message
        def message(msg, ctx, client):
            print(f"From {client.hostname}: {msg.message_type}")
        
        server.start()
    """
    
    def __init__(
        self,
        listen_address: str = "0.0.0.0:9999",
        service_name: str = "pyfleet",
        workers: int = 10,
        heartbeat_timeout: float = 60.0,
        offline_timeout: float = 300.0,
    ):
        self.listen_address = listen_address
        self.service_name = service_name
        self._workers = workers
        
        self.clients = ClientRegistry(
            heartbeat_timeout=heartbeat_timeout,
            offline_timeout=offline_timeout,
        )
        
        self._handlers: List[Callable] = []
        self._grpc_server: Optional[grpc.Server] = None
        self._running = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
    
    def on_enroll(self, handler: Callable) -> Callable:
        """Decorator for enrollment events."""
        self.clients.on_enroll(handler)
        return handler
    
    def on_status_change(self, handler: Callable) -> Callable:
        """Decorator for status changes."""
        self.clients.on_status_change(handler)
        return handler
    
    def on_message(self, handler: Callable) -> Callable:
        """Decorator for message events."""
        self._handlers.append(handler)
        return handler
    
    def _dispatch(self, message, context, client):
        for h in self._handlers:
            try:
                h(message, context, client)
            except Exception as e:
                logger.exception(f"Handler error: {e}")
    
    def start(self) -> "FleetServer":
        """Start the server."""
        if self._running:
            raise RuntimeError("Already running")
        
        self._grpc_server = grpc.server(
            futures.ThreadPoolExecutor(max_workers=self._workers)
        )
        grpcservice_pb2_grpc.add_ProcessorServicer_to_server(
            _Servicer(self), self._grpc_server
        )
        self._grpc_server.add_insecure_port(self.listen_address)
        self._grpc_server.start()
        
        self._stop.clear()
        self._monitor_thread = threading.Thread(target=self._monitor, daemon=True)
        self._monitor_thread.start()
        
        self._running = True
        logger.info(f"Server started on {self.listen_address}")
        return self
    
    def stop(self) -> None:
        """Stop the server."""
        self._stop.set()
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        if self._grpc_server:
            self._grpc_server.stop(grace=5)
        self._running = False
        logger.info("Server stopped")
    
    def _monitor(self) -> None:
        while not self._stop.wait(timeout=30):
            try:
                self.clients.check_timeouts()
            except Exception:
                pass
    
    def send_command(self, client_id: str, command_type: str, payload: bytes = b"") -> str:
        """Send command to client (queued)."""
        cmd = Command(
            command_id="",
            command_type=command_type,
            payload=payload,
            target_id=client_id,
        )
        logger.debug(f"Command {cmd.command_id} queued for {client_id}")
        return cmd.command_id
    
    def broadcast(self, command_type: str, payload: bytes = b"", tags: Optional[List[str]] = None) -> Dict[str, str]:
        """Broadcast command to clients."""
        results = {}
        
        if tags:
            clients = []
            for tag in tags:
                clients.extend(self.clients.get_by_tag(tag))
            clients = list({c.client_id: c for c in clients}.values())
        else:
            clients = self.clients.get_by_status(ClientStatus.ONLINE)
        
        for client in clients:
            cmd_id = self.send_command(client.client_id, command_type, payload)
            results[client.client_id] = cmd_id
        
        return results
    
    @property
    def running(self) -> bool:
        return self._running
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, *args):
        self.stop()
