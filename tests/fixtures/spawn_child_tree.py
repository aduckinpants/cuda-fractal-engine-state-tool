from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path


def main() -> int:
    sleeper = Path(__file__).with_name("sleeper.py")
    child = subprocess.Popen([sys.executable, str(sleeper), "60"])
    print(f"child_pid={child.pid}", flush=True)
    try:
        time.sleep(60)
    finally:
        if child.poll() is None:
            child.terminate()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
