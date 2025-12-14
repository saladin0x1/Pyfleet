"""
PyFleet Database - Simple SQLite persistence for enrollment tokens.
"""

import sqlite3
import secrets
import string
import threading
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from contextlib import contextmanager


class Database:
    """SQLite database for enrollment tokens."""
    
    def __init__(self, db_path: str = "pyfleet.db"):
        self.db_path = db_path
        self._local = threading.local()
        self._init_db()
    
    def _get_conn(self) -> sqlite3.Connection:
        """Get thread-local database connection."""
        if not hasattr(self._local, 'conn'):
            self._local.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn
    
    @contextmanager
    def _cursor(self):
        """Context manager for database cursor."""
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
    
    def _init_db(self):
        """Initialize database schema."""
        with self._cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS enrollment_tokens (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    token TEXT UNIQUE NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT,
                    max_uses INTEGER DEFAULT -1,
                    use_count INTEGER DEFAULT 0,
                    active INTEGER DEFAULT 1
                )
            """)
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS broadcasts (
                    id TEXT PRIMARY KEY,
                    message_type TEXT NOT NULL,
                    data TEXT,
                    required_labels TEXT,
                    source_service TEXT DEFAULT 'pyfleet',
                    created_at TEXT NOT NULL,
                    expires_at TEXT,
                    active INTEGER DEFAULT 1
                )
            """)
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS clients (
                    client_id TEXT PRIMARY KEY,
                    hostname TEXT,
                    os_type TEXT,
                    os_version TEXT,
                    agent_version TEXT,
                    ip_address TEXT,
                    tags TEXT,
                    status TEXT DEFAULT 'enrolling',
                    enrolled_at TEXT,
                    last_seen TEXT,
                    last_heartbeat TEXT,
                    message_count INTEGER DEFAULT 0,
                    error_count INTEGER DEFAULT 0
                )
            """)
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT NOT NULL,
                    client_id TEXT,
                    hostname TEXT,
                    message TEXT,
                    data TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT
                )
            """)
    
    def _generate_token(self, length: int = 32) -> str:
        """Generate secure random token."""
        chars = string.ascii_letters + string.digits
        return ''.join(secrets.choice(chars) for _ in range(length))
    
    def create_token(self, name: str, expires_hours: int = None, max_uses: int = -1) -> Dict[str, Any]:
        """Create enrollment token."""
        token_id = secrets.token_hex(8)
        token = self._generate_token()
        now = datetime.now()
        expires_at = (now + timedelta(hours=expires_hours)).isoformat() if expires_hours else None
        
        with self._cursor() as cur:
            cur.execute("""
                INSERT INTO enrollment_tokens (id, name, token, created_at, expires_at, max_uses)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (token_id, name, token, now.isoformat(), expires_at, max_uses))
        
        return {
            'id': token_id,
            'name': name,
            'token': token,
            'created_at': now.isoformat(),
            'expires_at': expires_at,
            'max_uses': max_uses,
            'use_count': 0,
            'active': 1
        }
    
    def get_tokens(self) -> List[Dict[str, Any]]:
        """Get all tokens."""
        with self._cursor() as cur:
            cur.execute("SELECT * FROM enrollment_tokens ORDER BY created_at DESC")
            return [dict(row) for row in cur.fetchall()]
    
    def get_token(self, token_id: str) -> Optional[Dict[str, Any]]:
        """Get token by ID."""
        with self._cursor() as cur:
            cur.execute("SELECT * FROM enrollment_tokens WHERE id = ?", (token_id,))
            row = cur.fetchone()
            return dict(row) if row else None
    
    def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate token for enrollment. Returns token data if valid."""
        with self._cursor() as cur:
            cur.execute("SELECT * FROM enrollment_tokens WHERE token = ? AND active = 1", (token,))
            row = cur.fetchone()
            if not row:
                return None
            
            data = dict(row)
            
            # Check expiry
            if data['expires_at']:
                if datetime.now() > datetime.fromisoformat(data['expires_at']):
                    return None
            
            # Check max uses
            if data['max_uses'] != -1 and data['use_count'] >= data['max_uses']:
                return None
            
            # Increment use count
            cur.execute("UPDATE enrollment_tokens SET use_count = use_count + 1 WHERE id = ?", (data['id'],))
            return data
    
    def revoke_token(self, token_id: str) -> bool:
        """Revoke token."""
        with self._cursor() as cur:
            cur.execute("UPDATE enrollment_tokens SET active = 0 WHERE id = ?", (token_id,))
            return cur.rowcount > 0
    
    def delete_token(self, token_id: str) -> bool:
        """Delete token."""
        with self._cursor() as cur:
            cur.execute("DELETE FROM enrollment_tokens WHERE id = ?", (token_id,))
            return cur.rowcount > 0
    
    # ========================
    # Broadcast Methods
    # ========================
    
    def create_broadcast(
        self,
        message_type: str,
        data: str = "",
        required_labels: List[str] = None,
        source_service: str = "pyfleet",
        expires_hours: int = None,
    ) -> Dict[str, Any]:
        """Create a broadcast."""
        import json
        
        broadcast_id = secrets.token_hex(16)
        now = datetime.now()
        expires_at = (now + timedelta(hours=expires_hours)).isoformat() if expires_hours else None
        labels_json = json.dumps(required_labels or [])
        
        with self._cursor() as cur:
            cur.execute("""
                INSERT INTO broadcasts (id, message_type, data, required_labels, source_service, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (broadcast_id, message_type, data, labels_json, source_service, now.isoformat(), expires_at))
        
        return {
            'id': broadcast_id,
            'message_type': message_type,
            'data': data,
            'required_labels': required_labels or [],
            'source_service': source_service,
            'created_at': now.isoformat(),
            'expires_at': expires_at,
            'active': 1
        }
    
    def get_broadcasts(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """Get all broadcasts."""
        import json
        
        with self._cursor() as cur:
            if active_only:
                cur.execute("SELECT * FROM broadcasts WHERE active = 1 ORDER BY created_at DESC")
            else:
                cur.execute("SELECT * FROM broadcasts ORDER BY created_at DESC")
            
            results = []
            for row in cur.fetchall():
                data = dict(row)
                # Parse labels JSON
                data['required_labels'] = json.loads(data['required_labels']) if data['required_labels'] else []
                
                # Check expiry
                if active_only and data['expires_at']:
                    if datetime.now() > datetime.fromisoformat(data['expires_at']):
                        continue
                
                results.append(data)
            return results
    
    def get_broadcast(self, broadcast_id: str) -> Optional[Dict[str, Any]]:
        """Get broadcast by ID."""
        import json
        
        with self._cursor() as cur:
            cur.execute("SELECT * FROM broadcasts WHERE id = ?", (broadcast_id,))
            row = cur.fetchone()
            if not row:
                return None
            data = dict(row)
            data['required_labels'] = json.loads(data['required_labels']) if data['required_labels'] else []
            return data
    
    def delete_broadcast(self, broadcast_id: str) -> bool:
        """Delete broadcast."""
        with self._cursor() as cur:
            cur.execute("DELETE FROM broadcasts WHERE id = ?", (broadcast_id,))
            return cur.rowcount > 0
    
    def deactivate_broadcast(self, broadcast_id: str) -> bool:
        """Deactivate broadcast (soft delete)."""
        with self._cursor() as cur:
            cur.execute("UPDATE broadcasts SET active = 0 WHERE id = ?", (broadcast_id,))
            return cur.rowcount > 0
    
    # ========================
    # Client Methods
    # ========================
    
    def upsert_client(
        self,
        client_id: str,
        hostname: str = "",
        os_type: str = "",
        os_version: str = "",
        agent_version: str = "",
        ip_address: str = "",
        tags: List[str] = None,
        status: str = "online",
    ) -> Dict[str, Any]:
        """Insert or update client."""
        import json
        
        now = datetime.now().isoformat()
        tags_json = json.dumps(tags or [])
        
        with self._cursor() as cur:
            # Check if exists
            cur.execute("SELECT * FROM clients WHERE client_id = ?", (client_id,))
            existing = cur.fetchone()
            
            if existing:
                cur.execute("""
                    UPDATE clients SET
                        hostname = ?, os_type = ?, os_version = ?, agent_version = ?,
                        ip_address = ?, tags = ?, status = ?, last_seen = ?
                    WHERE client_id = ?
                """, (hostname, os_type, os_version, agent_version, ip_address, tags_json, status, now, client_id))
            else:
                cur.execute("""
                    INSERT INTO clients (client_id, hostname, os_type, os_version, agent_version, ip_address, tags, status, enrolled_at, last_seen)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (client_id, hostname, os_type, os_version, agent_version, ip_address, tags_json, status, now, now))
        
        return {
            'client_id': client_id,
            'hostname': hostname,
            'os_type': os_type,
            'os_version': os_version,
            'agent_version': agent_version,
            'ip_address': ip_address,
            'tags': tags or [],
            'status': status,
            'last_seen': now
        }
    
    def get_clients(self, status: str = None) -> List[Dict[str, Any]]:
        """Get all clients, optionally filtered by status."""
        import json
        
        with self._cursor() as cur:
            if status:
                cur.execute("SELECT * FROM clients WHERE status = ? ORDER BY last_seen DESC", (status,))
            else:
                cur.execute("SELECT * FROM clients ORDER BY last_seen DESC")
            
            results = []
            for row in cur.fetchall():
                data = dict(row)
                data['tags'] = json.loads(data['tags']) if data['tags'] else []
                results.append(data)
            return results
    
    def get_client(self, client_id: str) -> Optional[Dict[str, Any]]:
        """Get client by ID."""
        import json
        
        with self._cursor() as cur:
            cur.execute("SELECT * FROM clients WHERE client_id = ?", (client_id,))
            row = cur.fetchone()
            if not row:
                return None
            data = dict(row)
            data['tags'] = json.loads(data['tags']) if data['tags'] else []
            return data
    
    def update_client_heartbeat(self, client_id: str) -> bool:
        """Update client heartbeat timestamp."""
        now = datetime.now().isoformat()
        with self._cursor() as cur:
            cur.execute("UPDATE clients SET last_heartbeat = ?, last_seen = ?, status = 'online' WHERE client_id = ?", 
                       (now, now, client_id))
            return cur.rowcount > 0
    
    def update_client_status(self, client_id: str, status: str) -> bool:
        """Update client status."""
        with self._cursor() as cur:
            cur.execute("UPDATE clients SET status = ? WHERE client_id = ?", (status, client_id))
            return cur.rowcount > 0
    
    def increment_client_messages(self, client_id: str) -> bool:
        """Increment client message count."""
        with self._cursor() as cur:
            cur.execute("UPDATE clients SET message_count = message_count + 1, last_seen = ? WHERE client_id = ?",
                       (datetime.now().isoformat(), client_id))
            return cur.rowcount > 0
    
    def delete_client(self, client_id: str) -> bool:
        """Delete client."""
        with self._cursor() as cur:
            cur.execute("DELETE FROM clients WHERE client_id = ?", (client_id,))
            return cur.rowcount > 0
    
    # ========================
    # Event Methods
    # ========================
    
    def add_event(
        self,
        event_type: str,
        message: str,
        client_id: str = None,
        hostname: str = None,
        data: str = None,
    ) -> Dict[str, Any]:
        """Add event to log."""
        now = datetime.now().isoformat()
        
        with self._cursor() as cur:
            cur.execute("""
                INSERT INTO events (type, client_id, hostname, message, data, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (event_type, client_id, hostname, message, data, now))
            event_id = cur.lastrowid
        
        return {
            'id': event_id,
            'type': event_type,
            'client_id': client_id,
            'hostname': hostname,
            'message': message,
            'data': data,
            'created_at': now
        }
    
    def get_events(self, limit: int = 50, event_type: str = None) -> List[Dict[str, Any]]:
        """Get recent events."""
        with self._cursor() as cur:
            if event_type:
                cur.execute("SELECT * FROM events WHERE type = ? ORDER BY created_at DESC LIMIT ?", (event_type, limit))
            else:
                cur.execute("SELECT * FROM events ORDER BY created_at DESC LIMIT ?", (limit,))
            return [dict(row) for row in cur.fetchall()]
    
    def clear_events(self) -> int:
        """Clear all events."""
        with self._cursor() as cur:
            cur.execute("DELETE FROM events")
            return cur.rowcount
    
    def get_client_stats(self) -> Dict[str, int]:
        """Get client statistics by status."""
        with self._cursor() as cur:
            cur.execute("SELECT status, COUNT(*) as count FROM clients GROUP BY status")
            stats = {row['status']: row['count'] for row in cur.fetchall()}
            stats['total'] = sum(stats.values())
            return stats
    
    # ========================
    # Settings Methods
    # ========================
    
    def get_setting(self, key: str, default: str = None) -> Optional[str]:
        """Get a setting value."""
        with self._cursor() as cur:
            cur.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = cur.fetchone()
            return row['value'] if row else default
    
    def set_setting(self, key: str, value: str) -> None:
        """Set a setting value."""
        now = datetime.now().isoformat()
        with self._cursor() as cur:
            cur.execute("""
                INSERT OR REPLACE INTO settings (key, value, updated_at)
                VALUES (?, ?, ?)
            """, (key, value, now))
    
    def get_all_settings(self) -> Dict[str, str]:
        """Get all settings."""
        with self._cursor() as cur:
            cur.execute("SELECT key, value FROM settings")
            return {row['key']: row['value'] for row in cur.fetchall()}
