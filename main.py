"""Compatibility entrypoint for running exercise 1 from the ex1 folder."""

from __future__ import annotations

import sys
from pathlib import Path


if __name__ == "__main__":
    package_root = Path(__file__).resolve().parent.parent
    package_root_str = str(package_root)
    if package_root_str not in sys.path:
        sys.path.insert(0, package_root_str)

    from ex1.interface import main

    main()
