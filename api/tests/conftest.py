"""Test configuration: ensures required settings exist before app modules import."""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("APP_ENCRYPTION_KEY", "test-only-encryption-key-32-bytes-minimum")
os.environ.setdefault("ADMIN_PASSWORD", "test-only-admin-password")
os.environ.setdefault("MONGODB_URI", "mongodb://localhost:27017")
os.environ.setdefault("MONGODB_DB", "DTP_test")
os.environ.setdefault("MONGODB_COLLECTION_PREFIX", "tunes_")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
