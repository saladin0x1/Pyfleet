"""
Dashboard Server - Flask web server with REST API and WebSocket support.
"""

import json
import logging
import os
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional

from flask import Flask, jsonify, send_from_directory, request
from flask_socketio import SocketIO

logger = logging.getLogger(__name__)


class DashboardServer:
    """
    Web dashboard server for PyFleet.
    
    Provides REST API and WebSocket for real-time updates.
    """
    
    def __init__(
        self,
        fleet_server,
        host: str = "0.0.0.0",
        port: int = 5000,
    ):
        self.fleet_server = fleet_server
        self.host = host
        self.port = port
        
        # Event history for activity feed
        self._events: List[Dict[str, Any]] = []
        self._max_events = 100
        
        # Flask app
        static_dir = os.path.join(os.path.dirname(__file__), "static")
        self.app = Flask(__name__, static_folder=static_dir)
        self.app.config["SECRET_KEY"] = os.urandom(24).hex()
        
        # Socket.IO for real-time updates
        self.socketio = SocketIO(self.app, cors_allowed_origins="*", async_mode="threading")
        
        self._setup_routes()
        self._setup_hooks()
        
        self._thread: Optional[threading.Thread] = None
        self._running = False
    
    def _setup_routes(self):
        """Setup REST API routes."""
        
        @self.app.route("/")
        def index():
            return send_from_directory(self.app.static_folder, "index.html")
        
        @self.app.route("/api/agents")
        def get_agents():
            agents = []
            for client in self.fleet_server.clients.get_all():
                agents.append(client.to_dict())
            return jsonify(agents)
        
        @self.app.route("/api/agents/<client_id>")
        def get_agent(client_id):
            client = self.fleet_server.clients.get(client_id)
            if client:
                return jsonify(client.to_dict())
            return jsonify({"error": "Not found"}), 404
        
        @self.app.route("/api/stats")
        def get_stats():
            stats = self.fleet_server.clients.stats()
            stats["server_running"] = self.fleet_server.running
            stats["listen_address"] = self.fleet_server.listen_address
            return jsonify(stats)
        
        @self.app.route("/api/events")
        def get_events():
            return jsonify(self._events[-50:])
        
        @self.app.route("/api/agents/<client_id>/tags", methods=["POST"])
        def add_tag(client_id):
            data = request.get_json()
            tag = data.get("tag")
            if tag:
                self.fleet_server.clients.add_tag(client_id, tag)
                return jsonify({"success": True})
            return jsonify({"error": "No tag provided"}), 400
    
    def _setup_hooks(self):
        """Hook into FleetServer events."""
        
        @self.fleet_server.on_enroll
        def on_enroll(client):
            event = {
                "type": "enrollment",
                "client_id": client.client_id,
                "hostname": client.hostname,
                "timestamp": datetime.now().isoformat(),
                "message": f"New agent enrolled: {client.hostname}",
            }
            self._add_event(event)
        
        @self.fleet_server.on_status_change
        def on_status_change(client, old_status, new_status):
            event = {
                "type": "status_change",
                "client_id": client.client_id,
                "hostname": client.hostname,
                "old_status": old_status.value,
                "new_status": new_status.value,
                "timestamp": datetime.now().isoformat(),
                "message": f"{client.hostname}: {old_status.value} → {new_status.value}",
            }
            self._add_event(event)
        
        @self.fleet_server.on_message
        def on_message(msg, ctx, client):
            if msg.message_type not in ("heartbeat", "enrollment"):
                event = {
                    "type": "message",
                    "client_id": client.client_id if client else None,
                    "hostname": client.hostname if client else "unknown",
                    "message_type": msg.message_type,
                    "timestamp": datetime.now().isoformat(),
                    "message": f"Message from {client.hostname if client else '?'}: {msg.message_type}",
                }
                self._add_event(event)
    
    def _add_event(self, event: Dict[str, Any]):
        """Add event and broadcast via WebSocket."""
        self._events.append(event)
        if len(self._events) > self._max_events:
            self._events = self._events[-self._max_events:]
        
        # Broadcast to all connected clients
        try:
            self.socketio.emit("event", event)
            self.socketio.emit("agents_update", {
                "agents": [c.to_dict() for c in self.fleet_server.clients.get_all()],
                "stats": self.fleet_server.clients.stats(),
            })
        except Exception as e:
            logger.debug(f"WebSocket emit error: {e}")
    
    def start(self) -> "DashboardServer":
        """Start the dashboard server in a background thread."""
        if self._running:
            return self
        
        def run():
            self.socketio.run(
                self.app,
                host=self.host,
                port=self.port,
                debug=False,
                use_reloader=False,
                log_output=False,
            )
        
        self._thread = threading.Thread(target=run, daemon=True)
        self._thread.start()
        self._running = True
        logger.info(f"Dashboard started on http://{self.host}:{self.port}")
        return self
    
    def stop(self):
        """Stop the dashboard server."""
        self._running = False
        logger.info("Dashboard stopped")
