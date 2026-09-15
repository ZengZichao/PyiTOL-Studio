"""``python -m pyitolstudio`` and PyInstaller entry point.

The import must be absolute: PyInstaller executes this file as a top-level
script without package context, so a relative import would crash the
frozen app before the window opens.
"""

from pyitolstudio.app.main import main

if __name__ == "__main__":
    raise SystemExit(main())
