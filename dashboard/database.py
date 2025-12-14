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
