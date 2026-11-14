import sys
from pathlib import Path

# Ensure workspace root is in sys.path for cloud deployment
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Launch Streamlit interface
import src.app.ui


