#!/usr/bin/env python3
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from core.application import HawkeyeApplication


def main() -> int:
    app = HawkeyeApplication(BASE_DIR)
    return app.run(sys.argv)


if __name__ == "__main__":
    raise SystemExit(main())
