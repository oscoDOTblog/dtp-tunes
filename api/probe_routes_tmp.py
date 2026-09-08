import os

os.environ.setdefault("APP_ENCRYPTION_KEY", "test-only-encryption-key-32-bytes-minimum")
os.environ.setdefault("ADMIN_PASSWORD", "test-only-admin-password")
os.environ.setdefault("MONGODB_URI", "mongodb://localhost:27017")
os.environ.setdefault("MONGODB_DB", "DTP_test")

from app.main import app

for route in app.routes:
    path = getattr(route, "path", "?")
    if "download" in path or "albums" in path or "stream" in path:
        print(sorted(getattr(route, "methods", []) or []), path)
