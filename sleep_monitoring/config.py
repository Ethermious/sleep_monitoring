"""Central configuration for the sleep monitoring stack."""
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _expanded_path(path: str | Path) -> Path:
    """Return an absolute, user-expanded :class:`Path` for the given input."""

    return Path(path).expanduser().resolve()


# Storage locations (override with env vars for relocations)
DB_PATH = _expanded_path(os.getenv("SLEEPU_DB_PATH", Path.home() / "sleepu_logs" / "sleepu.db"))
CSV_DIR = _expanded_path(os.getenv("SLEEPU_CSV_DIR", DB_PATH.parent))

# External acquisition script location
VIATOM_BLE_PATH = _expanded_path(
    os.getenv("SLEEPU_VIATOM_BLE_PATH", REPO_ROOT / "sleepu" / "ble" / "viatom-ble.py")
)

# Timezone used for sleep_date calculations
TIMEZONE = "America/Chicago"

# Default user identifier for single-user operation
DEFAULT_USER_ID = 1
