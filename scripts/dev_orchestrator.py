from __future__ import annotations

import argparse
import os
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
PARSER_ROOT = ROOT / "paper-review-system"
DOCLING_ROOT = ROOT / "docling-parser-service"
PARSER_HOST = "127.0.0.1"
PARSER_PORT = 8000
DOCLING_HOST = "127.0.0.1"
DOCLING_PORT = 8010
FRONTEND_HOST = "127.0.0.1"
FRONTEND_PORT = 5173

ORCHESTRATION_TARGETS = {
    "default": {
        "process_name": "parser",
        "display_name": "Parser API",
        "host": PARSER_HOST,
        "port": PARSER_PORT,
        "cwd": PARSER_ROOT,
        "command": [sys.executable, "-m", "paper_review_system.web_api"],
        "frontend_env": {},
    },
    "docling": {
        "process_name": "docling",
        "display_name": "Docling Parser API",
        "host": DOCLING_HOST,
        "port": DOCLING_PORT,
        "cwd": DOCLING_ROOT,
        "command": [sys.executable, "-m", "docling_parser_service.app"],
        "frontend_env": {
            "VITE_USE_LOCAL_PARSER": "true",
            "VITE_PARSER_API_BASE_URL": f"http://{DOCLING_HOST}:{DOCLING_PORT}",
        },
    },
}


def decode_output(raw: bytes) -> str:
    for encoding in ("utf-8", "gb18030"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue

    return raw.decode("utf-8", errors="replace")


def stream_output(prefix: str, process: subprocess.Popen[bytes]) -> None:
    assert process.stdout is not None
    while True:
        line = process.stdout.readline()
        if not line:
            break
        print(f"[{prefix}] {decode_output(line)}", end="")


def build_process_env(extra_env: dict[str, str] | None = None) -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    env.setdefault("FORCE_COLOR", "1")
    if extra_env:
        env.update(extra_env)
    return env


def is_port_in_use(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((host, port)) == 0


def start_process(
    command: list[str],
    cwd: Path,
    extra_env: dict[str, str] | None = None,
) -> subprocess.Popen[bytes]:
    return subprocess.Popen(
        command,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=False,
        bufsize=0,
        env=build_process_env(extra_env),
    )


def npm_command() -> str:
    return "npm.cmd" if os.name == "nt" else "npm"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Start the frontend dev server with a local parser service.",
    )
    parser.add_argument(
        "--parser",
        choices=tuple(ORCHESTRATION_TARGETS),
        default="default",
        help="Select which local parser service to start alongside the frontend.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    target = ORCHESTRATION_TARGETS[args.parser]
    processes: list[tuple[str, subprocess.Popen[bytes]]] = []

    if is_port_in_use(target["host"], target["port"]):
        print(f"{target['display_name']} already running at http://{target['host']}:{target['port']}")
    else:
        processes.append(
            (
                target["process_name"],
                start_process(
                    target["command"],
                    target["cwd"],
                ),
            )
        )

    if is_port_in_use(FRONTEND_HOST, FRONTEND_PORT):
        print(f"Frontend dev server may already be running at http://{FRONTEND_HOST}:{FRONTEND_PORT}")

    processes.append(
        (
            "frontend",
            start_process(
                [npm_command(), "run", "dev"],
                ROOT,
                target["frontend_env"],
            ),
        )
    )

    for name, process in processes:
        thread = threading.Thread(
            target=stream_output,
            args=(name, process),
            daemon=True,
        )
        thread.start()

    print(f"Frontend: http://{FRONTEND_HOST}:{FRONTEND_PORT}")
    print(f"{target['display_name']}: http://{target['host']}:{target['port']}")
    if target["frontend_env"]:
        print(f"Frontend parser target: {target['frontend_env']['VITE_PARSER_API_BASE_URL']}")
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
