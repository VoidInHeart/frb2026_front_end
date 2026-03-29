from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
PARSER_ROOT = ROOT / "paper-review-system"


def stream_output(prefix: str, process: subprocess.Popen[str]) -> None:
    assert process.stdout is not None
    for line in process.stdout:
        print(f"[{prefix}] {line}", end="")


def start_process(command: list[str], cwd: Path) -> subprocess.Popen[str]:
    return subprocess.Popen(
        command,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )


def npm_command() -> str:
    return "npm.cmd" if os.name == "nt" else "npm"


def main() -> int:
    processes = [
        (
            "parser",
            start_process(
                [sys.executable, "-m", "paper_review_system.web_api"],
                PARSER_ROOT,
            ),
        ),
        (
            "frontend",
            start_process(
                [npm_command(), "run", "dev"],
                ROOT,
            ),
        ),
    ]

    for name, process in processes:
        thread = threading.Thread(
            target=stream_output,
            args=(name, process),
            daemon=True,
        )
        thread.start()

    print("Frontend: http://127.0.0.1:5173")
    print("Parser API: http://127.0.0.1:8000")
    print("Press Ctrl+C to stop both processes.")

    try:
        while True:
            for _, process in processes:
                return_code = process.poll()
                if return_code is not None:
                    return return_code
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        for _, process in processes:
            if process.poll() is None:
                process.terminate()
        for _, process in processes:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
