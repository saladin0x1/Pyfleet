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

from .database import Database

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
        self.db = Database()
        
        # Load persisted settings
        self._load_settings()
        
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
    
    def _load_settings(self):
        """Load persisted settings from database."""
        hb = self.db.get_setting("heartbeat_timeout")
        if hb:
            self.fleet_server.clients._heartbeat_timeout = float(hb)
        off = self.db.get_setting("offline_timeout")
        if off:
            self.fleet_server.clients._offline_timeout = float(off)
    
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
        
        @self.app.route("/api/agents/<client_id>/tags", methods=["POST"])
        def add_tag(client_id):
            data = request.get_json()
            tag = data.get("tag")
            if tag:
                self.fleet_server.clients.add_tag(client_id, tag)
                return jsonify({"success": True})
            return jsonify({"error": "No tag provided"}), 400
        
        # Token API
        @self.app.route("/api/tokens")
        def get_tokens():
            tokens = self.db.get_tokens()
            for t in tokens:
                t['token_preview'] = t['token'][:8] + '...'
                del t['token']
            return jsonify(tokens)
        
        @self.app.route("/api/tokens", methods=["POST"])
        def create_token():
            data = request.get_json() or {}
            token = self.db.create_token(
                name=data.get("name", "Enrollment Token"),
                expires_hours=data.get("expires_hours"),
                max_uses=data.get("max_uses", -1)
            )
            return jsonify(token), 201
        
        @self.app.route("/api/tokens/<token_id>")
        def get_token(token_id):
            token = self.db.get_token(token_id)
            if token:
                return jsonify(token)
            return jsonify({"error": "Not found"}), 404
        
        @self.app.route("/api/tokens/<token_id>/revoke", methods=["POST"])
        def revoke_token(token_id):
            return jsonify({"success": self.db.revoke_token(token_id)})
        
        @self.app.route("/api/tokens/validate", methods=["POST"])
        def validate_token():
            data = request.get_json() or {}
            token = data.get("token")
            result = self.db.validate_token(token)
            if result:
                return jsonify({"valid": True, "token_id": result['id']})
            return jsonify({"valid": False}), 401
        
        # Broadcast API
        @self.app.route("/api/broadcasts")
        def get_broadcasts():
            broadcasts = self.db.get_broadcasts(active_only=True)
            return jsonify(broadcasts)
        
        @self.app.route("/api/broadcasts", methods=["POST"])
        def create_broadcast():
            data = request.get_json() or {}
            message_type = data.get("message_type", "broadcast")
            payload = data.get("data", "")
            labels = data.get("required_labels", [])
            
            broadcast = self.db.create_broadcast(
                message_type=message_type,
                data=payload,
                required_labels=labels,
            )
            
            # Add to activity feed
            self.db.add_event(
                event_type="broadcast",
                message=f"Broadcast created: {message_type}",
            )
            self._emit_event({"type": "broadcast", "message": f"Broadcast created: {message_type}"})
            
            return jsonify(broadcast), 201
        
        @self.app.route("/api/broadcasts/<broadcast_id>", methods=["DELETE"])
        def delete_broadcast(broadcast_id):
            success = self.db.delete_broadcast(broadcast_id)
            return jsonify({"success": success})
        
        # Endpoint for clients to fetch pending broadcasts
        @self.app.route("/api/broadcasts/pending/<client_id>")
        def get_pending_broadcasts(client_id):
            """Get broadcasts matching a client's tags."""
            # Get client tags from database or registry
            client = self.db.get_client(client_id)
            if not client:
                # Try in-memory registry
                registry_client = self.fleet_server.clients.get(client_id)
                if registry_client:
                    client_tags = list(registry_client.tags)
                else:
                    client_tags = []
            else:
                client_tags = client.get('tags', [])
            
            # Get all broadcasts and filter by labels
            all_broadcasts = self.db.get_broadcasts(active_only=True)
            matching = []
            for b in all_broadcasts:
                required = b.get('required_labels', [])
                if not required:
                    # No label requirements = matches all
                    matching.append(b)
                else:
                    # Check if client has any required label
                    if any(label in client_tags for label in required):
                        matching.append(b)
            
            return jsonify(matching)
        
        # Events API
        @self.app.route("/api/events")
        def get_events():
            events = self.db.get_events(limit=50)
            return jsonify(events)
        
        # Settings API
        @self.app.route("/api/settings")
        def get_settings():
            """Get current server settings."""
            return jsonify({
                "heartbeat_timeout": self.fleet_server.clients._heartbeat_timeout,
                "offline_timeout": self.fleet_server.clients._offline_timeout,
                "service_name": self.fleet_server.service_name,
                "listen_address": self.fleet_server.listen_address,
            })
        
        @self.app.route("/api/settings", methods=["POST"])
        def update_settings():
            """Update server timeout settings."""
            data = request.get_json() or {}
            
            if "heartbeat_timeout" in data:
                val = float(data["heartbeat_timeout"])
                if 5 <= val <= 300:
                    self.fleet_server.clients._heartbeat_timeout = val
                    self.db.set_setting("heartbeat_timeout", str(val))
            
            if "offline_timeout" in data:
                val = float(data["offline_timeout"])
                if 10 <= val <= 600:
                    self.fleet_server.clients._offline_timeout = val
                    self.db.set_setting("offline_timeout", str(val))
            
            # Log the change
            self.db.add_event(
                event_type="settings",
                message=f"Settings updated: heartbeat={self.fleet_server.clients._heartbeat_timeout}s, offline={self.fleet_server.clients._offline_timeout}s",
            )
            
            return jsonify({
                "success": True,
                "heartbeat_timeout": self.fleet_server.clients._heartbeat_timeout,
                "offline_timeout": self.fleet_server.clients._offline_timeout,
            })
    
    def _setup_hooks(self):
        """Hook into FleetServer events."""
        
        @self.fleet_server.on_enroll
        def on_enroll(client):
            # Persist to database
            self.db.add_event(
                event_type="enrollment",
                message=f"New agent enrolled: {client.hostname}",
                client_id=client.client_id,
                hostname=client.hostname,
            )
            # Also persist client to database
            self.db.upsert_client(
                client_id=client.client_id,
                hostname=client.hostname,
                os_type=client.os_type,
                os_version=client.os_version,
                agent_version=client.agent_version,
                ip_address=client.ip_address,
                tags=list(client.tags),
                status="online",
            )
            self._emit_event({"type": "enrollment", "message": f"New agent enrolled: {client.hostname}"})
        
        @self.fleet_server.on_status_change
        def on_status_change(client, old_status, new_status):
            self.db.add_event(
                event_type="status_change",
                message=f"{client.hostname}: {old_status.value} → {new_status.value}",
                client_id=client.client_id,
                hostname=client.hostname,
            )
            self.db.update_client_status(client.client_id, new_status.value)
            self._emit_event({"type": "status_change", "message": f"{client.hostname}: {old_status.value} → {new_status.value}"})
        
        @self.fleet_server.on_message
        def on_message(msg, ctx, client):
            if client:
                self.db.update_client_heartbeat(client.client_id)
            
            if msg.message_type not in ("heartbeat", "enrollment"):
                if client:
                    self.db.increment_client_messages(client.client_id)
                self.db.add_event(
                    event_type="message",
                    message=f"Message from {client.hostname if client else '?'}: {msg.message_type}",
                    client_id=client.client_id if client else None,
                    hostname=client.hostname if client else "unknown",
                )
                self._emit_event({"type": "message", "message": f"Message from {client.hostname if client else '?'}: {msg.message_type}"})
    
    def _emit_event(self, event: Dict[str, Any]):
        """Emit event via WebSocket for real-time updates."""
        event["timestamp"] = datetime.now().isoformat()
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
