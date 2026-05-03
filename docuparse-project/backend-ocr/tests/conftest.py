from __future__ import annotations

import sys
from pathlib import Path

BACKEND_OCR_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_OCR_ROOT))
sys.path.insert(0, str(BACKEND_OCR_ROOT.parent / "contracts"))
sys.path.insert(0, str(BACKEND_OCR_ROOT.parent / "shared"))
