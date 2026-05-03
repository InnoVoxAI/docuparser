from __future__ import annotations

import sys
from pathlib import Path

SHARED_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SHARED_ROOT))
