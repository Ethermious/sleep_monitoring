"""Central configuration for the sleep monitoring stack."""
from pathlib import Path

# Storage locations
DB_PATH = Path("/home/ethermious/sleepu_logs/sleepu.db")
CSV_DIR = Path("/home/ethermious/sleepu_logs")

# External acquisition script location
VIATOM_BLE_PATH = Path("/home/ethermious/repos/sleepu/ble/viatom-ble.py")

# Timezone used for sleep_date calculations
TIMEZONE = "America/Chicago"

# Default user identifier for single-user operation
DEFAULT_USER_ID = 1
