@echo off
rem Selection replay (RQ3) inside the Docker image; Ollama must be running for S5/S2.
rem   run-select.cmd --check-logprobs --judge-model soapfl-qwen2-5-coder-latest-c16384:latest
rem   run-select.cmd reports/run100-qwen25coder --selector S5
rem   run-select.cmd --list
docker compose run --rm soapfl python -m fl_tools select %*
