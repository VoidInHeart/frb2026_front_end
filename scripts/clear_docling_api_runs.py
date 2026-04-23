from __future__ import annotations

import argparse
import os
import shutil
import stat
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_API_RUNS_DIR = PROJECT_ROOT / "docling-parser-service" / "outputs" / "api_runs"
PRESERVE_NAMES = {".gitkeep", ".gitignore"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Clear generated data under docling-parser-service/outputs/api_runs.",
    )
    parser.add_argument(
        "--target-dir",
        type=Path,
        default=DEFAULT_API_RUNS_DIR,
        help=f"api_runs directory path. Default: {DEFAULT_API_RUNS_DIR}",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show which entries would be deleted without modifying the directory.",
    )
    return parser.parse_args()


def removable_entries(target_dir: Path) -> list[Path]:
    if not target_dir.exists():
        return []
    return sorted(
        [
            child
            for child in target_dir.iterdir()
            if child.name not in PRESERVE_NAMES
        ],
        key=lambda item: item.name.lower(),
    )


def ensure_within_root(path: Path, root: Path) -> None:
    resolved_path = path.resolve()
    resolved_root = root.resolve()
    if resolved_path != resolved_root and resolved_root not in resolved_path.parents:
        raise ValueError(f"Refusing to delete path outside target root: {resolved_path}")


def _retry_remove(func, path: str, exc) -> None:
    try:
        os.chmod(path, stat.S_IWRITE | stat.S_IREAD)
    except OSError:
        pass
    func(path)


def clear_windows_attributes(path: Path) -> None:
    subprocess.run(
        ["attrib", "-R", str(path), "/S", "/D"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )


def decode_subprocess_output(raw: bytes) -> str:
    for encoding in ("utf-8", "gb18030", "gbk"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def run_windows_command(command: list[str]) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def grant_windows_delete_access(path: Path) -> None:
    run_windows_command(["takeown", "/f", str(path), "/r", "/d", "y"])
    run_windows_command(["icacls", str(path), "/grant", f"{os.environ.get('USERNAME', 'Everyone')}:F", "/t", "/c"])


def force_delete_with_windows_shell(path: Path) -> None:
    completed = run_windows_command(["cmd", "/c", "rmdir", "/s", "/q", str(path)])
    stderr = decode_subprocess_output(completed.stderr or b"").strip()
    stdout = decode_subprocess_output(completed.stdout or b"").strip()
    if ("Access is denied" in stderr or "拒绝访问" in stderr) and path.exists():
        grant_windows_delete_access(path)
        completed = run_windows_command(["cmd", "/c", "rmdir", "/s", "/q", str(path)])
        stderr = decode_subprocess_output(completed.stderr or b"").strip()
        stdout = decode_subprocess_output(completed.stdout or b"").strip()

    if (completed.returncode != 0 or stderr) and path.exists():
        detail = stderr or stdout or f"exit code {completed.returncode}"
        raise PermissionError(f"Failed to remove {path}: {detail}")


def delete_entry(path: Path, root: Path) -> None:
    ensure_within_root(path, root)

    if path.is_dir() and not path.is_symlink():
        try:
            shutil.rmtree(path, onexc=_retry_remove)
        except PermissionError:
            if os.name != "nt":
                raise
            clear_windows_attributes(path)
            force_delete_with_windows_shell(path)
        return
    try:
        path.unlink()
    except PermissionError:
        if os.name != "nt":
            raise
        clear_windows_attributes(path)
        os.chmod(path, stat.S_IWRITE | stat.S_IREAD)
        path.unlink()


def format_delete_error(path: Path, exc: Exception) -> str:
    return (
        f"Failed to remove {path}\n"
        "This is usually caused by one of these cases:\n"
        "1. A parser/dev process is still using files in this directory.\n"
        "2. The directory was created with restrictive Windows ACL permissions.\n"
        "Try closing related Python services first, then rerun the script.\n"
        "If it still fails, rerun the command in an Administrator PowerShell.\n"
        f"Original error: {exc}"
    )


def main() -> int:
    args = parse_args()
    target_dir = Path(args.target_dir).expanduser().resolve()

    if target_dir.name != "api_runs":
        print(f"[WARN] Target directory is not named api_runs: {target_dir}")

    target_dir.mkdir(parents=True, exist_ok=True)
    entries = removable_entries(target_dir)

    print(f"Target directory: {target_dir}")
    if entries:
        print("Entries to delete:")
        for entry in entries:
            kind = "dir" if entry.is_dir() and not entry.is_symlink() else "file"
            print(f"  [{kind}] {entry.name}")
    else:
        print("No generated entries found.")

    if args.dry_run:
        print("Dry run only. No changes were made.")
        return 0

    for entry in entries:
        try:
            delete_entry(entry, target_dir)
        except Exception as exc:
            raise RuntimeError(format_delete_error(entry, exc)) from exc

    target_dir.mkdir(parents=True, exist_ok=True)
    print("api_runs data cleared.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
