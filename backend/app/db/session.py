"""
In-memory store — replaces PostgreSQL entirely.
All data is lost on restart, which is fine for the free-tier MVP.
"""
from typing import Dict, Any
import uuid

# Simple in-memory dicts keyed by UUID string
_projects: Dict[str, Any] = {}
_users: Dict[str, Any] = {}


def get_projects() -> Dict[str, Any]:
    return _projects


def get_users() -> Dict[str, Any]:
    return _users
