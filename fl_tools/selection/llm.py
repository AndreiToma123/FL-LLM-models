"""Model client for judge selectors: OpenAI-compatible chat endpoint (Ollama locally, vLLM on CSC).

Connection settings are the same environment variables as the pipelines: SOAPFL_BASE_URL (or SOAPFL_UDS for a
Unix socket), SOAPFL_API_KEY. Every call is cached on disk by a hash of (model, messages, parameters), so
re-running a selector, an ablation or the test part never repeats a call. Each answer records its cost.
"""
import hashlib
import json
import os
import threading
import time
import urllib.error
from typing import Dict, List, Optional

from ..preflight import _http_json


class JudgeError(RuntimeError):
    pass


class JudgeClient:
    def __init__(self, model: str, base_url: Optional[str] = None, api_key: Optional[str] = None,
                 cache_path: Optional[str] = None, timeout: float = 600.0, retries: int = 2):
        self.model = model
        self.base_url = (base_url or os.environ.get("SOAPFL_BASE_URL") or os.environ.get("OPENAI_BASE_URL")
                         or ("http://localhost/v1" if os.environ.get("SOAPFL_UDS") else "")).rstrip("/")
        if not self.base_url:
            raise JudgeError("no model endpoint: set SOAPFL_BASE_URL (or SOAPFL_UDS), as for the pipelines")
        self.api_key = api_key or os.environ.get("SOAPFL_API_KEY") or os.environ.get("OPENAI_API_KEY") or "EMPTY"
        self.timeout, self.retries = timeout, retries
        self.cache_path = cache_path
        self._cache: Dict[str, dict] = {}
        self._lock = threading.Lock()
        if cache_path and os.path.exists(cache_path):
            with open(cache_path, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        row = json.loads(line)
                        self._cache[row["key"]] = row["response"]
                    except (json.JSONDecodeError, KeyError):
                        continue
        self.stats = {"calls": 0, "cached": 0, "prompt_tokens": 0, "completion_tokens": 0, "seconds": 0.0}

    def _key(self, payload: dict) -> str:
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

    def chat(self, messages: List[dict], max_tokens: int = 4, temperature: float = 0.0, seed: int = 0,
             logprobs: bool = False, top_logprobs: int = 0, tools: Optional[List[dict]] = None) -> dict:
        payload = {"model": self.model, "messages": messages, "max_tokens": max_tokens,
                   "temperature": temperature, "seed": seed}
        if logprobs:
            payload["logprobs"] = True
            payload["top_logprobs"] = top_logprobs
        if tools:
            payload["tools"] = tools
        key = self._key(payload)
        with self._lock:
            if key in self._cache:
                self.stats["cached"] += 1
                return dict(self._cache[key], cached=True)
        last = None
        for attempt in range(self.retries + 1):
            started = time.time()
            try:
                reply = _http_json(self.base_url + "/chat/completions", payload, self.api_key, timeout=self.timeout)
                break
            except urllib.error.HTTPError as exc:
                if exc.code in (400, 404):   # wrong model name or bad request: retrying will not help
                    raise JudgeError(f"HTTP {exc.code} from {self.base_url} for model {self.model!r}. "
                                     + ("The model is probably not installed under this name (check `ollama "
                                        "list`; give the run folder or --judge-model)." if exc.code == 404 else
                                        exc.read().decode(errors="replace")[:300]))
                last = exc
                time.sleep(2 ** attempt)
            except (urllib.error.URLError, OSError, ValueError) as exc:
                last = exc
                time.sleep(2 ** attempt)
        else:
            raise JudgeError(f"judge call failed after {self.retries + 1} attempts: {last}")
        seconds = time.time() - started
        choice = (reply.get("choices") or [{}])[0]
        usage = reply.get("usage") or {}
        content = ((choice.get("message") or {}).get("content") or "").strip()
        tops = []
        for tok in ((choice.get("logprobs") or {}).get("content") or [])[:1]:
            tops = [(t.get("token", ""), float(t.get("logprob", -1e9))) for t in tok.get("top_logprobs") or []]
        calls = []
        for i, tc in enumerate((choice.get("message") or {}).get("tool_calls") or []):
            fn = tc.get("function") or {}
            args = fn.get("arguments")
            if isinstance(args, str):
                try:
                    args = json.loads(args) if args.strip() else {}
                except json.JSONDecodeError:
                    args = {"_unparsed": args}
            calls.append({"id": tc.get("id") or f"call_{i}", "name": fn.get("name", ""), "arguments": args or {}})
        response = {"text": content, "top_logprobs": tops, "tool_calls": calls,
                    "prompt_tokens": usage.get("prompt_tokens", 0),
                    "completion_tokens": usage.get("completion_tokens", 0), "seconds": round(seconds, 3)}
        with self._lock:
            self.stats["calls"] += 1
            self.stats["prompt_tokens"] += response["prompt_tokens"] or 0
            self.stats["completion_tokens"] += response["completion_tokens"] or 0
            self.stats["seconds"] += seconds
            self._cache[key] = response
            if self.cache_path:
                os.makedirs(os.path.dirname(os.path.abspath(self.cache_path)), exist_ok=True)
                with open(self.cache_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps({"key": key, "model": self.model, "response": response}) + "\n")
        return dict(response, cached=False)


PROBE_TOOL = {"type": "function", "function": {
    "name": "get_method_code", "description": "Return the source code of a Java method.",
    "parameters": {"type": "object", "properties": {"method": {"type": "string", "description": "Class::method"}},
                   "required": ["method"]}}}


def probe_tools(client: JudgeClient) -> dict:
    """Does the endpoint return native tool calls (OpenAI `tools` API)? Needed for S8b's native protocol;
    otherwise S8b uses its JSON action protocol."""
    r = client.chat([{"role": "user", "content": "Use the tool to get the code of the method Foo::bar(int). "
                                                  "Do not answer in text."}],
                    max_tokens=128, tools=[PROBE_TOOL])
    ok = any(c["name"] == "get_method_code" and "method" in c["arguments"] for c in r["tool_calls"])
    return {"supported": ok, "tool_calls": r["tool_calls"], "text": r["text"][:200]}


def probe_logprobs(client: JudgeClient) -> dict:
    """Does the endpoint return per-token log-probabilities? (needed for the S2 layer)"""
    r = client.chat([{"role": "user", "content": "Answer with a single digit from 0 to 9: how many sides has a "
                                                  "triangle?"}], max_tokens=1, logprobs=True, top_logprobs=10)
    return {"supported": bool(r["top_logprobs"]), "answer": r["text"], "top_logprobs": r["top_logprobs"][:10]}
