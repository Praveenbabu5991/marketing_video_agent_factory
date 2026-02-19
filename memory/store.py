"""
Persistent Memory Store for Marketing Video Agent Factory.
Uses SQLite for session persistence across restarts.
"""

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional
from contextlib import contextmanager

from memory.state import SessionState, WorkflowState, BrandContext, VideoContext, MarketingContext, UserUploadedImage


class DatabaseManager:
    """SQLite database manager with connection pooling."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema."""
        with self.get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    state_json TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS generated_content (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    content_type TEXT NOT NULL,
                    content_path TEXT,
                    metadata_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                );
                
                CREATE TABLE IF NOT EXISTS brand_profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    industry TEXT,
                    overview TEXT,
                    brand_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
                CREATE INDEX IF NOT EXISTS idx_sessions_updated ON sessions(updated_at);
                CREATE INDEX IF NOT EXISTS idx_content_session ON generated_content(session_id);
            """)
    
    @contextmanager
    def get_connection(self):
        """Get a database connection with proper cleanup."""
        conn = sqlite3.connect(self.db_path, detect_types=sqlite3.PARSE_DECLTYPES)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


class MemoryStore:
    """Persistent memory store for session and content management."""
    
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            from config.settings import DATABASE_PATH
            db_path = str(DATABASE_PATH)
        
        self.db = DatabaseManager(db_path)
        self._session_cache: dict[str, SessionState] = {}
    
    # =========================================================================
    # Session Management
    # =========================================================================
    
    def create_session(self, session_id: str, user_id: str) -> SessionState:
        """Create a new session."""
        state = SessionState(session_id=session_id, user_id=user_id)
        self._save_session(state)
        self._session_cache[session_id] = state
        return state
    
    def get_session(self, session_id: str) -> Optional[SessionState]:
        """Get a session by ID."""
        # Check cache first
        if session_id in self._session_cache:
            return self._session_cache[session_id]
        
        # Load from database
        with self.db.get_connection() as conn:
            row = conn.execute(
                "SELECT state_json FROM sessions WHERE session_id = ?",
                (session_id,)
            ).fetchone()
            
            if row:
                state = SessionState.from_dict(json.loads(row["state_json"]))
                self._session_cache[session_id] = state
                return state
        
        return None
    
    def get_or_create_session(self, session_id: str, user_id: str) -> SessionState:
        """Get existing session or create new one."""
        session = self.get_session(session_id)
        if session is None:
            session = self.create_session(session_id, user_id)
        return session
    
    def update_session(self, state: SessionState) -> None:
        """Update session state."""
        state.updated_at = datetime.now()
        self._save_session(state)
        self._session_cache[state.session_id] = state
    
    def _save_session(self, state: SessionState) -> None:
        """Save session to database."""
        with self.db.get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO sessions (session_id, user_id, state_json, updated_at)
                VALUES (?, ?, ?, ?)
            """, (
                state.session_id,
                state.user_id,
                json.dumps(state.to_dict()),
                datetime.now()
            ))
    
    def delete_session(self, session_id: str) -> None:
        """Delete a session."""
        with self.db.get_connection() as conn:
            conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
        self._session_cache.pop(session_id, None)
    
    def list_sessions(self, user_id: str) -> list[SessionState]:
        """List all sessions for a user."""
        with self.db.get_connection() as conn:
            rows = conn.execute(
                "SELECT state_json FROM sessions WHERE user_id = ? ORDER BY updated_at DESC",
                (user_id,)
            ).fetchall()
            
            return [SessionState.from_dict(json.loads(row["state_json"])) for row in rows]
    
    def cleanup_old_sessions(self, max_age_hours: int = 24) -> int:
        """Clean up sessions older than max_age_hours."""
        cutoff = datetime.now() - timedelta(hours=max_age_hours)
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM sessions WHERE updated_at < ?",
                (cutoff,)
            )
            deleted = cursor.rowcount
        
        # Clear cache entries
        for session_id in list(self._session_cache.keys()):
            if self._session_cache[session_id].updated_at < cutoff:
                del self._session_cache[session_id]
        
        return deleted
    
    # =========================================================================
    # Content Management
    # =========================================================================
    
    def save_generated_content(
        self,
        session_id: str,
        content_type: str,
        content_path: str,
        metadata: Optional[dict] = None
    ) -> int:
        """Save generated content reference."""
        with self.db.get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO generated_content (session_id, content_type, content_path, metadata_json)
                VALUES (?, ?, ?, ?)
            """, (
                session_id,
                content_type,
                content_path,
                json.dumps(metadata or {})
            ))
            return cursor.lastrowid
    
    def get_session_content(self, session_id: str, content_type: Optional[str] = None) -> list[dict]:
        """Get generated content for a session."""
        with self.db.get_connection() as conn:
            if content_type:
                rows = conn.execute("""
                    SELECT * FROM generated_content 
                    WHERE session_id = ? AND content_type = ?
                    ORDER BY created_at DESC
                """, (session_id, content_type)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT * FROM generated_content 
                    WHERE session_id = ?
                    ORDER BY created_at DESC
                """, (session_id,)).fetchall()
            
            return [dict(row) for row in rows]
    
    def get_recent_content(self, limit: int = 10) -> list[dict]:
        """Get recent generated content across all sessions."""
        with self.db.get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM generated_content 
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,)).fetchall()
            
            return [dict(row) for row in rows]
    
    # =========================================================================
    # Brand Profiles
    # =========================================================================
    
    def save_brand_profile(self, brand: BrandContext) -> int:
        """Save a brand profile for reuse."""
        with self.db.get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO brand_profiles (name, industry, overview, brand_json)
                VALUES (?, ?, ?, ?)
            """, (
                brand.name,
                brand.industry,
                brand.overview,
                json.dumps(brand.to_dict())
            ))
            return cursor.lastrowid
    
    def get_brand_profile(self, name: str) -> Optional[BrandContext]:
        """Get a brand profile by name."""
        with self.db.get_connection() as conn:
            row = conn.execute(
                "SELECT brand_json FROM brand_profiles WHERE name = ?",
                (name,)
            ).fetchone()
            
            if row:
                return BrandContext.from_dict(json.loads(row["brand_json"]))
        return None
    
    def list_brand_profiles(self) -> list[BrandContext]:
        """List all saved brand profiles."""
        with self.db.get_connection() as conn:
            rows = conn.execute(
                "SELECT brand_json FROM brand_profiles ORDER BY updated_at DESC"
            ).fetchall()
            
            return [BrandContext.from_dict(json.loads(row["brand_json"])) for row in rows]


# =============================================================================
# Global Instance and Tool Functions
# =============================================================================

_memory_store: Optional[MemoryStore] = None


def get_memory_store() -> MemoryStore:
    """Get the global memory store instance."""
    global _memory_store
    if _memory_store is None:
        _memory_store = MemoryStore()
    return _memory_store


# Tool functions for agents (simplified interface)

def save_to_memory(category: str, key: str, value: str) -> dict:
    """
    Save data to memory for later recall.
    
    Args:
        category: Type of data (context, content, brand, marketing)
        key: Identifier for the data
        value: JSON string or simple text value
    """
    store = get_memory_store()
    
    try:
        data = json.loads(value) if value.startswith("{") or value.startswith("[") else {"value": value}
    except json.JSONDecodeError:
        data = {"value": value}
    
    if category == "brand":
        brand = BrandContext(**data) if isinstance(data, dict) and "name" in data else BrandContext(name=key)
        store.save_brand_profile(brand)
        return {"status": "success", "message": f"Brand '{key}' saved"}
    
    elif category == "content":
        content_id = store.save_generated_content(
            session_id=key,
            content_type=data.get("type", "unknown"),
            content_path=data.get("path", ""),
            metadata=data
        )
        return {"status": "success", "content_id": content_id}
    
    return {"status": "success", "key": key}


def recall_from_memory(category: str, key: str = None) -> dict:
    """
    Recall data from memory.
    
    Args:
        category: Type of data to recall (brand, content, recent, marketing)
        key: Specific identifier (optional)
    """
    store = get_memory_store()
    
    if category == "brand":
        if key:
            brand = store.get_brand_profile(key)
            return {"status": "success", "data": brand.to_dict() if brand else None}
        brands = store.list_brand_profiles()
        return {"status": "success", "data": [b.to_dict() for b in brands]}
    
    elif category == "content":
        if key:
            content = store.get_session_content(key)
            return {"status": "success", "data": content}
        content = store.get_recent_content(10)
        return {"status": "success", "data": content}
    
    elif category == "recent":
        limit = int(key) if key and key.isdigit() else 10
        content = store.get_recent_content(limit)
        return {"status": "success", "data": content}
    
    return {"status": "error", "message": f"Unknown category: {category}"}


def get_brand_context(session_id: str = "") -> dict:
    """
    Retrieve structured brand context for video generation.

    Call this BEFORE generating any video to get brand colors, logo, tone,
    target audience, and other marketing data that should be baked into the video.

    Args:
        session_id: The current session ID. If empty, uses the most recent session.

    Returns:
        dict with keys: name, colors, logo_path, tone, industry, target_audience,
        company_overview, products_services, brand_messaging, marketing_goals,
        user_images (list of {path, usage_intent}), reference_images.
        Returns {"status": "no_brand_context"} if nothing is found.
    """
    store = get_memory_store()

    session = None
    if session_id:
        session = store.get_session(session_id)

    # Fallback: try to find most recent session with brand data
    if session is None:
        with store.db.get_connection() as conn:
            row = conn.execute(
                "SELECT state_json FROM sessions ORDER BY updated_at DESC LIMIT 1"
            ).fetchone()
            if row:
                session = SessionState.from_dict(json.loads(row["state_json"]))

    if session is None or not session.brand.name:
        return {"status": "no_brand_context"}

    brand = session.brand
    mc = brand.marketing_context

    user_imgs = []
    for img in brand.user_images:
        if isinstance(img, UserUploadedImage):
            user_imgs.append({"path": img.path, "usage_intent": img.usage_intent})
        elif isinstance(img, dict):
            user_imgs.append({"path": img.get("path", ""), "usage_intent": img.get("usage_intent", "auto")})

    return {
        "status": "success",
        "name": brand.name,
        "colors": brand.colors,
        "logo_path": brand.logo_path or "",
        "tone": brand.tone,
        "industry": brand.industry,
        "overview": brand.overview,
        "target_audience": mc.target_audience,
        "company_overview": mc.company_overview,
        "products_services": mc.products_services,
        "brand_messaging": mc.brand_messaging,
        "marketing_goals": mc.marketing_goals,
        "user_images": user_imgs,
        "reference_images": brand.reference_images,
    }


def get_or_create_project(
    project_name: str,
    brand_name: str = "",
    niche: str = "",
    tone: str = "professional"
) -> dict:
    """Get existing brand/project or create new one."""
    store = get_memory_store()
    
    # Check if brand exists
    brand = store.get_brand_profile(project_name)
    if brand:
        return {"status": "success", "project": brand.to_dict(), "is_new": False}
    
    # Create new brand
    new_brand = BrandContext(
        name=brand_name or project_name,
        industry=niche,
        tone=tone
    )
    store.save_brand_profile(new_brand)
    
    return {"status": "success", "project": new_brand.to_dict(), "is_new": True}
