from fl_tools.mock_server import start_mock_server
from fl_tools.preflight import check_endpoint


def levels(checks):
    return {name: level for level, name, _ in checks}


def test_endpoint_ok():
    srv = start_mock_server(model="m", max_model_len=8192)
    try:
        r = levels(check_endpoint(srv.url, "m", "x", 8192))
        assert r["endpoint"] == r["model-name"] == r["context"] == r["chat"] == "ok"
    finally:
        srv.stop()


def test_endpoint_problems():
    srv = start_mock_server(model="m", max_model_len=8192)
    try:
        assert levels(check_endpoint(srv.url, "other", "x", 8192))["model-name"] == "fail"
        assert levels(check_endpoint(srv.url, "m", "x", 32768))["context"] == "fail"
        assert levels(check_endpoint(srv.url, None, "x"))["model-name"] == "fail"
    finally:
        srv.stop()
    assert levels(check_endpoint("http://127.0.0.1:9/v1", "m"))["endpoint"] == "fail"
    assert levels(check_endpoint(None, "m"))["endpoint"] == "fail"


def test_parse_ollama_num_ctx():
    from fl_tools.preflight import parse_ollama_num_ctx
    assert parse_ollama_num_ctx({"parameters": "num_ctx                        16384\nstop   \"<|im_end|>\""}) == 16384
    assert parse_ollama_num_ctx({"parameters": "stop \"x\""}) is None
    assert parse_ollama_num_ctx({}) is None


def test_empty_reply_is_a_warning():
    srv = start_mock_server(model="m", max_model_len=8192, null_content=True)
    try:
        assert levels(check_endpoint(srv.url, "m", "x", 8192))["chat"] == "warn"
    finally:
        srv.stop()
