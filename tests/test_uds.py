"""Preflight endpoint checks over a Unix domain socket (vLLM --uds on CSC Roihu)."""
from fl_tools.mock_server import start_mock_server
from fl_tools.preflight import check_endpoint


def test_check_endpoint_over_unix_socket(tmp_path, monkeypatch):
    sock = str(tmp_path / "vllm.sock")
    srv = start_mock_server(model="qwen25coder", reply="ready", max_model_len=16384, uds=sock)
    try:
        monkeypatch.setenv("SOAPFL_UDS", sock)
        checks = check_endpoint("http://localhost/v1", "qwen25coder", "EMPTY", context_limit=16384)
        status = {name: level for level, name, _ in checks}
        assert status["endpoint"] == "ok" and status["model-name"] == "ok"
        assert status["context"] == "ok" and status["chat"] == "ok", checks
        assert srv.requests[-1]["model"] == "qwen25coder"
    finally:
        srv.stop()


def test_unix_socket_missing_is_reported(tmp_path, monkeypatch):
    monkeypatch.setenv("SOAPFL_UDS", str(tmp_path / "nothing.sock"))
    checks = check_endpoint("http://localhost/v1", "m", "EMPTY")
    assert checks[-1][0] == "fail" and checks[-1][1] == "endpoint"
