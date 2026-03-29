@echo off
setlocal
cd /d "%~dp0paper-review-system"
python -m paper_review_system.web_api
