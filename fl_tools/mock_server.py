"""A tiny OpenAI-compatible server for testing, standard library only.

It implements GET /v1/models and POST /v1/chat/completions, which is all SoapFL
needs, and can inject the failures small open models cause in practice:
<think> blocks, context-window overflows, truncated generations, server errors.

Use it from tests::

    server = start_mock_server(reply="Looks suspicious. #8#", think=True)
    ... point SOAPFL_BASE_URL at server.url ...
    server.stop()

or from the command line::

    python -m fl_tools.mock_server --port 8000 --reply "OK #7#"
"""
import argparse
import json
import math
import re
import threading
import time
import os
import socketserver
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import List, Optional


def estimate_tokens(text: str) -> int:
    """Crude token estimate (~3.5 characters per token)."""
    return int(math.ceil(len(text) / 3.5))


class _ThreadingUnixHTTPServer(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    """HTTP server on a Unix domain socket, like vLLM started with --uds."""
    daemon_threads = True

    def get_request(self):
        request, _ = super().get_request()
        return request, ("uds", 0)   # BaseHTTPRequestHandler expects a (host, port) client address


class MockServer:
    def __init__(self, httpd: ThreadingHTTPServer, state: dict):
        self._httpd = httpd
        self.state = state
        self._thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        self._thread.start()

    @property
    def uds(self) -> Optional[str]:
        """Socket path if the server listens on a Unix domain socket, else None."""
        address = self._httpd.server_address
        return address if isinstance(address, str) else None

    @property
    def port(self) -> Optional[int]:
        return None if self.uds else self._httpd.server_address[1]

    @property
    def url(self) -> str:
        """Base URL to use as SOAPFL_BASE_URL (ends in /v1)."""
        return "http://localhost/v1" if self.uds else f"http://127.0.0.1:{self.port}/v1"

    @property
    def requests(self) -> List[dict]:
        return self.state["requests"]

    def stop(self) -> None:
        self._httpd.shutdown()
        self._httpd.server_close()


def start_mock_server(port: int = 0,
                      model: str = "mock-model",
                      reply: str = "Mock answer. #5#",
                      rules: Optional[List[dict]] = None,
                      think: bool = False,
                      max_model_len: int = 32768,
                      enforce_context: bool = True,
                      fail_first: int = 0,
                      finish_reason: str = "stop",
                      null_content: bool = False,
                      omit_usage: bool = False,
                      latency: float = 0.0,
                      ollama_models: Optional[dict] = None,
                      create_style: str = "new",
                      uds: Optional[str] = None) -> MockServer:
    """Start the server on a free port (port=0) in a background thread.

    rules: list of {"match": <regex on the last user message>, "reply": str,
           "finish_reason": optional str}. The first matching rule wins.
    ollama_models: if given ({"name:latest": num_ctx or None}), also emulate Ollama's native API
           (/api/tags, /api/show, /api/create) and serve exactly these models on /v1/models.
           create_style "new" accepts {"model","from","parameters"}, "old" only {"name","modelfile"}.
    """
    state = {"requests": [], "api_requests": [], "n": 0, "lock": threading.Lock(),
             "models": dict(ollama_models) if ollama_models is not None else None}
    compiled = [(re.compile(r.get("match") or r.get("match_last") or "", re.S), r) for r in (rules or [])]

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *args):  # keep test output quiet
            pass

        def _send(self, status: int, payload: dict):
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            path = self.path.rstrip("/")
            if path.endswith("/api/tags") and state["models"] is not None:
                self._send(200, {"models": [{"name": n, "model": n} for n in state["models"]]})
            elif path.endswith("/models"):
                if state["models"] is not None:
                    data = [{"id": n, "object": "model"} for n in state["models"]]
                else:
                    data = [{"id": model, "object": "model", "max_model_len": max_model_len}]
                self._send(200, {"object": "list", "data": data})
            else:
                self._send(404, {"error": {"message": "not found"}})

        def _ollama_api(self, path: str, body: dict) -> bool:
            """Handle /api/show and /api/create; return True if the request was an Ollama API call."""
            models = state["models"]
            if models is None or not path.rstrip("/").startswith("/api/"):
                return False
            with state["lock"]:
                state["api_requests"].append({"path": path, "body": body})
            def with_tag(n):
                return n if ":" in n else n + ":latest"
            if path.rstrip("/") == "/api/show":
                name = with_tag(body.get("model") or body.get("name") or "")
                if name not in models:
                    self._send(404, {"error": f"model '{name}' not found"})
                else:
                    ctx = models[name]
                    self._send(200, {"parameters": f"num_ctx                        {ctx}" if ctx else ""})
            elif path.rstrip("/") == "/api/create":
                if create_style == "old":
                    if "modelfile" not in body:
                        self._send(400, {"error": "unknown field"})
                        return True
                    name = with_tag(body.get("name", ""))
                    m = re.search(r"PARAMETER\s+num_ctx\s+(\d+)", body["modelfile"])
                    models[name] = int(m.group(1)) if m else None
                else:
                    if "from" not in body:
                        self._send(400, {"error": "from required"})
                        return True
                    name = with_tag(body.get("model", ""))
                    models[name] = int((body.get("parameters") or {}).get("num_ctx") or 0) or None
                self._send(200, {"status": "success"})
            else:
                self._send(404, {"error": "unknown api"})
            return True

        def do_POST(self):
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length) or b"{}")
            if self._ollama_api(self.path.split("?")[0], body):
                return
            with state["lock"]:
                state["n"] += 1
                n = state["n"]
                state["requests"].append(body)
            if latency:
                time.sleep(latency)
            if n <= fail_first:
                self._send(500, {"error": {"message": "injected server error"}})
                return

            messages = body.get("messages", [])
            prompt_text = "\n".join(str(m.get("content", "")) for m in messages)
            prompt_tokens = estimate_tokens(prompt_text) + 4 * len(messages)
            max_tokens = int(body.get("max_tokens") or 0)
            if enforce_context and prompt_tokens + max_tokens > max_model_len:
                self._send(400, {"error": {
                    "message": (f"This model's maximum context length is {max_model_len} tokens. "
                                f"However, you requested {max_tokens} output tokens and your "
                                f"prompt contains at least {prompt_tokens} input tokens, for a "
                                f"total of {prompt_tokens + max_tokens} tokens."),
                    "type": "BadRequestError", "code": 400}})
                return

            last_user = ""
            for m in reversed(messages):
                if m.get("role") == "user":
                    last_user = str(m.get("content", ""))
                    break
            last_any = str(messages[-1].get("content", "")) if messages else ""
            text, reason, token_logprobs, tool_calls = reply, finish_reason, None, None
            for pattern, rule in compiled:
                target = last_any if "match_last" in rule else last_user   # match_last: last message of any role
                if pattern.search(target):
                    text = rule.get("reply", "")
                    reason = rule.get("finish_reason", finish_reason)
                    token_logprobs = rule.get("logprobs")     # {token: logprob} for the first output token
                    tool_calls = rule.get("tool_calls")       # [{"name", "arguments"}] -> OpenAI tool_calls
                    break
            if think:
                text = "<think>Let me reason about this first.</think>\n" + text

            completion_tokens = estimate_tokens(text)
            payload = {
                "id": f"chatcmpl-mock-{n}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": body.get("model", model),
                "choices": [{
                    "index": 0,
                    "message": {"role": "assistant", "content": None if null_content else text},
                    "finish_reason": reason,
                }],
            }
            if tool_calls:
                payload["choices"][0]["message"]["tool_calls"] = [
                    {"id": f"call_{n}_{i}", "type": "function",
                     "function": {"name": c["name"], "arguments": json.dumps(c.get("arguments", {}))}}
                    for i, c in enumerate(tool_calls)]
                payload["choices"][0]["finish_reason"] = "tool_calls"
            if body.get("logprobs") and token_logprobs:
                top = sorted(token_logprobs.items(), key=lambda kv: -kv[1])[:int(body.get("top_logprobs") or 5)]
                first = text[:1]
                payload["choices"][0]["logprobs"] = {"content": [{
                    "token": first, "logprob": token_logprobs.get(first, top[0][1]),
                    "top_logprobs": [{"token": t, "logprob": lp} for t, lp in top]}]}
            if not omit_usage:
                payload["usage"] = {"prompt_tokens": prompt_tokens,
                                    "completion_tokens": completion_tokens,
                                    "total_tokens": prompt_tokens + completion_tokens}
            self._send(200, payload)

    if uds:
        if os.path.exists(uds):
            os.unlink(uds)
        httpd = _ThreadingUnixHTTPServer(uds, Handler)
    else:
        httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    return MockServer(httpd, state)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--model", default="mock-model")
    parser.add_argument("--reply", default="Mock answer. #5#")
    parser.add_argument("--think", action="store_true")
    parser.add_argument("--max-model-len", type=int, default=32768)
    parser.add_argument("--uds", default=None, help="listen on this Unix socket instead of a port")
    args = parser.parse_args()
    server = start_mock_server(port=args.port, model=args.model, reply=args.reply,
                               think=args.think, max_model_len=args.max_model_len, uds=args.uds)
    where = f"unix socket {server.uds}" if server.uds else server.url
    print(f"mock server listening on {where} (model={args.model}); Ctrl-C to stop")
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        server.stop()


if __name__ == "__main__":
    main()
