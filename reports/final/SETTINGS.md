# Settings sheet (A3)

| Run | model (checkpoint) | weights id | served by | context / max answer | sampling | seed | code version | patch digest | prompts |
|---|---|---|---|---|---|---|---|---|---|
| runall-qwen25coder-csc | Qwen/Qwen2.5-Coder-7B-Instruct (instruct, bf16, not quantized) | not recorded | python-vllm/0.29.0 | 16384 / 3072 | temperature 0 (greedy; SoapFL/camel default) | SoapFL 0, vLLM 0 | not recorded | f305e1247c469785 | SoapFL's own (patched SoapFL checkout, CompanyConfig/Default) |
| runall-qwen25coder-ca3-csc | Qwen/Qwen2.5-Coder-7B-Instruct (instruct, bf16, not quantized) | not recorded | python-vllm/0.29.0 | 16384 / 3072 | temperature 0 (greedy; SoapFL/camel default) | SoapFL 0, vLLM 0 | not recorded | f305e1247c469785 | SoapFL's own; class list from fl_tools/classaug.py (digest 4aa3d13b0b7b1758) |
| runall-qwen25coder-ca3g-csc | Qwen/Qwen2.5-Coder-7B-Instruct (instruct, bf16, not quantized) | not recorded | python-vllm/0.29.0 | 16384 / 3072 | temperature 0 (greedy; SoapFL/camel default) | SoapFL 0, vLLM 0 | not recorded | f305e1247c469785 | SoapFL's own; class list from fl_tools/classaug.py (digest 4aa3d13b0b7b1758) |
| runall-qwen25coder-d4j2new-csc | Qwen/Qwen2.5-Coder-7B-Instruct (instruct, bf16, not quantized) | not recorded | python-vllm/0.29.0 | 16384 / 3072 | temperature 0 (greedy; SoapFL/camel default) | SoapFL 0, vLLM 0 | not recorded | f305e1247c469785 | SoapFL's own (patched SoapFL checkout, CompanyConfig/Default) |
| runall-qwen25coder-ca3-d4j2new-csc | Qwen/Qwen2.5-Coder-7B-Instruct (instruct, bf16, not quantized) | not recorded | python-vllm/0.29.0 | 16384 / 3072 | temperature 0 (greedy; SoapFL/camel default) | SoapFL 0, vLLM 0 | not recorded | f305e1247c469785 | SoapFL's own; class list from fl_tools/classaug.py (digest 4aa3d13b0b7b1758) |
| runall-qwen25coder-ca3g-d4j2new-csc | Qwen/Qwen2.5-Coder-7B-Instruct (instruct, bf16, not quantized) | not recorded | python-vllm/0.29.0 | 16384 / 3072 | temperature 0 (greedy; SoapFL/camel default) | SoapFL 0, vLLM 0 | not recorded | f305e1247c469785 | SoapFL's own; class list from fl_tools/classaug.py (digest 4aa3d13b0b7b1758) |

Judge: same model and server, temperature 0, answers of 1-2 tokens, prompts in `fl_tools/selection/prompts.py` (hash stored as `prompt_version` in each `<run>-selection.json`). SoapFL commit: c9f75f4f34.

Presets: qwen25coder = Qwen/Qwen2.5-Coder-7B-Instruct; llama31 = meta-llama/Llama-3.1-8B-Instruct; qwen25coder32 = Qwen/Qwen2.5-Coder-32B-Instruct
