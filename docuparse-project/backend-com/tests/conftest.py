from __future__ import annotations

import sys
from pathlib import Path

SERVICE_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = SERVICE_ROOT.parent
sys.path.insert(0, str(SERVICE_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "contracts"))
sys.path.insert(0, str(PROJECT_ROOT / "shared"))
