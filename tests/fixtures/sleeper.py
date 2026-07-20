from __future__ import annotations

import sys
import time


def main() -> int:
    seconds = float(sys.argv[1]) if len(sys.argv) > 1 else 60.0
    time.sleep(seconds)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
