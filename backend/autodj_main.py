"""Entrypoint for the packaged AutoDJ .exe. Starts uvicorn programmatically."""
import sys
import os

# When running from PyInstaller bundle, the import system needs help locating app.
if getattr(sys, "frozen", False):
    sys.path.insert(0, sys._MEIPASS)

import uvicorn
from app.api import app  # ensures app.api is loaded (incl. browser-open hook)


def main() -> None:
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")


if __name__ == "__main__":
    main()
