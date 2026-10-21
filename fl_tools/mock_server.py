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
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import List, Optional


def estimate_tokens(text: str) -> int:
    """Crude token estimate (~3.5 characters per token)."""
    return int(math.ceil(len(text) / 3.5))


class MockServer:
    def __init__(self, httpd: ThreadingHTTPServer, state: dict):
        self._httpd = httpd
        self.state = state
        self._thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        self._thread.start()

    @property
    def port(self) -> int:
        return self._httpd.server_address[1]

    @property
    def url(self) -> str:
        """Base URL to use as SOAPFL_BASE_URL (ends in /v1)."""
        return f"http://127.0.0.1:{self.port}/v1"

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
                      latency: float = 0.0) -> MockServer:
    """Start the server on a free port (port=0) in a background thread.

    rules: list of {"match": <regex on the last user message>, "reply": str,
           "finish_reason": optional str}. The first matching rule wins.
    """
    state = {"requests": [], "n": 0, "lock": threading.Lock()}
    compiled = [(re.compile(r["match"], re.S), r) for r in (rules or [])]

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
            if self.path.rstrip("/").endswith("/models"):
                self._send(200, {"object": "list",
                                 "data": [{"id": model, "object": "model",
                                           "max_model_len": max_model_len}]})
            else:
                self._send(404, {"error": {"message": "not found"}})

        def do_POST(self):
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length) or b"{}")
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
            text, reason = reply, finish_reason
            for pattern, rule in compiled:
                if pattern.search(last_user):
                    text = rule["reply"]
                    reason = rule.get("finish_reason", finish_reason)
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
            if not omit_usage:
                payload["usage"] = {"prompt_tokens": prompt_tokens,
                                    "completion_tokens": completion_tokens,
                                    "total_tokens": prompt_tokens + completion_tokens}
            self._send(200, payload)

    httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    return MockServer(httpd, state)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--model", default="mock-model")
    parser.add_argument("--reply", default="Mock answer. #5#")
    parser.add_argument("--think", action="store_true")
    parser.add_argument("--max-model-len", type=int, default=32768)
    args = parser.parse_args()
    server = start_mock_server(port=args.port, model=args.model, reply=args.reply,
                               think=args.think, max_model_len=args.max_model_len)
    print(f"mock server listening on {server.url} (model={args.model}); Ctrl-C to stop")
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        server.stop()


if __name__ == "__main__":
    main()
