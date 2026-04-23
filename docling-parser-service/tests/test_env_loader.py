from __future__ import annotations

import os
import shutil
import unittest
from pathlib import Path

from docling_parser_service.env_loader import load_parser_service_env


class EnvLoaderTests(unittest.TestCase):
    def test_service_env_is_loaded_before_project_env(self) -> None:
        sandbox_root = Path(__file__).resolve().parent / "_tmp" / "env_loader_case"
        service_root = sandbox_root / "service"
        project_root = sandbox_root / "project"
        service_root.mkdir(parents=True, exist_ok=True)
        project_root.mkdir(parents=True, exist_ok=True)

        service_env = service_root / ".env"
        project_env = project_root / ".env"
        service_env.write_text(
            "OPENAI_PDF_PARSER_API_KEY=service-key\n"
            "OPENAI_PDF_PARSER_MODEL=service-model\n",
            encoding="utf-8",
        )
        project_env.write_text(
            "OPENAI_PDF_PARSER_API_KEY=project-key\n"
            "OPENAI_PDF_PARSER_BASE_URL=https://example.test/v1\n",
            encoding="utf-8",
        )

        keys = [
            "OPENAI_PDF_PARSER_API_KEY",
            "OPENAI_PDF_PARSER_BASE_URL",
            "OPENAI_PDF_PARSER_MODEL",
        ]
        snapshot = {key: os.environ.get(key) for key in keys}

        try:
            for key in keys:
                os.environ.pop(key, None)

            loaded = load_parser_service_env(
                force=True,
                candidate_paths=[service_env, project_env],
            )

            self.assertEqual(loaded, [service_env.resolve(), project_env.resolve()])
            self.assertEqual(os.getenv("OPENAI_PDF_PARSER_API_KEY"), "service-key")
            self.assertEqual(os.getenv("OPENAI_PDF_PARSER_BASE_URL"), "https://example.test/v1")
            self.assertEqual(os.getenv("OPENAI_PDF_PARSER_MODEL"), "service-model")
        finally:
            for key, value in snapshot.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
            shutil.rmtree(sandbox_root, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
