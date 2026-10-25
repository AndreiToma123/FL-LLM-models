@echo off
rem Failure-context export (stack traces, failing tests, coverage) inside the Docker image. CPU only, resumable.
rem   run-context.cmd reports/run100-qwen25coder --bugs Lang-1,Closure-105     (smoke test)
rem   run-context.cmd reports/run100-qwen25coder --part dev --jobs 4          (the 50 dev bugs)
docker compose run --rm soapfl python -m fl_tools context %*
