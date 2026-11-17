"""Delete only the dev-prefixed collections (e.g. tunes_dev_*) from MongoDB.

Reads MONGODB_URI / MONGODB_DB / MONGODB_COLLECTION_PREFIX from the
environment (injected by `make local-reset` via the local Compose overlay).
Refuses to run unless the prefix looks like a dev prefix, so a misapplied
overlay can never wipe production collections.
"""

import os
import sys

from pymongo import MongoClient


def main() -> int:
    prefix = os.environ.get("MONGODB_COLLECTION_PREFIX", "")
    if "dev" not in prefix or prefix == "tunes_":
        print(f"Refusing to reset: not a dev prefix: {prefix!r}", file=sys.stderr)
        return 1
    db = MongoClient(os.environ["MONGODB_URI"])[os.environ.get("MONGODB_DB", "DTP")]
    dropped = [name for name in db.list_collection_names() if name.startswith(prefix)]
    for name in dropped:
        db.drop_collection(name)
    print(f"Dropped {len(dropped)} collection(s): {', '.join(dropped) or '(none)'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
