"""
KinetiQ MongoDB Persistence & Multi-Role Authentication Layer
Provides MongoDB Atlas connectivity, role-based access control,
sample account seeding, and resilient offline fallback.
"""

import os
import hashlib
import secrets
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

try:
    import pymongo
    from pymongo.errors import PyMongoError, ServerSelectionTimeoutError
    PYMONGO_AVAILABLE = True
except ImportError:
    PYMONGO_AVAILABLE = False


# Default Seed Accounts for 1-Click Quick Demo & Manual Login
DEFAULT_SAMPLE_USERS = [
    {
        "username": "manager@kinetiq.com",
        "password_plain": "manager123",
        "name": "Alice Johnson",
        "role": "store_manager",
        "role_label": "Store General Manager",
        "assigned_store": "STORE_01",
        "store_name": "Downtown Metro Express",
        "avatar": "🏪",
        "description": "Manages local daily sales velocity, inventory runway, and prevents imminent stockouts.",
        "badge_color": "emerald",
    },
    {
        "username": "director@kinetiq.com",
        "password_plain": "director123",
        "name": "Bob Martinez",
        "role": "supply_chain_director",
        "role_label": "Regional Supply Chain Director",
        "assigned_store": "ALL",
        "store_name": "Multi-Store Network (3 Hubs)",
        "avatar": "🔄",
        "description": "Orchestrates inter-store stock rebalancing arbitrage, reclaims dead capital, and resolves phantom inventory.",
        "badge_color": "indigo",
    },
    {
        "username": "executive@kinetiq.com",
        "password_plain": "exec123",
        "name": "Clara Vance",
        "role": "executive",
        "role_label": "Chief Operating Officer",
        "assigned_store": "ALL",
        "store_name": "Enterprise Fleet Portfolio",
        "avatar": "📊",
        "description": "Monitors enterprise gross margin health, portfolio variance, and oversees Gemini AI copilot governance.",
        "badge_color": "amber",
    },
]


def _hash_password(password: str) -> str:
    """Deterministic salted SHA256 hash for secure storage."""
    salt = "kinetiq_retail_salt_2026"
    return hashlib.sha256(f"{salt}:{password}".encode("utf-8")).hexdigest()


class MongoAuthService:
    """
    MongoDB service for user authentication, role management, and audit tracking.
    Features automatic fallback to an in-memory registry if the MongoDB cluster is unreachable.
    """

    def __init__(self, uri: Optional[str] = None, db_name: str = "kinetiq_db"):
        self.uri = uri or os.environ.get("MONGODB_URI")
        self.db_name = db_name
        self.client: Optional[Any] = None
        self.db: Optional[Any] = None
        self.is_connected: bool = False
        
        # In-memory fallback stores
        self._fallback_users: Dict[str, dict] = {}
        self._fallback_sessions: Dict[str, dict] = {}
        self._fallback_audit_logs: List[dict] = []

        self._connect()
        self._seed_sample_accounts()

    def _connect(self):
        """Attempt connection to MongoDB Atlas with a strict 3-second timeout."""
        if not PYMONGO_AVAILABLE or not self.uri:
            print("[MONGODB] PyMongo or MONGODB_URI not configured. Operating in resilient in-memory mode.")
            self.is_connected = False
            return

        try:
            self.client = pymongo.MongoClient(self.uri, serverSelectionTimeoutMS=3000)
            # Verify connection via ping
            self.client.admin.command("ping")
            self.db = self.client[self.db_name]
            self.is_connected = True
            print(f"[MONGODB] Successfully connected to MongoDB Atlas database '{self.db_name}'.")
        except Exception as e:
            print(f"[MONGODB] Notice: Cluster connection deferred ({e}). Fallback auth cache engaged.")
            self.is_connected = False
            self.client = None
            self.db = None

    def _seed_sample_accounts(self):
        """Seed the 3 official demo accounts in MongoDB and in-memory cache."""
        for u in DEFAULT_SAMPLE_USERS:
            record = {
                "username": u["username"],
                "password_hash": _hash_password(u["password_plain"]),
                "name": u["name"],
                "role": u["role"],
                "role_label": u["role_label"],
                "assigned_store": u["assigned_store"],
                "store_name": u["store_name"],
                "avatar": u["avatar"],
                "description": u["description"],
                "badge_color": u["badge_color"],
                "custom_api_key": "",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            # Cache in fallback
            self._fallback_users[u["username"]] = record

            # Upsert into MongoDB if online
            if self.is_connected and self.db is not None:
                try:
                    self.db.users.update_one(
                        {"username": u["username"]},
                        {"$setOnInsert": record},
                        upsert=True,
                    )
                except Exception as e:
                    print(f"[MONGODB] Failed to upsert user {u['username']}: {e}")

    def authenticate(self, username: str, password: str) -> Optional[dict]:
        """Verify username and password against MongoDB or fallback store."""
        target_hash = _hash_password(password)

        user_doc = None
        if self.is_connected and self.db is not None:
            try:
                user_doc = self.db.users.find_one({"username": username.strip().lower()})
            except Exception:
                user_doc = None

        if not user_doc:
            user_doc = self._fallback_users.get(username.strip().lower())

        if not user_doc or user_doc.get("password_hash") != target_hash:
            return None

        # Generate session token
        token = secrets.token_hex(24)
        session_data = {
            "token": token,
            "username": user_doc["username"],
            "name": user_doc["name"],
            "role": user_doc["role"],
            "role_label": user_doc["role_label"],
            "assigned_store": user_doc["assigned_store"],
            "store_name": user_doc["store_name"],
            "avatar": user_doc["avatar"],
            "badge_color": user_doc["badge_color"],
            "custom_api_key": user_doc.get("custom_api_key", ""),
            "created_at": time.time(),
        }

        # Store session
        self._fallback_sessions[token] = session_data
        if self.is_connected and self.db is not None:
            try:
                self.db.sessions.insert_one({**session_data, "_id": token})
            except Exception:
                pass

        self.log_audit(user_doc["username"], user_doc["role"], "LOGIN_PASSWORD", {"store": user_doc["assigned_store"]})
        return session_data

    def quick_login(self, role: str) -> Optional[dict]:
        """1-Click instant sign-in for quick demos and evaluator walk-throughs."""
        matching_user = None
        for u in DEFAULT_SAMPLE_USERS:
            if u["role"] == role:
                matching_user = u
                break

        if not matching_user:
            return None

        return self.authenticate(matching_user["username"], matching_user["password_plain"])

    def get_session(self, token: str) -> Optional[dict]:
        """Retrieve user session by token."""
        if not token:
            return None

        if token in self._fallback_sessions:
            return self._fallback_sessions[token]

        if self.is_connected and self.db is not None:
            try:
                sess = self.db.sessions.find_one({"_id": token})
                if sess:
                    return sess
            except Exception:
                pass

        return None

    def update_custom_api_key(self, username: str, new_api_key: str) -> bool:
        """Update user/role custom Gemini API key."""
        clean_key = new_api_key.strip()
        
        # Update fallback
        if username in self._fallback_users:
            self._fallback_users[username]["custom_api_key"] = clean_key

        # Update active sessions
        for token, sess in self._fallback_sessions.items():
            if sess.get("username") == username:
                sess["custom_api_key"] = clean_key

        # Update MongoDB
        if self.is_connected and self.db is not None:
            try:
                self.db.users.update_one(
                    {"username": username},
                    {"$set": {"custom_api_key": clean_key}}
                )
                self.db.sessions.update_many(
                    {"username": username},
                    {"$set": {"custom_api_key": clean_key}}
                )
            except Exception as e:
                print(f"[MONGODB] Could not update API key: {e}")

        self.log_audit(username, "UNKNOWN", "API_KEY_UPDATED", {"has_key": bool(clean_key)})
        return True

    def log_audit(self, username: str, role: str, action: str, details: Optional[dict] = None):
        """Record operational event for audit compliance."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "username": username,
            "role": role,
            "action": action,
            "details": details or {},
        }
        self._fallback_audit_logs.append(entry)

        if self.is_connected and self.db is not None:
            try:
                self.db.audit_logs.insert_one(entry)
            except Exception:
                pass

    def get_role_presets(self) -> List[dict]:
        """Return public role metadata for 1-click login cards on the login page."""
        return [
            {
                "role": u["role"],
                "role_label": u["role_label"],
                "username": u["username"],
                "password_plain": u["password_plain"],
                "name": u["name"],
                "assigned_store": u["assigned_store"],
                "store_name": u["store_name"],
                "avatar": u["avatar"],
                "description": u["description"],
                "badge_color": u["badge_color"],
            }
            for u in DEFAULT_SAMPLE_USERS
        ]


# Singleton instance
_mongo_auth_singleton: Optional[MongoAuthService] = None


def get_auth_service() -> MongoAuthService:
    """Retrieve or initialize the MongoAuthService singleton."""
    global _mongo_auth_singleton
    if _mongo_auth_singleton is None:
        _mongo_auth_singleton = MongoAuthService()
    return _mongo_auth_singleton
