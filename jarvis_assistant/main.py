from __future__ import annotations

from .config import load_settings
from .logging_utils import setup_logging
from .ui import JarvisDesktopApp


def main() -> None:
    setup_logging()
    settings = load_settings()
    app = JarvisDesktopApp(settings)
    app.run()


if __name__ == "__main__":
    main()
