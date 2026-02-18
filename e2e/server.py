"""E2E test server — starts Flask with an isolated test database."""
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from storage.db import Database
from web.app import create_app

PORT = int(os.environ.get("E2E_PORT", "5099"))
DB_PATH = Path(__file__).parent / ".test.db"

if __name__ == "__main__":
    # Remove stale test DB for fresh state
    DB_PATH.unlink(missing_ok=True)
    for ext in ("-shm", "-wal"):
        Path(str(DB_PATH) + ext).unlink(missing_ok=True)

    app = create_app()
    app.db = Database(db_path=DB_PATH)

    print(f"  E2E test server starting on http://127.0.0.1:{PORT}")
    app.run(host="127.0.0.1", port=PORT, debug=False)
