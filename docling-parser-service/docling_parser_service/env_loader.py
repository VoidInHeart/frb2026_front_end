from __future__ import annotations

from pathlib import Path

_LOADED_ENV_PATHS: tuple[Path, ...] | None = None


def load_parser_service_env(
    *,
    force: bool = False,
    override: bool = False,
    candidate_paths: list[Path] | tuple[Path, ...] | None = None,
) -> list[Path]:
    global _LOADED_ENV_PATHS

    if _LOADED_ENV_PATHS is not None and not force:
        return list(_LOADED_ENV_PATHS)

    try:
        from dotenv import load_dotenv
    except Exception:
        _LOADED_ENV_PATHS = tuple()
        return []

    if candidate_paths is None:
        package_root = Path(__file__).resolve().parent
        service_root = package_root.parent
        project_root = service_root.parent
        candidate_paths = [
            service_root / ".env",
            project_root / ".env",
        ]

    loaded: list[Path] = []
    for raw_path in candidate_paths:
        path = Path(raw_path)
        if not path.is_file():
            continue
        load_dotenv(path, override=override)
        loaded.append(path.resolve())

    _LOADED_ENV_PATHS = tuple(loaded)
    return list(loaded)
