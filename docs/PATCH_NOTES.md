# Changes to SoapFL (patches/0001-open-model-support.patch)

Base: https://github.com/IntHelloWorld/SoapFL at `c9f75f4f349849bc84d5cc50c4cc7dc70f012f16`.
Everything is switched on by `--model LOCAL`; the OpenAI code path is kept (verify with `git diff` if in doubt).

| File | Change | Why |
|---|---|---|
| `camel/local_llm.py` (new) | env-var settings, event log, `<think>` stripping, score parser | one place for all new behaviour |
| `camel/typing.py` | `ModelType.LOCAL` | new model kind |
| `camel/utils.py` | `get_encoding()` with fallbacks (tiktoken → cl100k → 3-chars/token estimate); LOCAL context limit from `SOAPFL_CONTEXT_LIMIT` | tiktoken downloads its vocabulary at first use and fails on offline nodes; open models have other context sizes |
| `camel/model_backend.py` | LOCAL branch: OpenAI-compatible client (`SOAPFL_BASE_URL`, or a Unix domain socket via `SOAPFL_UDS` as used by vLLM `--uds` on CSC Roihu), served model name, `max_tokens` = window − prompt·(1+margin) − 32, `extra_body`, null-content/usage guards, `<think>` stripping, per-call event | original code hard-codes OpenAI model names, token limits and assumes `usage` is present |
| `camel/agents/chat_agent.py` | log `context_overflow_guard` event | make overflow visible in the funnel |
| `functions/func.py` | `check_tokens` uses `get_encoding` | same tokenizer fallback |
| `run.py` | `--model LOCAL`, `SOAPFL_SEED` | seed per bug; clear error if model name missing |
| `chatdev/phase.py` | lenient mode: tolerate terminated chat, class/method name chars (`$`), unparseable score → 0 + event | open models break formats; strict mode keeps original crashes |

## Not changed (deliberate)
Prompts, the seven tasks, test sampling, score-tie ordering, the 3-step pipeline. The model is the only intended difference.

## Ideas not implemented
FlexFL-style fuzzy name matching of the model's answers; bug reports as extra input; multiple hypotheses (HypoDeduce);
retrieve-then-rerank (FaR-Loc). These are thesis directions, not part of the baseline.
