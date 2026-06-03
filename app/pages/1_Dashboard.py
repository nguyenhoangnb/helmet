import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from violation_ui import render_dashboard


render_dashboard()
