@echo off
setlocal
cd /d "%~dp0docling-parser-service"
python -m docling_parser_service.app
