import sys
from pathlib import Path

# Ensure parent directory is on sys.path so jarvis_assistant package can be imported
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from jarvis_assistant.main import main


if __name__ == "__main__":
    main()
